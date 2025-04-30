#  This script uses stdio to connect to a Teradata MCP server and interact with it using the Pydantic AI library.
#  Ensure that the .env file SSE=False
#

from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client

# Create server parameters for stdio connection
server_params = StdioServerParameters(
    command="uv",  # Executable
    args=["--directory", "/Users/Daniel.Tehan/Code/MCP/teradata-mcp-server/src/teradata_mcp_server", "run", "server.py"],  # Optional command line arguments
    env=None,  # Optional environment variables
)


# Optional: create a sampling callback
async def handle_sampling_message(
    message: types.CreateMessageRequestParams,
) -> types.CreateMessageResult:
    return types.CreateMessageResult(
        role="assistant",
        content=types.TextContent(
            type="text",
            text="Hello, world! from model",
        ),
        model="gpt-3.5-turbo",
        stopReason="endTurn",
    )


async def run():
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(
            read, write, sampling_callback=handle_sampling_message
        ) as session:
            # Initialize the connection
            await session.initialize()

            # List available prompts
            prompts = await session.list_prompts()
            print(f"\n\n Prompts:\n  {prompts}\n\n")
            
            # Get a prompt
            prompt = await session.get_prompt(
                "sql_prompt", 
            )
            print(f"\n\n Prompt:\n  {prompt}\n\n")

            # List available resources
            resources = await session.list_resources()
            print(f"\n\n Resources:\n  {resources}\n\n")

            # List available tools
            tools = await session.list_tools()
            print(f"\n\n Tools:\n  {tools}\n\n")

            # Call a tool
            # result = await session.call_tool("execute_sql", arguments={"sql": "sel * from DBC.tablesV;"})
            # print(f"\n\n Tool Results:\n  {result}\n\n")

if __name__ == "__main__":
    import asyncio

    asyncio.run(run())