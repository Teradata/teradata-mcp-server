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
import argparse
from datetime import datetime

nest_asyncio.apply()
load_dotenv()


class MCP_TestSuite:
    def __init__(self):
        self.exit_stack = AsyncExitStack()
        self.anthropic = AnthropicBedrock(
            aws_access_key=os.getenv("aws_access_key_id"),
            aws_secret_key=os.getenv("aws_secret_access_key"),
            aws_region=os.getenv("aws_region", 'us-east-1')
        )
        # Sessions dict maps tool/prompt names or resource URIs to MCP client sessions
        self.sessions = {}
        self.test_data = {}
        self.available_tools = []

    async def connect_to_server(self):
        try:
            server_config = {
                "command": "uv",
                "args": [
                    "--directory",
                    "/Users/Daniel.Tehan/Code/MCP/teradata-mcp-server/src/teradata_mcp_server/",
                    "run",
                    "server.py"
                ],
                "env": {
                    "DATABASE_URI": os.getenv("DATABASE_URI"),
                }
            }
    
            server_params = StdioServerParameters(**server_config)
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            read, write = stdio_transport
            self.session = await self.exit_stack.enter_async_context(
                ClientSession(read, write)
            )
            await self.session.initialize()
            
            
            try:
                # List available tools
                response = await self.session.list_tools()
                for tool in response.tools:
                    self.sessions[tool.name] = self.session
                    self.available_tools.append({
                        "name": tool.name,
                        "description": tool.description,
                        "input_schema": tool.inputSchema
                    })
            except Exception as e:
                print(f"Error loading tools: {e}")

        except Exception as e:
            print(f"Error connecting to server: {e}")


    async def test_loop(self, test_json_path):
        print("\nMCP Test Loop Started!")
        
        # Load in the test JSON file
        try:
            with open(test_json_path, "r") as f:
                self.test_data = json.load(f)
        except Exception as e:
            print(f"Error loading test data: {e}")
            return

        print(f"Running tests from {self.test_data.get('module', 'Unknown Test Suite')} module\n")

        for i in range(len(self.test_data["tests"])):
            print(f"Test {i+1}: {self.test_data['tests'][i]['name']}")
            messages = []
            messages.append({'role':'user', 'content':[{"type":"text", "text": self.test_data["tests"][i]["input"]["query"]}]})

            
            response = self.anthropic.messages.create(
                max_tokens = 2024,
                model = 'anthropic.claude-3-5-sonnet-20240620-v1:0', 
                tools = self.available_tools,
                messages = messages
            )

            for content in response.content:
                if content.type == 'text':
                    messages.append({'role':'assistant', 'content':[{"type":"text","text":content.text}]}) 
                    self.test_data["tests"][i]["ouput"] = messages

                elif content.type == 'tool_use':   
                    # Get session and call tool
                    session = self.sessions.get(content.name)
                    if not session:
                        print(f"Tool '{content.name}' not found.")
                        break
                        
                    result = await self.session.call_tool(content.name, arguments=content.input)

                    # Convert the result content to a string if it's a TextContent object
                    result_content = result.content
                    if hasattr(result_content, 'text'):
                        result_content = result_content.text
                    elif isinstance(result_content, list):
                        result_content = [item.text if hasattr(item, 'text') else str(item) for item in result_content]
                    messages.append({'role': 'assistant', 'content': [{'type':'tool_use', 'id': content.id, 'name': content.name, 'input': content.input}]})
                    messages.append({'role': 'user', 'content': [{'type':'tool_result', 'tool_use_id': content.id, 'content': f"""{result_content}"""}]})
                    self.test_data["tests"][i]["ouput"] = messages
            

        # Write the modified test data with results into a JSON file
        try:
            base_name = os.path.splitext(os.path.basename(test_json_path))[0]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            results_dir = "test/test_suite/test_results"
            os.makedirs(results_dir, exist_ok=True)
            results_path = os.path.join(
                results_dir,
                f"{base_name}_results_{timestamp}.json"
            )
            with open(results_path, "w") as f:
                json.dump(self.test_data, f, indent=4)
            print(f"\nTest results saved to {results_path}")
        except Exception as e:
            print(f"Error saving test results: {e}")
    
    async def cleanup(self):
        await self.exit_stack.aclose()
        try:
            self.anthropic.close()
        except Exception as e:
            print(f"Error closing Anthropic client: {e}")


async def main():
    parser = argparse.ArgumentParser(description="Run MCP test suite.")
    parser.add_argument(
        "--test_json",
        type=str,
        required=True,
        help="Path to the test JSON file (e.g., test/test_suite/base_test.json)"
    )
    if len(os.sys.argv) == 1:
        parser.print_usage()
        print("No arguments provided. Exiting.")
        print("Usage: python test_suite.py --test_json <path_to_test_json>")
        return

    args = parser.parse_args()
    testbot = MCP_TestSuite()
    await testbot.connect_to_server()
    print("Connected to MCP servers successfully!")
    await testbot.test_loop(args.test_json)
    print("Test loop completed!")
    await testbot.cleanup() 

if __name__ == "__main__":
    asyncio.run(main())