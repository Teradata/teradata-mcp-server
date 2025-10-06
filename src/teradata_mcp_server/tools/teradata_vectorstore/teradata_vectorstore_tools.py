# ------------------------------------------------------------------------------ #
#  Copyright (C) 2025 by Teradata Corporation.                                   #
#  All Rights Reserved.                                                          #
#                                                                                #
#  File: teradata_vectorstore_tools.py                                           #
#                                                                                #
#  Description:                                                                  #
#    This file has various functions to call by your tools                       #
#                                                                                #
#    Enable LLMs to perform actions through your server                          #
#                                                                                #
#  Tools are a powerful primitive in the Model Context Protocol (MCP) that       #
#  enable servers to expose executable functionality to clients. Through tools,  #
#  LLMs can interact with external systems, perform computations, and take       #
#  actions in the real world.                                                    #
# ------------------------------------------------------------------------------ #
import os
import logging
import json
import yaml
import requests
import pandas as pd

from typing import Union
from teradatagenai import VSManager, VectorStore
from teradataml import remove_context
from teradatagenai import VSManager, VectorStore
from teradatasql import TeradataConnection

from .teradata_vectorstore_utilies import create_teradataml_context
from teradata_mcp_server.tools.utils import create_response

from .types import (
    VectorStoreSimilaritySearch,
    VectorStoreAsk,
    VectorStoreCreate,
    VectorStoreUpdate
)

logger = logging.getLogger("teradata_mcp_server")

# Load YAML
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
with open(f"{BASE_DIR}/teradata_vectorstore_prompts.yaml", "r") as file:
    vs_prompts = yaml.safe_load(file)

def handle_teradata_vectorstore_get_health(conn: TeradataConnection, *args,
    **kwargs,
):
    try:
        create_teradataml_context()
        df = VSManager.health()
        df1 = df.to_pandas()
        data = df1.to_json(orient='records', indent=4)
        metadata = { "tool_name": "teradata_vectorstore_get_health" }
        return create_response(json.loads(data), metadata)
    except Exception as e:
        logger.error(f"Error getting vector store health: {e}")
        return create_response({"error": str(e)}, {"tool_name": "teradata_vectorstore_get_health"})
    

def handle_teradata_vectorstore_list(conn: TeradataConnection, *args,
    **kwargs,):
    try:
        create_teradataml_context()
        df = VSManager.list()
        if df is None:
            data = '[]'
        else:
            df1 = df.to_pandas()
            data = df1.to_json(orient='records', indent=4)
        metadata = { "tool_name": "teradata_vectorstore_list" }
        return create_response(json.loads(data), metadata)
    except Exception as e:
        logger.error(f"Error listing vector stores: {e}")
        return create_response({"error": str(e)}, {"tool_name": "teradata_vectorstore_list"})
    
            
def handle_teradata_vectorstore_get_details(conn: TeradataConnection, vs_name: str, *args,
    **kwargs):
    try:
        create_teradataml_context()
        vs = VectorStore(vs_name)
        df = vs.get_details()
        df1 = df.to_pandas()
        data = df1.to_json(orient='records', indent=4)
        metadata = { "tool_name": "teradata_vectorstore_get_details" }
        return create_response(json.loads(data), metadata)
    except Exception as e:
        logger.error(f"Error getting vector store details for '{vs_name}': {e}")
        return create_response({"error": str(e)}, {"tool_name": "teradata_vectorstore_get_details", "vs_name": vs_name})
    

def handle_teradata_vectorstore_destroy(conn: TeradataConnection, vs_name: str, *args,
    **kwargs):
    try:
        create_teradataml_context()
        vs = VectorStore(vs_name)
        vs.destroy()
        data = f"Vector store '{vs_name}' destroyed successfully."
        metadata = { "tool_name": "teradata_vectorstore_destroy" }
        return create_response(data, metadata)
    except Exception as e:
        logger.error(f"Error destroying vector store '{vs_name}': {e}")
        return create_response({"error": str(e)}, {"tool_name": "teradata_vectorstore_destroy", "vs_name": vs_name})


def handle_teradata_vectorstore_grant_user_permission(conn: TeradataConnection, vs_name: str, user_name: str, permission: str, *args,
    **kwargs):
    try:
        create_teradataml_context()
        vs = VectorStore(vs_name)
        if(permission.upper() == "ADMIN"):
            vs.grant.admin(user_name)
        elif(permission.upper() == "USER"):
            vs.grant.user(user_name)
        else:
            raise ValueError(f"Invalid permission type '{permission}'. Use 'ADMIN' or 'USER'.")
        data = f"User '{user_name}' granted requested permission on vector store '{vs_name}' successfully."
        metadata = { "tool_name": "teradata_vectorstore_grant_user_permission" }
        return create_response(data, metadata)
    except Exception as e:
        logger.error(f"Error granting permission to user '{user_name}' on vector store '{vs_name}': {e}")
        return create_response({"error": str(e)}, {"tool_name": "teradata_vectorstore_grant_user_permission", "vs_name": vs_name, "user_name": user_name})
            
            
def handle_teradata_vectorstore_revoke_user_permission(conn: TeradataConnection, vs_name: str, user_name: str, permission: str, *args,
    **kwargs):
    try:
        create_teradataml_context()
        vs = VectorStore(vs_name)
        if(permission.upper() == "ADMIN"):
            vs.revoke.admin(user_name)
        elif(permission.upper() == "USER"):
            vs.revoke.user(user_name)
        else:
            raise ValueError(f"Invalid permission type '{permission}'. Use 'ADMIN' or 'USER'.")
        data = f"User '{user_name}' revoked requested permission on vector store '{vs_name}' successfully."
        metadata = { "tool_name": "teradata_vectorstore_revoke_user_permission" }
        return create_response(data, metadata)
    except Exception as e:
        logger.error(f"Error revoking permission from user '{user_name}' on vector store '{vs_name}': {e}")
        return create_response({"error": str(e)}, {"tool_name": "teradata_vectorstore_revoke_user_permission", "vs_name": vs_name, "user_name": user_name})
    

def handle_teradata_vectorstore_similarity_search(conn: TeradataConnection, vs_name: str, vs_similaritysearch: VectorStoreSimilaritySearch, *args,
    **kwargs):
    try:
        create_teradataml_context()
        vs = VectorStore(vs_name)
        data = vs.similarity_search(**vs_similaritysearch.model_dump())
        metadata = { "tool_name": "teradata_vectorstore_similarity_search" }
        return create_response(data, metadata)
    except Exception as e:
        logger.error(f"Error performing similarity search on vector store '{vs_name}': {e}")
        return create_response({"error": str(e)}, {"tool_name": "teradata_vectorstore_similarity_search", "vs_name": vs_name})
    
    
def handle_teradata_vectorstore_ask(conn: TeradataConnection, vs_name: str, vsask: VectorStoreAsk, *args,
    **kwargs):
    try:
        create_teradataml_context()
        VSManager.health()
        vs = VectorStore(name=vs_name)
        response = vs.ask(**vsask.model_dump())
        metadata = { "tool_name": "teradata_vectorstore_ask" }
        return create_response(response, metadata)
    except Exception as e:
        logger.error(f"Error asking vector store '{vs_name}': {e}")
        return create_response({"error": str(e)}, {"tool_name": "teradata_vectorstore_ask", "vs_name": vs_name})
            
            
def handle_teradata_vectorstore_create(conn: TeradataConnection, vs_name: str, vs_create: VectorStoreCreate, *args,
    **kwargs):
    try:
        logger.info(f"Starting creation of vector store '{vs_name}'")
        create_teradataml_context()
        vs = VectorStore(name=vs_name)
        create_kwargs = {}
        for(key, value) in vs_create.model_dump().items():
            if value is not None:
                create_kwargs[key] = value
        logger.info(f"Creating vector store '{vs_name}' with parameters: {create_kwargs}")
        response = vs.create(**create_kwargs)
        metadata = { "tool_name": "teradata_vectorstore_create" }
        return create_response(response, metadata)
    except Exception as e:
        logger.error(f"Error creating vector store '{vs_name}': {e}")
        return create_response({"error": str(e)}, {"tool_name": "teradata_vectorstore_create", "vs_name": vs_name})
            

def handle_teradata_vectorstore_update(conn: TeradataConnection, vs_name: str, vs_update: VectorStoreUpdate, *args,
    **kwargs):
    try:
        create_teradataml_context()
        vs = VectorStore(name=vs_name)
        update_kwargs = {}
        for(key, value) in vs_update.model_dump().items():
            if value is not None:
                update_kwargs[key] = value
        
        response = vs.update(**update_kwargs)
        metadata = { "tool_name": "teradata_vectorstore_update" }
        return create_response(response, metadata)
    except Exception as e:
        logger.error(f"Error updating vector store '{vs_name}': {e}")
        return create_response({"error": str(e)}, {"tool_name": "teradata_vectorstore_update", "vs_name": vs_name})

handle_teradata_vectorstore_destroy.__doc__ = vs_prompts['tool_descriptions']['teradata_vectorstore_destroy']
handle_teradata_vectorstore_ask.__doc__ = vs_prompts['tool_descriptions']['teradata_vectorstore_ask']
handle_teradata_vectorstore_create.__doc__ = vs_prompts['tool_descriptions']['teradata_vectorstore_create']
handle_teradata_vectorstore_update.__doc__ = vs_prompts['tool_descriptions']['teradata_vectorstore_update']
handle_teradata_vectorstore_get_health.__doc__ = vs_prompts['tool_descriptions']['teradata_vectorstore_get_health']
handle_teradata_vectorstore_list.__doc__ = vs_prompts['tool_descriptions']['teradata_vectorstore_list']
handle_teradata_vectorstore_get_details.__doc__ = vs_prompts['tool_descriptions']['teradata_vectorstore_get_details']
handle_teradata_vectorstore_grant_user_permission.__doc__ = vs_prompts['tool_descriptions']['teradata_vectorstore_grant_user_permission']
handle_teradata_vectorstore_revoke_user_permission.__doc__ = vs_prompts['tool_descriptions']['teradata_vectorstore_revoke_user_permission']
handle_teradata_vectorstore_similarity_search.__doc__ = vs_prompts['tool_descriptions']['teradata_vectorstore_similarity_search']