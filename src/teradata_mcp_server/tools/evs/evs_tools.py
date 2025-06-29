import logging
from teradatasql import TeradataConnection 
from typing import Optional, Any, Dict, List
import json
from datetime import date, datetime
from decimal import Decimal
from teradata_mcp_server.tools.evs_connect import get_evs

logger = logging.getLogger("teradata_mcp_server")

def serialize_teradata_types(obj: Any) -> Any:
    """Convert Teradata-specific types to JSON serializable formats"""
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    return str(obj)

def rows_to_json(cursor_description: Any, rows: List[Any]) -> List[Dict[str, Any]]:
    """Convert database rows to JSON objects using column names as keys"""
    if not cursor_description or not rows:
        return []
    
    columns = [col[0] for col in cursor_description]
    return [
        {
            col: serialize_teradata_types(value)
            for col, value in zip(columns, row)
        }
        for row in rows
    ]

def create_response(data: Any, metadata: Optional[Dict[str, Any]] = None) -> str:
    """Create a standardized JSON response structure"""
    if metadata:
        response = {
            "status": "success",
            "metadata": metadata,
            "results": data
        }
    else:
        response = {
            "status": "success",
            "results": data
        }

    return json.dumps(response, default=serialize_teradata_types)

#------------------ Do not make changes above  ------------------#


#================================================================
#  Enterprise Vector Store 相关工具
#================================================================


def handle_evs_similarity_search(
    conn: TeradataConnection,        # 保持一致的签名，实际不使用
    question: str,
    top_k: int = 1,
    *args,
    **kwargs,
) -> str:
    """
    在 Enterprise Vector Store 中做相似度检索。
    
    Args:
        question: 待检索的问题
        top_k:    返回前 K 条
    Returns:
        JSON 格式字符串
    """
    logger.debug(f"EVS similarity_search: q='{question}', top_k={top_k}")
    vs = get_evs()
    try:
        results = vs.similarity_search(
            question=question,
            top_k=top_k,
            return_type="json",
        )
        return create_response(
            results,
            metadata={
                "tool_name": "evs_similarity_search",
                "question": question,
                "top_k": top_k,
            },
        )
    except Exception as e:
        logger.error(f"EVS similarity_search failed: {e}")
        return json.dumps({"status": "error", "message": str(e)})


