# web_client.py
import asyncio
import json
import os
import sys
import re
import uuid
from quart import Quart, request, jsonify, render_template, Response
from quart_cors import cors
import hypercorn.asyncio
from hypercorn.config import Config
from dotenv import load_dotenv

# This environment variable MUST be set to "false" before any LangChain
# modules are imported to programmatically disable the problematic tracer.
os.environ["LANGCHAIN_TRACING_V2"] = "false"

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_mcp_adapters.resources import load_mcp_resources

# Using the base google.generativeai library for stateful chat
import google.generativeai as genai

# --- Globals for Web App ---
app = Quart(__name__)
app = cors(app, allow_origin="*") # Enable CORS for all origins

tools_context = None
prompts_context = None
# This will be the GenerativeModel object
llm = None
mcp_tools = {}
mcp_prompts = {}
structured_tools = {}
structured_prompts = {}
structured_resources = {}

# This dictionary will store active chat sessions, keyed by a unique session ID.
SESSIONS = {}
# This will hold the active session with the MCP server
mcp_session = None

# --- Core Logic ---

async def call_llm_api(prompt: str, session_id: str = None, chat_history=None) -> str:
    """
    Sends a prompt to the Gemini API.
    Can use a specific session or be a one-off call if chat_history is provided.
    """
    if not llm: raise RuntimeError("LLM is not initialized.")
    
    try:
        if session_id:
            if session_id not in SESSIONS: raise ValueError("Invalid session ID.")
            chat_session = SESSIONS[session_id]
            response = await chat_session.send_message_async(prompt)
        elif chat_history is not None:
            # This is used for one-off calls that need specific system instructions
            chat_session = llm.start_chat(history=chat_history)
            response = await chat_session.send_message_async(prompt)
        else: # A simple one-off call without history
             response = await llm.generate_content_async(prompt)

        # Check for empty or invalid response from the LLM
        if not response or not hasattr(response, 'text'):
            app.logger.error("LLM returned an empty or invalid response.")
            return "Error: The language model returned an empty response."

        return response.text.strip()
    except Exception as e:
        app.logger.error(f"Error calling LLM API: {e}", exc_info=True)
        return None # Return None on failure to be handled by the caller


async def invoke_mcp_tool(command: dict) -> any:
    """Looks up and invokes a tool, then correctly parses the result."""
    tool_name = command.get("tool_name")
    args = command.get("arguments", {})

    if not tool_name or tool_name not in mcp_tools:
        app.logger.error(f"LLM requested a non-existent tool: '{tool_name}'")
        return {"error": f"Tool '{tool_name}' not found or not loaded."}

    tool_to_invoke = mcp_tools[tool_name]
    
    try:
        app.logger.info(f"Attempting to invoke tool '{tool_name}' with dictionary input: {args}")
        raw_result = await tool_to_invoke.ainvoke(args)
        app.logger.info(f"Successfully invoked tool. Raw response: {raw_result}")

        if isinstance(raw_result, str):
            try:
                return json.loads(raw_result)
            except json.JSONDecodeError:
                app.logger.error(f"Tool '{tool_name}' returned a string that is not valid JSON: {raw_result}")
                return {"error": "Tool returned non-JSON string", "data": raw_result}
        elif isinstance(raw_result, list) and len(raw_result) > 0 and hasattr(raw_result[0], 'text'):
            return json.loads(raw_result[0].text)
        elif isinstance(raw_result, dict):
            return raw_result
        else:
            app.logger.warning(f"Tool '{tool_name}' returned an unhandled format: {type(raw_result)}")
            return str(raw_result)

    except Exception as e:
        app.logger.error(f"Error during tool invocation for '{tool_name}': {e}", exc_info=True)
        return {"error": f"An exception occurred while invoking tool '{tool_name}'."}

# --- Helper for Server-Sent Events ---
def format_sse(data: dict, event: str = None) -> str:
    """Formats a dictionary into a server-sent event string."""
    msg = f"data: {json.dumps(data)}\n"
    if event is not None:
        msg += f"event: {event}\n"
    return f"{msg}\n"

# --- Web Server Routes ---

@app.route("/")
async def index():
    """Serves the main chat interface."""
    return await render_template("index.html")

@app.route("/tools")
async def get_tools():
    """Returns the structured and categorized list of available tools."""
    global structured_tools
    if not structured_tools:
        return jsonify({"error": "Tools not loaded or categorized yet."}), 503
    return jsonify(structured_tools)

@app.route("/prompts")
async def get_prompts():
    """Returns the structured and categorized list of available prompts."""
    global structured_prompts
    if not structured_prompts:
        return jsonify({"error": "Prompts not loaded or categorized yet."}), 503
    return jsonify(structured_prompts)

@app.route("/resources")
async def get_resources_route():
    """Returns the structured and categorized list of available resources."""
    global structured_resources
    if not structured_resources:
        return jsonify({"error": "Resources not loaded or categorized yet."}), 503
    return jsonify(structured_resources)


@app.route("/session", methods=["POST"])
async def new_session():
    """Creates a new, independent chat session."""
    global llm, tools_context, prompts_context
    try:
        session_id = str(uuid.uuid4())
        
        system_prompt = (
            "You are a specialized API calling assistant. Your purpose is to translate a user's request into a command to call a tool. "
            "Adhere to these rules strictly:\n"
            "1. First, on a new line, write a short thought process explaining which tool you are choosing and why. Start this line with 'Thought:'.\n"
            "2. After your thought, provide a single, valid JSON object to call the chosen tool. The JSON object must be enclosed in a ```json ... ``` markdown block.\n"
            "3. Your response must contain both the thought and the JSON block.\n\n"
            "--- Available Tools ---\n"
            f"{tools_context}\n\n"
            "--- Available Prompts ---\n"
            f"{prompts_context}\n\n"
            "--- Example ---\n"
            "User request: \"list all the dbs\"\n"
            "Your response:\n"
            "Thought: The user wants to list all databases. The `base_databaseList` tool is designed for this purpose. It requires no arguments.\n"
            "```json\n"
            "{\"tool_name\": \"base_databaseList\", \"arguments\": {}}\n"
            "```\n"
            "--- End Example ---"
        )
        
        SESSIONS[session_id] = llm.start_chat(history=[
            {"role": "user", "parts": [{"text": system_prompt}]},
            {"role": "model", "parts": [{"text": "Understood. I will respond with my thought process followed by a JSON command block."}]}
        ])
        app.logger.info(f"Created new session: {session_id}")
        return jsonify({"session_id": session_id})
    except Exception as e:
        app.logger.error(f"Failed to create new session: {e}", exc_info=True)
        return jsonify({"error": "Failed to initialize a new chat session on the server."}), 500


@app.route("/ask_stream", methods=["POST"])
async def ask_stream():
    """
    Handles a user's request for a specific session and streams responses.
    """
    data = await request.get_json()
    user_input = data.get("message")
    session_id = data.get("session_id")
    
    async def stream_generator(user_input, session_id):
        if not all([user_input, session_id]):
            yield format_sse({"error": "Missing 'message' or 'session_id'"}, "error")
            return
        if session_id not in SESSIONS:
            yield format_sse({"error": "Invalid or expired session ID"}, "error")
            return

        app.logger.info(f"Received stream request for session {session_id}: {user_input}")

        try:
            # Step 1: Call LLM to get the command
            yield format_sse({"step": "Assistant is thinking...", "details": "Generating tool command based on user input."})
            
            command_prompt = (
                f"Based on our conversation history, process the following new request.\n"
                f"User request: \"{user_input}\"\n"
                "Your response: "
            )
            llm_reasoning_and_command = await call_llm_api(command_prompt, session_id)
            yield format_sse({"step": "Assistant has decided on a tool", "details": llm_reasoning_and_command}, "llm_thought")
            
            # Step 2: Parse the command
            mcp_command = None
            json_match = re.search(r"```json\s*\n(.*?)\n\s*```", llm_reasoning_and_command, re.DOTALL)

            if not json_match:
                raise ValueError(f"LLM failed to generate a valid JSON command block. Response: {llm_reasoning_and_command}")

            json_string = json_match.group(1).strip()
            mcp_command = json.loads(json_string)

            # Step 3: Invoke the MCP tool
            yield format_sse({"step": f"Calling tool: {mcp_command.get('tool_name')}", "details": mcp_command})
            mcp_response = await invoke_mcp_tool(mcp_command)
            yield format_sse({"step": "Tool execution finished", "details": mcp_response, "tool_name": mcp_command.get('tool_name')}, "tool_result")

            # Step 4: Summarize the result
            yield format_sse({"step": "Summarizing result...", "details": "Generating a natural language response for the user."})
            summary_prompt = (
                f"Based on our conversation history, the user's last message was: '{user_input}'.\n"
                f"The system executed a command and got this JSON response: {json.dumps(mcp_response)}.\n\n"
                "Please provide a friendly, natural language answer to the user's last message. "
                "Do not just repeat the JSON. If the response indicates an error, explain it clearly."
            )
            final_answer = await call_llm_api(summary_prompt, session_id)
            yield format_sse({"final_answer": final_answer}, "final_answer")

        except Exception as e:
            app.logger.error(f"An unhandled error occurred in /ask_stream: {e}", exc_info=True)
            yield format_sse({"error": "An unexpected server error occurred.", "details": str(e)}, "error")

    return Response(stream_generator(user_input, session_id), mimetype="text/event-stream")


@app.route("/invoke_prompt_stream", methods=["POST"])
async def invoke_prompt_stream():
    """
    Handles a prompt invocation and streams the multi-step process.
    """
    data = await request.get_json()
    session_id = data.get("session_id")
    prompt_name = data.get("prompt_name")
    arguments = data.get("arguments", {})

    async def stream_generator(session_id, prompt_name, arguments):
        if not all([session_id, prompt_name]):
            yield format_sse({"error": "Missing 'session_id' or 'prompt_name'"}, "error")
            return
        if not mcp_session:
            yield format_sse({"error": "MCP session is not active."}, "error")
            return
            
        app.logger.info(f"Executing multi-step stream for prompt: '{prompt_name}' with arguments: {arguments}")
        
        try:
            mcp_command = {}
            
            # Step 1: Get instruction from MCP server (or build command directly)
            yield format_sse({"step": "Preparing to execute prompt...", "details": f"Prompt: {prompt_name}\nArguments: {json.dumps(arguments)}"})
            
            if prompt_name == 'base_query':
                # This prompt bypasses the LLM for command generation
                sql_query = arguments.get("qry")
                if not sql_query: raise ValueError("The 'base_query' prompt was invoked without a 'qry' argument.")
                mcp_command = {"tool_name": "base_readQuery", "arguments": {"sql": sql_query}}
                yield format_sse({"step": "Assistant has decided on a tool", "details": "Directly using `base_readQuery` for this prompt."}, "llm_thought")
            else:
                # For other prompts, get the instruction and have the LLM create the command
                get_prompt_result = await mcp_session.get_prompt(name=prompt_name, arguments=arguments)
                mcp_instruction = str(get_prompt_result)
                yield format_sse({"step": "Assistant is thinking...", "details": "Received instruction from MCP Server, generating tool command."})

                system_prompt_for_tool_call = (
                    "You are a specialized API calling assistant. Your purpose is to translate a user's request into a command to call a tool. "
                    "Adhere to these rules strictly:\n"
                    "1. First, on a new line, write a short thought process explaining which tool you are choosing and why. Start this line with 'Thought:'.\n"
                    "2. After your thought, provide a single, valid JSON object to call the chosen tool. The JSON object must be enclosed in a ```json ... ``` markdown block.\n"
                    "3. The JSON object MUST have a 'tool_name' key and an 'arguments' key.\n\n"
                    "--- Available Tools ---\n"
                    f"{tools_context}\n\n"
                    "--- Example ---\n"
                    "User request: \"Create a SQL query to count all tables.\"\n"
                    "Your response:\n"
                    "Thought: The user wants to execute a SQL query. The `base_readQuery` tool is designed for this purpose. The query is `SELECT count(*) FROM DBC.Tables;`.\n"
                    "```json\n"
                    "{\"tool_name\": \"base_readQuery\", \"arguments\": {\"sql\": \"SELECT count(*) FROM DBC.Tables;\"}}\n"
                    "```\n"
                    "--- End Example ---"
                )
                tool_call_history = [
                    {"role": "user", "parts": [{"text": system_prompt_for_tool_call}]},
                    {"role": "model", "parts": [{"text": "Understood. I will respond with my thought process followed by a JSON command block with 'tool_name' and 'arguments' keys."}]}
                ]
                llm_reasoning_and_command = await call_llm_api(mcp_instruction, chat_history=tool_call_history)
                yield format_sse({"step": "Assistant has decided on a tool", "details": llm_reasoning_and_command}, "llm_thought")
                
                json_match = re.search(r"```json\s*\n(.*?)\n\s*```", llm_reasoning_and_command, re.DOTALL)
                if not json_match: raise ValueError(f"LLM failed to generate a valid JSON command block.")
                json_string = json_match.group(1).strip()
                mcp_command = json.loads(json_string)
            
            # Step 2: Invoke the tool
            yield format_sse({"step": f"Calling tool: {mcp_command.get('tool_name')}", "details": mcp_command})
            execution_result = await invoke_mcp_tool(mcp_command)
            yield format_sse({"step": "Tool execution finished", "details": execution_result, "tool_name": mcp_command.get("tool_name")}, "tool_result")

            # Step 3: Summarize
            yield format_sse({"step": "Summarizing result...", "details": "Generating a natural language response for the user."})
            summary_prompt = (
                f"A user executed a pre-defined prompt named '{prompt_name}'.\n"
                f"This resulted in the following action being taken: {json.dumps(mcp_command, indent=2)}.\n"
                f"The action returned this JSON result: {json.dumps(execution_result)}.\n\n"
                "Please provide a friendly, natural language summary of this result for the user. "
                "Do not just repeat the JSON. If the result is an error, explain it clearly."
            )
            final_answer = await call_llm_api(summary_prompt, session_id)
            yield format_sse({"final_answer": final_answer}, "final_answer")

        except Exception as e:
            app.logger.error(f"An unhandled error occurred in /invoke_prompt_stream: {e}", exc_info=True)
            yield format_sse({"error": "An unexpected server error occurred.", "details": str(e)}, "error")
            
    return Response(stream_generator(session_id, prompt_name, arguments), mimetype="text/event-stream")


# --- Main Application Entry Point ---

async def main():
    """Initializes services and runs the web server within a persistent MCP session."""
    global mcp_tools, tools_context, llm, structured_tools, mcp_prompts, structured_prompts, prompts_context, mcp_session, structured_resources

    # Load environment variables from a .env file for MCP configuration
    load_dotenv()
    
    try:
        # The GEMINI_API_KEY is expected to be in the shell environment, not the .env file.
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key: 
            raise ValueError("GEMINI_API_KEY not found. Please export it in your shell environment.")
        genai.configure(api_key=api_key)
        llm = genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        print(f"Fatal Error initializing LLM: {e}")
        sys.exit(1)

    # Construct MCP Server URL from environment variables
    mcp_host = os.getenv("MCP_HOST", "127.0.0.1")
    mcp_port = os.getenv("MCP_PORT", "8001")
    mcp_path = os.getenv("MCP_PATH", "/mcp/")
    mcp_server_url = f"http://{mcp_host}:{mcp_port}{mcp_path}"

    print(f"\nAttempting to connect to MCP server at {mcp_server_url}...")
    client = MultiServerMCPClient({"mcp_server": {"url": mcp_server_url, "transport": "streamable_http"}})
    
    try:
        async with client.session("mcp_server") as session:
            mcp_session = session
            print("--- MCP CLIENT SESSION ACTIVE ---")
            
            print("--- Loading tools, prompts, and resources from MCP server... ---")
            
            # Load Tools
            try:
                loaded_tools = await load_mcp_tools(session)
                print(f"Successfully loaded {len(loaded_tools)} tools.")
            except Exception as e:
                print(f"FATAL: Could not load tools from the server. Error: {e}", exc_info=True)
                return

            if not loaded_tools:
                print("Fatal Error: No tools were loaded.")
                return

            mcp_tools = {tool.name: tool for tool in loaded_tools}
            tools_context = "\n\n".join([f"Tool: `{tool.name}`\nDescription: {tool.description}" for tool in loaded_tools])

            # Load Prompts
            loaded_prompts = []
            try:
                list_prompts_result = await session.list_prompts()
                loaded_prompts = list_prompts_result.prompts
                print(f"Successfully loaded {len(loaded_prompts)} prompts.")
            except Exception as e:
                print(f"WARNING: Could not load prompts. The prompt feature will be disabled. Error: {e}")
                loaded_prompts = []

            if loaded_prompts:
                mcp_prompts = {prompt.name: prompt for prompt in loaded_prompts}
                prompts_context = "\n\n".join([f"Prompt: `{prompt.name}`\nDescription: {prompt.description}" for prompt in loaded_prompts])
            else:
                prompts_context = ""

            # Load Resources
            loaded_resources = []
            try:
                loaded_resources = await load_mcp_resources(session)
                print(f"Successfully loaded {len(loaded_resources)} resources.")
            except Exception as e:
                print(f"WARNING: Could not load resources. The resource feature will be disabled. Error: {e}")
                loaded_resources = []


            print("\n--- Categorizing tools using the LLM ---")
            tool_list_for_prompt = "\n".join([f"- {tool.name}: {tool.description}" for tool in loaded_tools])
            
            categorization_prompt = (
                "You are a helpful assistant that organizes lists of technical tools for a **Teradata database system** into logical categories. "
                "Based on the following list of tools and their descriptions, group them into categories. "
                "Your response MUST be a single, valid JSON object. The keys should be the category names, "
                "and the values should be an array of tool names belonging to that category.\n\n"
                "Example Format:\n"
                "{\n"
                "  \"Database & Schema\": [\"tool_db_create\"],\n"
                "  \"User Administration\": [\"tool_user_add\"]\n"
                "}\n\n"
                "--- Tool List ---\n"
                f"{tool_list_for_prompt}"
            )
            
            categorized_tools_str = await call_llm_api(categorization_prompt)
            try:
                if categorized_tools_str is None: raise ValueError("LLM returned None")
                cleaned_str = re.search(r'\{.*\}', categorized_tools_str, re.DOTALL).group(0)
                categorized_tools = json.loads(cleaned_str)
                
                structured_tools = {}
                for category, tool_names in categorized_tools.items():
                    structured_tools[category] = []
                    for name in tool_names:
                        if name in mcp_tools:
                            structured_tools[category].append({
                                "name": name,
                                "description": mcp_tools[name].description
                            })
                print("Successfully categorized tools.")
            except (json.JSONDecodeError, TypeError, AttributeError, ValueError) as e:
                print(f"Warning: Could not categorize tools, will display as a single list. Error: {e}")
                structured_tools = {
                    "All Tools": [{"name": tool.name, "description": tool.description} for tool in loaded_tools]
                }
            
            # Categorize Prompts
            if loaded_prompts:
                print("\n--- Categorizing prompts using the LLM ---")
                serializable_prompts = []
                for prompt in loaded_prompts:
                    try:
                        prompt_dict = {
                            "name": prompt.name,
                            "description": prompt.description,
                            "arguments": [arg.model_dump() for arg in prompt.arguments]
                        }
                        serializable_prompts.append(prompt_dict)
                    except Exception as e:
                        print(f"Warning: Could not serialize prompt '{prompt.name}'. Error: {e}")

                prompt_list_for_prompt = "\n".join([f"- {p['name']}: {p['description']}" for p in serializable_prompts])
                categorization_prompt_for_prompts = (
                    "You are a helpful assistant that organizes lists of technical prompts for a **Teradata database system** into logical categories. "
                    "Based on the following list of prompts and their descriptions, group them into categories. "
                    "Your response MUST be a single, valid JSON object. The keys should be the category names, "
                    "and the values should be an array of prompt names belonging to that category.\n\n"
                    "--- Prompt List ---\n"
                    f"{prompt_list_for_prompt}"
                )
                categorized_prompts_str = await call_llm_api(categorization_prompt_for_prompts)
                try:
                    if categorized_prompts_str is None: raise ValueError("LLM returned None")
                    cleaned_str = re.search(r'\{.*\}', categorized_prompts_str, re.DOTALL).group(0)
                    categorized_prompts = json.loads(cleaned_str)
                    
                    structured_prompts = {}
                    for category, prompt_names in categorized_prompts.items():
                        structured_prompts[category] = []
                        for name in prompt_names:
                            prompt_to_add = next((p for p in serializable_prompts if p['name'] == name), None)
                            if prompt_to_add:
                                structured_prompts[category].append(prompt_to_add)
                    print("Successfully categorized prompts.")

                except (json.JSONDecodeError, TypeError, AttributeError, ValueError) as e:
                    print(f"Warning: Could not categorize prompts, will display as a single list. Error: {e}")
                    structured_prompts = { "All Prompts": serializable_prompts }
            
            # Categorize Resources
            if loaded_resources:
                print("\n--- Categorizing resources using the LLM ---")
                resource_list_for_prompt = "\n".join([f"- {res.name}: {res.description}" for res in loaded_resources])
                categorization_prompt_for_resources = (
                    "You are a helpful assistant that organizes lists of server resources into logical categories. "
                    "Based on the following list of resources and their descriptions, group them into categories. "
                    "Your response MUST be a single, valid JSON object. The keys should be the category names, "
                    "and the values should be an array of resource names belonging to that category.\n\n"
                    "--- Resource List ---\n"
                    f"{resource_list_for_prompt}"
                )
                categorized_resources_str = await call_llm_api(categorization_prompt_for_resources)
                try:
                    if categorized_resources_str is None: raise ValueError("LLM returned None")
                    cleaned_str = re.search(r'\{.*\}', categorized_resources_str, re.DOTALL).group(0)
                    categorized_resources = json.loads(cleaned_str)
                    
                    for category, resource_names in categorized_resources.items():
                        structured_resources[category] = []
                        for name in resource_names:
                            res_to_add = next((r for r in loaded_resources if r.name == name), None)
                            if res_to_add:
                                structured_resources[category].append({
                                    "name": res_to_add.name,
                                    "description": res_to_add.description
                                })
                    print("Successfully categorized resources.")

                except (json.JSONDecodeError, TypeError, AttributeError, ValueError) as e:
                    print(f"Warning: Could not categorize resources, will display as a single list. Error: {e}")
                    structured_resources = {
                        "All Resources": [{"name": res.name, "description": res.description} for res in loaded_resources]
                    }


            print("\n--- Starting Hypercorn Server for Quart App ---")
            print("Web client initialized and ready. Navigate to http://127.0.0.1:5000")
            config = Config()
            config.bind = ["127.0.0.1:5000"]
            config.accesslog = "-"
            config.errorlog = "-"
            await hypercorn.asyncio.serve(app, config)

    except Exception as e:
        print(f"--- FATAL: Could not establish a session with the MCP server: {e} ---")
        print(f"--- Please ensure the MCP server is running and accessible. ---")

if __name__ == "__main__":
    if not os.path.exists('templates'):
        os.makedirs('templates')
    
    if not os.path.exists('templates/index.html'):
        print("Warning: 'templates/index.html' not found.")
        print("Please ensure the provided index.html file is saved in the 'templates' directory.")

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer shut down.")
