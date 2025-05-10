# To run this code type the following command in the terminal:
#   adk web
#
#  The followin video is a good overview of ADK and how to use it:
#  https://www.youtube.com/watch?v=P4VFL9nIaIA

import os
import boto3
from google.adk.agents.llm_agent import LlmAgent 
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters
from google.adk.models.lite_llm import LiteLlm

async def create_agent():
    """Gets tools from MCP Server."""
    tools, exit_stack = await MCPToolset.from_server(
        connection_params=StdioServerParameters(
            command='uv',
            args=[
                "--directory",
                "/Users/Daniel.Tehan/Code/MCP/teradata-mcp-server/src/teradata_mcp_server/",
                "run",
                "server.py"
            ],
        )
    )

    # # Using Google model
    # agent = LlmAgent(
    #     model='gemini-2.0-flash',
    #     name='td_agent',
    #     instruction=(
    #       'Help user with Teradata tasks'
    #     ),
    #   tools=tools,
    # )
    # return agent, exit_stack

    # # Using Azure model
    # agent = LlmAgent(
    #     model=LiteLlm(
    #         model='azure/gpt-4o-mini',
    #         api_key=os.getenv('azure_api_key'),
    #         api_base=os.getenv('azure_gpt-4o-mini'),
    #     ),
    #     name='td_agent',
    #     instruction=(
    #       'Help user with Teradata tasks'
    #     ),
    #     tools=tools,
    # )
    # return agent, exit_stack

    # Using Bedrock model
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

    agent = LlmAgent(
        model=LiteLlm(
            model='bedrock/anthropic.claude-3-5-sonnet-20240620-v1:0',  
            aws_access_key_id=temp_credentials["AccessKeyId"],
            aws_secret_access_key=temp_credentials["SecretAccessKey"],
            aws_session_token=temp_credentials["SessionToken"],
            region_name='us-west-2'  # I have to enable the same model in us-west-2, seems there is a hard coded feature 
            ),
        name='td_agent',
        instruction=(
          'Help user with Teradata tasks'
        ),
        tools=tools,
    )
    return agent, exit_stack

root_agent = create_agent()
