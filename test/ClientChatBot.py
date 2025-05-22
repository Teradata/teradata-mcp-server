
#  This script uses stdio to connect to a Teradata MCP server and interact with it using the Pydantic AI library.
#  Ensure that the .env file SSE=False
#

import os
import boto3
from dotenv import load_dotenv
from pydantic_ai import Agent
from pydantic_ai.models.bedrock import BedrockConverseModel
from pydantic_ai.providers.bedrock import BedrockProvider
from pydantic_ai.mcp import MCPServerStdio
import asyncio


load_dotenv(override=True)

# connecting to AWS requires a client be created
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

bedrock_client = boto3.client(
    "bedrock-runtime",
    aws_access_key_id=temp_credentials["AccessKeyId"],
    aws_secret_access_key=temp_credentials["SecretAccessKey"],
    aws_session_token=temp_credentials["SessionToken"],
    region_name='us-east-1'
)

model = BedrockConverseModel(
    'anthropic.claude-3-5-sonnet-20240620-v1:0',
    provider=BedrockProvider(bedrock_client=bedrock_client),
)

td_mcp_server = MCPServerStdio('uv', ["--directory", "/Users/Daniel.Tehan/Code/MCP/teradata-mcp-server", "run", "teradata-mcp-server"])

system_prompt = """Help user with Teradata tasks"""
agent = Agent(model, instrument=True, system_prompt=system_prompt, mcp_servers=[td_mcp_server])


async def main():
    async with agent.run_mcp_servers():
        result = await agent.run("hello!")
        while True:
            print(f"\n{result.output}")
            user_input = input("\n> ")
            if user_input.lower() in ["exit", "quit"]:
                break
            result = await agent.run(user_input, 
                                     message_history=result.new_messages())

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
