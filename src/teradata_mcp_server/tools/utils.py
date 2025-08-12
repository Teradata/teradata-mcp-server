import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional


def serialize_teradata_types(obj: Any) -> Any:
    """Convert Teradata-specific types to JSON serializable formats"""
    if isinstance(obj, date | datetime):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    return str(obj)

def rows_to_json(cursor_description: Any, rows: list[Any]) -> list[dict[str, Any]]:
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

def create_response(data: Any, metadata: dict[str, Any] | None = None, error: dict[str, Any] | None = None) -> str:
    """Create a standardized JSON response structure"""
    if error:
        if metadata:
            response = {
                "status": "error",
                "message": error,
                "metadata": metadata,
            }
        else:
            response = {
                "status": "error",
                "message": error
            }
    elif metadata:
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
