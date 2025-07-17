# MCP (Model Context Protocol) Web Client

## 1. Introduction

This application is a Python-based web client that provides an interactive, user-friendly interface for interacting with an MCP (Model Context Protocol) server. It acts as a bridge between a user's natural language requests and a suite of backend tools, prompts, and resources exposed by the MCP server.

The client leverages a powerful Large Language Model (LLM), specifically Google's Gemini 1.5 Flash, to interpret user intent, select the appropriate tool or prompt, and generate the necessary commands. The results are then streamed back to the user in a clear, conversational format. This creates a dynamic "natural language shell" for complex backend systems, particularly geared towards managing a Teradata database environment.

## 2. Core Features

* **Natural Language to Tool Execution**: Translates plain English requests (e.g., "list all the databases") into specific JSON-based tool commands that the MCP server can execute.
* **Interactive Chat Interface**: Provides a web-based chat UI where users can have an ongoing conversation with the system. Each chat is managed in a separate, stateful session.
* **Dynamic Tool, Prompt, and Resource Discovery**: On startup, the client automatically queries the MCP server to load and display all available tools, prompts, and resources.
* **LLM-Powered Categorization**: Uses the Gemini LLM to intelligently group the discovered tools, prompts, and resources into logical categories, making them easier for users to browse.
* **Streaming Responses**: Utilizes Server-Sent Events (SSE) to provide real-time, step-by-step feedback to the user as a request is processed. This includes the LLM's reasoning, the tool being called, the execution result, and the final summary.
* **Pre-defined Prompt Execution**: Allows users to invoke complex, pre-defined prompts on the MCP server with specific arguments, simplifying multi-step or frequently used operations.
* **Session Management**: Supports multiple concurrent user sessions, each with its own independent chat history and context.

## 3. System Architecture & Workflow

The application operates in a multi-step flow to process a user's request:

1.  **User Input**: The user enters a request in the web UI (e.g., "How many tables are in the 'sales' database?").
2.  **LLM Command Generation**: The web client sends the user's request to the Gemini LLM, along with a list of available tools. The LLM determines the correct tool to use (e.g., `base_readQuery`) and generates a JSON command object (e.g., `{"tool_name": "base_readQuery", "arguments": {"sql": "SELECT COUNT(*) FROM DBC.TablesV WHERE DatabaseName = 'sales';"}}`).
3.  **Tool Invocation**: The client parses the JSON command and sends it to the `invoke_mcp_tool` function, which executes the corresponding tool via the `langchain_mcp_adapters` library.
4.  **Result Execution**: The MCP server receives the command, executes it against the target system (e.g., Teradata), and returns a JSON result to the web client.
5.  **LLM Summarization**: The client sends the raw JSON result back to the LLM and asks it to generate a user-friendly, natural language summary (e.g., "There are 57 tables in the 'sales' database.").
6.  **Stream to UI**: Each of these steps (LLM thought, tool call, result, final answer) is streamed back to the user's web browser in real-time.

## 4. Requirements

### 4.1. Python Environment
This application requires **Python 3.9** or newer.

### 4.2. Python Libraries

You will need to install the following Python libraries. You can use the provided `requirements.txt` file and install them using `pip install -r requirements.txt`.

```
quart
quart-cors
hypercorn
python-dotenv
langchain-mcp-adapters
google-generativeai
```

### 4.3. External Dependencies

* **MCP Server**: A running instance of the MCP server is required. The client is configured via the `.env` file to connect to the server.
* **Google Gemini API Key**: The application requires a valid API key for the Gemini LLM, which must be set as a shell environment variable.
* **Web Browser**: A modern web browser that supports Server-Sent Events (e.g., Chrome, Firefox, Safari, Edge).

## 5. Usage

1.  **Clone the Repository**:
    ```bash
    git clone <your-repo-url>
    cd <your-repo-directory>
    ```

2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Set Environment Variable**: Set your Gemini API key as a shell environment variable. This is more secure than saving it in a file.

    *On macOS/Linux:*
    ```bash
    export GEMINI_API_KEY="YOUR_API_KEY_HERE"
    ```
    *On Windows (Command Prompt):*
    ```powershell
    set GEMINI_API_KEY="YOUR_API_KEY_HERE"
    ```
    *On Windows (PowerShell):*
    ```powershell
    $env:GEMINI_API_KEY="YOUR_API_KEY_HERE"
    ```

4.  **Configure MCP Server**: Ensure you have a `.env` file with the correct connection details for your MCP server.

5.  **Start the MCP Server**: Ensure your MCP server instance is running and accessible. The client will connect to the URL configured in your `.env` file (`http://<MCP_HOST>:<MCP_PORT><MCP_PATH>`).

    For the `streamable-http` transport protocol to work, the MCP server must also be started with the correct settings. You can do this by setting the environment variables before running the server.

    *Example on macOS/Linux:*
    ```bash
    export MCP_PORT=8001
    export MCP_TRANSPORT=streamable-http
    uv run teradata-mcp-server
    ```

6.  **Run the Web Client**: Execute the main Python script from your terminal:
    ```bash
    python mcp_web_client.py
    ```

7.  **Access the UI**: Once the server starts, you will see a message like:
    ```
    --- Starting Hypercorn Server for Quart App ---
    Web client initialized and ready. Navigate to [http://127.0.0.1:5000](http://127.0.0.1:5000)
    ```
    Open your web browser and navigate to `http://127.0.0.1:5000` to begin using the application.

## 6. API Endpoints

The Quart web server exposes the following RESTful API endpoints:

* **`GET /`**:
    * **Description**: Serves the main `index.html` chat interface.
* **`GET /tools`**:
    * **Description**: Returns a categorized JSON object of all tools loaded from the MCP server.
* **`GET /prompts`**:
    * **Description**: Returns a categorized JSON object of all prompts loaded from the MCP server.
* **`GET /resources`**:
    * **Description**: Returns a categorized JSON object of all resources loaded from the MCP server.
* **`POST /session`**:
    * **Description**: Creates a new, unique chat session with the LLM.
* **`POST /ask_stream`**:
    * **Description**: The main endpoint for processing a user's natural language request.
* **`POST /invoke_prompt_stream`**:
    * **Description**: Executes a pre-defined prompt with arguments and streams the results.

## 7. Project Structure

```
.
├── .env                    # Environment variables file for MCP server
├── mcp_web_client.py       # Main Quart application file
├── templates/
│   └── index.html          # Frontend HTML, CSS, and JavaScript
└── requirements.txt        # Python dependencies
```
