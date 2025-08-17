# To run this code type the following command in the terminal:
#   adk web
#
#  The followin video is a good overview of ADK and how to use it:
#  https://www.youtube.com/watch?v=P4VFL9nIaIA

import asyncio
import os

import nest_asyncio
from dotenv import load_dotenv
from google.adk.agents.llm_agent import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.mcp_tool.mcp_toolset import (
    MCPToolset,
    SseConnectionParams,
    StdioConnectionParams,
    StdioServerParameters,
    StreamableHTTPConnectionParams,
)

load_dotenv()
nest_asyncio.apply()

async def create_agent():
    """Defines the transport mode to be used."""

    if os.getenv("MCP_TRANSPORT") == 'stdio':
        # .env file needs to have MCP_TRANSPORT=stdio
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command='uv',
                args=[
                    "--directory",
                    "/Users/Daniel.Tehan/Code/MCP/teradata-mcp-server",
                    "run",
                    "teradata-mcp-server"
                ],
            ),
            timeout=30  # Timeout in seconds for establishing the connection to the MCP std
        )
    elif os.getenv("MCP_TRANSPORT") == 'sse':
        # .env file needs to have MCP_TRANSPORT=sse
        connection_params=SseConnectionParams(
            url = f'http://{os.getenv("MCP_HOST", "localhost")}:{os.getenv("MCP_PORT", 8001)}/sse',  # URL of the MCP server
            timeout=20,  # Timeout in seconds for establishing the connection to the MCP SSE server
        )

    elif os.getenv("MCP_TRANSPORT") == 'streamable-http':
        # .env file needs to have MCP_TRANSPORT=streamable-http
        connection_params=StreamableHTTPConnectionParams(
            url = f'http://{os.getenv("MCP_HOST", "localhost")}:{os.getenv("MCP_PORT", 8001)}/mcp/',  # URL of the MCP server
            timeout=20,  # Timeout in seconds for establishing the connection to the MCP Streamable HTTP server
        )

    else:
        raise ValueError("MCP_TRANSPORT environment variable must be set to 'stdio', 'sse', or 'streamable-http'.")

    toolset = MCPToolset(connection_params=connection_params)

    """Defines the model to be used."""
    # Using Bedrock model
    model=LiteLlm(
            model='bedrock/anthropic.claude-3-5-sonnet-20240620-v1:0',
            aws_access_key_id=os.getenv("aws_access_key_id"),
            aws_secret_access_key=os.getenv("aws_secret_access_key"),
            region_name=os.getenv("aws_region", "us-west-2")
        )

    # # Using Google model
    # model='gemini-2.0-flash'

    # # Using Azure model
    # model=LiteLlm(
    #         model='azure/gpt-4o-mini',
    #         api_key=os.getenv('azure_api_key'),
    #         api_base=os.getenv('azure_gpt-4o-mini'),
    #     )

    # # Using Ollama model, you need to install Ollama and run the server
    # # https://ollama.com/docs/installation
    # model=LiteLlm(
    #         model='ollama/llama4:latest',
    #         api_base=os.getenv('ollama_api_base', 'http://localhost:11434'),
    #     )

    agent = LlmAgent(
        model=model,
        name='Simple_Agent',
        instruction='Help user with Teradata tasks',
        tools=[toolset]
    )

    return agent

# Create the agent asynchronously
root_agent = asyncio.run(create_agent())

