import os
import nest_asyncio
import asyncio
from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.mcp_tool.mcp_toolset import StdioServerParameters, StreamableHTTPConnectionParams, SseConnectionParams, StdioConnectionParams

from .sub_agents.DB_Object_Agent import create_db_object_agent
from .sub_agents.DB_Space_Agent import create_db_space_agent
from .sub_agents.DB_User_Agent import create_db_user_agent
from .sub_agents.DB_Security_Agent import create_db_security_agent



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
            timeout=10  # Timeout in seconds for establishing the connection to the MCP std
        )
    elif os.getenv("MCP_TRANSPORT") == 'sse':
        # .env file needs to have MCP_TRANSPORT=sse
        connection_params=SseConnectionParams(
            url = f'http://{os.getenv("MCP_HOST", "localhost")}:{os.getenv("MCP_PORT", 8001)}/sse',  # URL of the MCP server
            timeout=10,  # Timeout in seconds for establishing the connection to the MCP SSE server
        )

    elif os.getenv("MCP_TRANSPORT") == 'streamable-http':
        # .env file needs to have MCP_TRANSPORT=streamable-http
        connection_params=StreamableHTTPConnectionParams(
            url = f'http://{os.getenv("MCP_HOST", "localhost")}:{os.getenv("MCP_PORT", 8001)}/mcp/',  # URL of the MCP server
            timeout=10,  # Timeout in seconds for establishing the connection to the MCP Streamable HTTP server
        )

    else:
        raise ValueError("MCP_TRANSPORT environment variable must be set to 'stdio', 'sse', or 'streamable-http'.")


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
    #         model='ollama/llama4:latest,
    #         api_base=os.getenv('ollama_api_base', 'http://localhost:11434'),
    #     )
    
    # Create sub-agents with shared tools
    db_object_agent = create_db_object_agent(connection_params, model)
    db_space_agent = create_db_space_agent(connection_params, model)
    db_user_agent = create_db_user_agent(connection_params, model)
    db_security_agent = create_db_security_agent(connection_params, model)

    # Create the root agent that orchestrates the DBA process
    agent = LlmAgent(
        name="DBA_Agent",
        description=("A manager agent that orchestrates DBA process."),
        model=model,
        sub_agents=[
            db_object_agent,
            db_space_agent,
            db_user_agent,
            db_security_agent,
        ],
        instruction=(
            """
            # Teradata Database Administrator (DBA) Agent

            You are the Teradata DBA agent, responsible for orchestrating the 
            process of managing DBA activities on a Teradata database.  

            ## Your Role as Manager

            You oversee all database administration processes by delegating to specialized agents for administration activitites:

            ## Database Security Management
            Delegate to: DB_Security_Agent
            This specialized agent will be responsible for managing security in the Teradata environment. This will include
            - Identifying user roles
            - Identify permissions for each role
            - Granting and revoking permissions

            ## Database Space Management
            Delegate to: DB_Space_Agent
            This specialized agent will be responsible for managing space on the Teradata environment. This will include:
            - Providing visibility into what space is being used currently
            - Adding space to databases
            - Removing space from databases
            - Making recommendations on when space should be moved

            ## Database User Management
            Delegate to: DB_User_Agent
            This specialized agent will be responsible for managing users in the Teradata environment. This will include:
            - Monitoring user activity
            - Creating, modifying, and deleting users

            ## Database Object Management
            Delegate to: DB_Object_Agent
            This specialized agent will be responsible for managing database objects in the Teradata environment. This will include:
            - Monitoring object usage and performance
            - Creating, modifying, and deleting database objects
            - Managing object permissions and access
            

            ## Your Management Responsibilities:

            1. Clearly explain the DBA process to the creator
            2. Identify the task and delegate to the appropriate specialized agent
            3. Monitor the progress of the specialized agents
                - Database Security Managemet
                - Database Space Management
                - Database User Management
                - Database Object Management

            ## Communication Guidelines:

            - Be concise but informative in your explanations
            - Clearly indicate which task the process is currently performing
            - When delegating to a specialized agent, clearly state that you're doing so

            Remember, your job is to orchestrate the process - let the specialized agents handle their specific tasks.
            """  
        )
    )

    return agent


# Create the agent asynchronously
root_agent = asyncio.run(create_agent())
