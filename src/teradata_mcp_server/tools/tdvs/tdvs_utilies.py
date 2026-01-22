import logging
import os
from functools import lru_cache
from typing import Union
from urllib.parse import urlparse

import requests
from teradatagenai import VSManager
from teradataml import create_context, get_context, set_auth_token

from ..td_connect import TDConn
from .constants import DATABASE_URI, TD_PAT_TOKEN, TD_PEM_FILE, TD_VS_BASE_URL

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
log_level = logging._nameToLevel[LOG_LEVEL]
logger = logging.getLogger(__name__)
logger.setLevel(log_level)

# --------------- VS Service Utilies -----------------------------#
@lru_cache(maxsize=1)
def create_teradataml_context():
    """
    Create the appropriate credentials for TeradataML context based on the type of authentication.
    """
    td_conn = TDConn()
    if DATABASE_URI is None:
        raise ValueError("DATABASE_URI environment variable is not set.")

    conn_url = urlparse(DATABASE_URI)
    if get_context() is None:
        create_context(host=conn_url.hostname,
                       username=conn_url.username,
                       password=conn_url.password)
        logger.info("teradataml context ready.")
    else:
        logger.info("teradataml context already exists.")

    if TD_VS_BASE_URL is None:
        raise ValueError("TD_BASE_URL environment variable is not set.")

    logger.info(f"Vector Store base URL: {TD_VS_BASE_URL}")
    if TD_PAT_TOKEN is not None and TD_PEM_FILE is not None:
        set_auth_token(
            base_url=TD_VS_BASE_URL,
            pat_token=TD_PAT_TOKEN,
            pem_file=TD_PEM_FILE
        )
    else:
        set_auth_token(
            base_url=TD_VS_BASE_URL,
            username=conn_url.username,
            password=conn_url.password
        )


# -------------------------------------------------------------
#  Reconnect logic: clear cache + disconnect session → auto-reconnect
# -------------------------------------------------------------
def refresh_vectorstore_session():
    VSManager.disconnect()                             # Release the previous Vector Store session
    create_teradataml_context.cache_clear()            # Clear the LRU cache
    return create_teradataml_context()                 # Re-establish and return the new session
