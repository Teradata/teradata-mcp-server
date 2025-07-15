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

### 4.1. Python Libraries

You will need to install the following Python libraries. You can create a `requirements.txt` file and install them using `pip install -r requirements.txt`.

```
quart
quart-cors
hypercorn
google-generativeai
langchain-mcp-adapters
python-dotenv
```

### 4.2. External Dependencies

* **MCP Server**: A running instance of the MCP server is required. The client is configured by default to connect to `http://localhost:8001/mcp/`. This URL can be changed in the `MCP_SERVER_URL` global variable.
* **Google Gemini API Key**: The application requires a valid API key for the Gemini LLM, configured via a `.env` file.
* **Web Browser**: A modern web browser that supports Server-Sent Events (e.g., Chrome, Firefox, Safari, Edge).

## 5. Setup & Installation

1.  **Clone the Repository**:
    ```bash
    git clone <your-repo-url>
    cd <your-repo-directory>
    ```

2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure Environment Variables**: Create a file named `.env` in the root directory of the project. Add your Gemini API key to this file:
    ```
    GEMINI_API_KEY="YOUR_API_KEY_HERE"
    ```

4.  **Create the Web Interface**: Create a directory named `templates` in the same directory as `mcp_web_client.py`. Inside the `templates` directory, create an `index.html` file. You will need to provide your own HTML/CSS/JS for the frontend that interacts with the backend API endpoints.

## 6. Usage

1.  **Start the MCP Server**: Ensure your MCP server instance is running and accessible at the configured URL.

2.  **Run the Web Client**: Execute the main Python script from your terminal:
    ```bash
    python mcp_web_client.py
    ```

3.  **Access the UI**: Once the server starts, you will see a message like:
    ```
    --- Starting Hypercorn Server for Quart App ---
    Web client initialized and ready. Navigate to [http://127.0.0.1:5000](http://127.0.0.1:5000)
    ```
    Open your web browser and navigate to `http://127.0.0.1:5000` to begin using the application.

## 7. API Endpoints

The Quart web server exposes the following RESTful API endpoints:

* **`GET /`**:
    * **Description**: Serves the main `index.html` chat interface.
* **`GET /tools`**:
    * **Description**: Returns a categorized JSON object of all tools loaded from the MCP server.
    * **Success Response**: `200 OK` with a JSON body like `{"Category 1": [{"name": "tool_A", "description": "..."}]}`.
* **`GET /prompts`**:
    * **Description**: Returns a categorized JSON object of all prompts loaded from the MCP server.
    * **Success Response**: `200 OK` with a JSON body containing prompt details.
* **`GET /resources`**:
    * **Description**: Returns a categorized JSON object of all resources loaded from the MCP server.
    * **Success Response**: `200 OK` with a JSON body containing resource details.
* **`POST /session`**:
    * **Description**: Creates a new, unique chat session with the LLM, initialized with the system prompt.
    * **Success Response**: `200 OK` with a JSON body: `{"session_id": "unique-uuid-string"}`.
* **`POST /ask_stream`**:
    * **Description**: The main endpoint for processing a user's natural language request. It streams the entire multi-step process back to the client.
    * **Request Body**: `{"session_id": "...", "message": "..."}`
    * **Response**: A `text/event-stream` response with multiple events (`llm_thought`, `tool_result`, `final_answer`, `error`).
* **`POST /invoke_prompt_stream`**:
    * **Description**: Executes a pre-defined prompt with arguments and streams the results.
    * **Request Body**: `{"session_id": "...", "prompt_name": "...", "arguments": {...}}`
    * **Response**: A `text/event-stream` response similar to `/ask_stream`.

## 8. Project Structure

```
.
├── .env                    # Environment variables file
├── mcp_web_client.py       # Main Quart application file
├── templates/
│   └── index.html          # Frontend HTML, CSS, and JavaScript
└── requirements.txt        # Python dependencies
```
