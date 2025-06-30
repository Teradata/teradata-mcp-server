# ── evs_connect.py ────────────────────────────────────────────
import os, logging
from urllib.parse import urlparse
from functools import lru_cache

from teradataml import create_context, get_context, set_auth_token
from teradatagenai import VectorStore, VSManager
from .td_connect import TDConn                 
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("evs_connect")

# -------------------------------------------------------------
#  Singleton：Enterprise Vector Store
# -------------------------------------------------------------
@lru_cache(maxsize=1)
def get_evs() -> VectorStore:

    if get_context() is None:
        dbc = TDConn()                           
        p = urlparse(dbc.connection_url)                    
        create_context(host=p.hostname,
                       username=p.username,
                       password=p.password)
        logger.info("teradataml context ready.")


    set_auth_token(
        base_url=os.getenv("TD_BASE_URL"),
        pat_token=os.getenv("TD_PAT"),
        pem_file=os.getenv("TD_PEM") or None,
    )
    VSManager.health()


    vs_name = os.getenv("VS_NAME","vs_demo")
    vs = VectorStore(vs_name)
    df = VSManager.list().to_pandas() 
    if vs_name not in df["vs_name"].values:
        raise RuntimeError(
            f"Vector store '{vs_name}' does not exist. Please create it on the Vector Store side first.")
    logger.info("VectorStore '%s' ready.", vs_name)
    return vs


# -------------------------------------------------------------
#  Reconnect logic: clear cache + disconnect session → auto-reconnect
# -------------------------------------------------------------
def refresh_evs() -> VectorStore:
    VSManager.disconnect()           # Release the previous Vector Store session
    get_evs.cache_clear()            # Clear the LRU cache
    return get_evs()                 # Re-establish and return the new session
