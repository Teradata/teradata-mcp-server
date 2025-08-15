from dotenv import load_dotenv
from anthropic import AnthropicBedrock
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from contextlib import AsyncExitStack
import json
import asyncio
import nest_asyncio
import boto3
import os

nest_asyncio.apply()
load_dotenv()


class MCP_ChatBot:
    def __init__(self):
        self.exit_stack = AsyncExitStack()
        self.history_file = "logs/chat_history.json"
        self.history = self.load_history()

        if os.getenv("aws_role_switch"):
            sts_client = boto3.client(
                "sts",
                aws_access_key_id=os.getenv("aws_access_key_id"),
                aws_secret_access_key=os.getenv("aws_secret_access_key"),
                aws_session_token=os.getenv("aws_session_token")
            )

            # assume role with bedrock permissions, you will need to copy your ARN into the RoleArn field below
            assumed_role = sts_client.assume_role(
                RoleArn=os.getenv("aws_role_arn"), RoleSessionName=os.getenv("aws_role_name")
            )
            # get bedrock role credentials
            temp_credentials = assumed_role["Credentials"]
            # create bedrock runtime
            self.anthropic = AnthropicBedrock(
                aws_access_key=temp_credentials["AccessKeyId"],
                aws_secret_key=temp_credentials["SecretAccessKey"],
                aws_session_token=temp_credentials["SessionToken"],
                aws_region=os.getenv("aws_region", 'us-east-1')
            )
        else:
            self.anthropic = AnthropicBedrock(
                aws_access_key=os.getenv("aws_access_key_id"),
                aws_secret_key=os.getenv("aws_secret_access_key"),
                aws_session_token=os.getenv("aws_session_token"),
                aws_region=os.getenv("aws_region", 'us-east-1')
            )

        # Tools list required for Anthropic API
        self.available_tools = []
        # Prompts list for quick display 
        self.available_prompts = []
        # Sessions dict maps tool/prompt names or resource URIs to MCP client sessions
        self.sessions = {}
        # Message history for the chat
        self.history = []

    def load_history(self):
        """Load chat history from file"""
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r') as f:
                    return json.load(f)
            return []
        except Exception as e:
            print(f"Error loading chat history: {e}")
            return []

    def save_history(self):
        """Save chat history to file"""
        try:
            with open(self.history_file, 'w') as f:
                json.dump(self.history, f, indent=2)
        except Exception as e:
            print(f"Error saving chat history: {e}")

    async def connect_to_server(self, server_name, server_config):
        try:
            server_params = StdioServerParameters(**server_config)
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            read, write = stdio_transport
            session = await self.exit_stack.enter_async_context(
                ClientSession(read, write)
            )
            await session.initialize()
            
            
            try:
                # List available tools
                response = await session.list_tools()
                for tool in response.tools:
                    self.sessions[tool.name] = session
                    self.available_tools.append({
                        "name": tool.name,
                        "description": tool.description,
                        "input_schema": tool.inputSchema
                    })
            
                # List available prompts
                prompts_response = await session.list_prompts()
                if prompts_response and prompts_response.prompts:
                    for prompt in prompts_response.prompts:
                        self.sessions[prompt.name] = session
                        self.available_prompts.append({
                            "name": prompt.name,
                            "description": prompt.description,
                            "arguments": prompt.arguments
                        })
                # List available resources
                resources_response = await session.list_resources()
                if resources_response and resources_response.resources:
                    for resource in resources_response.resources:
                        resource_uri = str(resource.uri)
                        self.sessions[resource_uri] = session
            
            except Exception as e:
                print(f"Error {e}")
                
        except Exception as e:
            print(f"Error connecting to {server_name}: {e}")

    async def connect_to_servers(self):
        try:
            with open("./examples/MCP_Client_Example/server_config.json", "r") as file:
                data = json.load(file)
            servers = data.get("mcpServers", {})
            for server_name, server_config in servers.items():
                await self.connect_to_server(server_name, server_config)
        except Exception as e:
            print(f"Error loading server config: {e}")
            raise
    
    async def process_query(self, query, previous_messages=None):
        # Include previous context if available
        messages = previous_messages or []
        messages.append({'role':'user', 'content':[{"type":"text", "text": query}]})
        self.history.append({'role':'user', 'content':[{"type":"text","text": query}]})

        while True:
            response = self.anthropic.messages.create(
                max_tokens = 2024,
                model = 'anthropic.claude-3-5-sonnet-20240620-v1:0', 
                tools = self.available_tools,
                messages = messages
            )
            
            assistant_content = []
            has_tool_use = False

            for content in response.content:
                if content.type == 'text':
                    print(f"\n{content.text}\n")
                    self.history.append({'role':'assistant', 'content':[{"type":"text","text":content.text}]})
                    assistant_content.append(content)
                elif content.type == 'tool_use':
                    has_tool_use = True
                    
                    # Get session and call tool
                    session = self.sessions.get(content.name)
                    if not session:
                        print(f"Tool '{content.name}' not found.")
                        break
                        
                    result = await session.call_tool(content.name, arguments=content.input)

                    # Convert the result content to a string if it's a TextContent object
                    result_content = result.content
                    if hasattr(result_content, 'text'):
                        result_content = result_content.text
                    elif isinstance(result_content, list):
                        result_content = [item.text if hasattr(item, 'text') else str(item) for item in result_content]
                    
                    messages.append({'role': 'assistant', 'content': [{'type':'tool_use', 'id': content.id, 'name': content.name, 'input': content.input}]})
                    self.history.append({'role': 'assistant', 'content': [{'type':'tool_use', 'id': content.id, 'name': content.name, 'input': content.input}]})

                    messages.append({'role': 'user', 'content': [{'type':'tool_result', 'tool_use_id': content.id, 'content': f"""{result_content}"""}]})
                    self.history.append({'role': 'user', 'content': [{'type':'tool_result', 'tool_use_id': content.id, 'content': f"""{result_content}"""}]})

            # Exit loop if no tool was used
            if not has_tool_use:
                break

    async def get_resource(self, resource_uri):
        session = self.sessions.get(resource_uri)
        
        # Fallback for papers URIs - try any papers resource session
        if not session and resource_uri.startswith("papers://"):
            for uri, sess in self.sessions.items():
                if uri.startswith("papers://"):
                    session = sess
                    break
            
        if not session:
            print(f"Resource '{resource_uri}' not found.")
            return
        
        try:
            result = await session.read_resource(uri=resource_uri)
            if result and result.contents:
                print(f"\nResource: {resource_uri}")
                print("Content:")
                print(result.contents[0].text)
            else:
                print("No content available.")
        except Exception as e:
            print(f"Error: {e}")
    
    async def list_prompts(self):
        """List all available prompts."""
        if not self.available_prompts:
            print("No prompts available.")
            return
        
        print("\nAvailable prompts:")
        for prompt in self.available_prompts:
            print(f"- {prompt['name']}: {prompt['description']}")
            if prompt['arguments']:
                print("  Arguments:")
                for arg in prompt['arguments']:
                    arg_name = arg.name if hasattr(arg, 'name') else arg.get('name', '')
                    print(f"    - {arg_name}")
    
    async def execute_prompt(self, prompt_name, args):
        """Execute a prompt with the given arguments."""
        session = self.sessions.get(prompt_name)
        if not session:
            print(f"Prompt '{prompt_name}' not found.")
            return
        
        try:
            result = await session.get_prompt(prompt_name, arguments=args)
            if result and result.messages:
                prompt_content = result.messages[0].content
                
                # Extract text from content (handles different formats)
                if isinstance(prompt_content, str):
                    text = prompt_content
                elif hasattr(prompt_content, 'text'):
                    text = prompt_content.text
                else:
                    # Handle list of content items
                    text = " ".join(item.text if hasattr(item, 'text') else str(item) 
                                  for item in prompt_content)
                
                print(f"\nExecuting prompt '{prompt_name}'...")
                await self.process_query(text)
        except Exception as e:
            print(f"Error: {e}")
    
    async def chat_loop(self):
        print("\nMCP Chatbot Started!")
        print("Type your queries or 'quit' to exit.")
        print("Use @folders to see available topics")
        print("Use @<topic> to search papers in that topic")
        print("Use /prompts to list available prompts")
        print("Use /prompt <name> <arg1=value1> to execute a prompt")
        print("Use --help to see this message again")
        
        while True:
            try:
                query = input("\nQuery: ").strip()
                if not query:
                    continue
        
                if query.lower() == 'quit':
                    break

                if query.lower() == '--help':
                    print("Type your queries or 'quit' to exit.")
                    print("Use @folders to see available topics")
                    print("Use @<topic> to search papers in that topic")
                    print("Use /prompts to list available prompts")
                    print("Use /prompt <name> <arg1=value1> to execute a prompt")
                    print("Use --help to see this message again")
                    continue
                
                # Check for @resource syntax first
                if query.startswith('@'):
                    # Remove @ sign  
                    topic = query[1:]
                    if topic == "folders":
                        resource_uri = "papers://folders"
                    else:
                        resource_uri = f"papers://{topic}"
                    await self.get_resource(resource_uri)
                    continue
                
                # Check for /command syntax
                if query.startswith('/'):
                    parts = query.split()
                    command = parts[0].lower()
                    
                    if command == '/prompts':
                        await self.list_prompts()
                    elif command == '/prompt':
                        if len(parts) < 2:
                            print("Usage: /prompt <name> <arg1=value1> <arg2=value2>")
                            continue
                        
                        prompt_name = parts[1]
                        args = {}
                        
                        # Parse arguments
                        for arg in parts[2:]:
                            if '=' in arg:
                                key, value = arg.split('=', 1)
                                args[key] = value
                        
                        await self.execute_prompt(prompt_name, args)
                    else:
                        print(f"Unknown command: {command}")
                    continue
                
                # Get last few messages for context (last 4 messages)
                context_messages = []
                for msg in self.history[-15:]:  # Get last 15 messages
                    if msg['role'] in ['user', 'assistant']:  # Only include user and assistant messages
                        context_messages.append(msg)
                
                await self.process_query(query, context_messages)
                    
            except Exception as e:
                print(f"\nError: {str(e)}")
    
    async def cleanup(self):
        self.save_history()
        await self.exit_stack.aclose()


async def main():
    chatbot = MCP_ChatBot()
    try:
        await chatbot.connect_to_servers()
        await chatbot.chat_loop()
    finally:
        await chatbot.cleanup()


if __name__ == "__main__":
    asyncio.run(main())