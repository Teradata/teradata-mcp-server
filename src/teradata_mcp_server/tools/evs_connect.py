# ── evs_connect.py ────────────────────────────────────────────
import os, logging
from urllib.parse import urlparse
from functools import lru_cache

from teradataml import create_context, get_context, set_auth_token
from teradatagenai import VectorStore, VSManager
from .td_connect import TDConn                    # ← 你的 DB 封装

logger = logging.getLogger("evs_connect")        # 拼写修正

# -------------------------------------------------------------
#  单例：Enterprise Vector Store
# -------------------------------------------------------------
@lru_cache(maxsize=1)
def get_evs() -> VectorStore:
    # 1) teradataml context（只建一次）
    if get_context() is None:
        dbc = TDConn()                           # 若已连会复用
        p = urlparse(dbc.connection_url)                    # TDConn 把 URL 存在 .url
        create_context(host=p.hostname,
                       username=p.username,
                       password=p.password)
        logger.info("teradataml context ready.")

    # 2) VS 鉴权
    set_auth_token(
        base_url=os.getenv("TD_BASE_URL"),
        pat_token=os.getenv("TD_PAT"),
        pem_file=os.getenv("TD_PEM") or None,
    )
    VSManager.health()

    # 3) 拿 Enterprise Vector Store（已由 DBA 创建）
    vs_name = os.getenv("VS_NAME","vs_demo")
    vs = VectorStore(vs_name)
    df = VSManager.list().to_pandas()   # 先 materialize 成 pandas
    if vs_name not in df["vs_name"].values:
        raise RuntimeError(
            f"Vector store '{vs_name}' 不存在，请先在 DB 侧创建。")
    logger.info("VectorStore '%s' ready.", vs_name)
    return vs


# -------------------------------------------------------------
#  掉线后清缓存 + 断会话 → 自动重连
# -------------------------------------------------------------
def refresh_evs() -> VectorStore:
    VSManager.disconnect()           # 释放旧 VS 会话
    get_evs.cache_clear()            # 清 lru_cache
    return get_evs()
