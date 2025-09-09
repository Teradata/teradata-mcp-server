"""Utilities for Teradata tools package.

Exposes helper functions used across tools implementations. This package
replaces the older single-module utils.py to avoid name conflicts and to group
protocol-agnostic helpers together.
"""

from __future__ import annotations

import base64
import hashlib
import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from .queryband import build_queryband, sanitize_qb_value  # noqa: F401


# -------------------- Serialization & response helpers -------------------- #
def serialize_teradata_types(obj: Any) -> Any:
    """Convert Teradata-specific types to JSON serializable formats."""
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    return str(obj)


def rows_to_json(cursor_description: Any, rows: list[Any]) -> list[dict[str, Any]]:
    """Convert DB rows into JSON objects using column names as keys."""
    if not cursor_description or not rows:
        return []
    columns = [col[0] for col in cursor_description]
    out: list[dict[str, Any]] = []
    for row in rows:
        out.append({col: serialize_teradata_types(val) for col, val in zip(columns, row)})
    return out


def create_response(data: Any, metadata: dict[str, Any] | None = None, error: dict[str, Any] | None = None) -> str:
    """Create a standardized JSON response structure."""
    if error:
        resp = {"status": "error", "message": error}
        if metadata:
            resp["metadata"] = metadata
        return json.dumps(resp, default=serialize_teradata_types)
    resp = {"status": "success", "results": data}
    if metadata:
        resp["metadata"] = metadata
    return json.dumps(resp, default=serialize_teradata_types)


# ------------------------------ Auth helpers ------------------------------ #
def parse_auth_header(auth_header: Optional[str]) -> tuple[str, str]:
    """Parse an HTTP Authorization header into (scheme, value).

    Returns ("", "") if header is missing or malformed. Scheme is lowercased
    and stripped. Value is stripped (but not decoded).
    """
    if not auth_header:
        return "", ""
    try:
        scheme, _, value = auth_header.partition(" ")
        return scheme.strip().lower(), value.strip()
    except Exception:
        return "", ""


def compute_auth_token_sha256(auth_header: Optional[str]) -> Optional[str]:
    """Return a hex SHA-256 over the value portion of Authorization header."""
    scheme, value = parse_auth_header(auth_header)
    if not value:
        return None
    try:
        h = hashlib.sha256()
        h.update(value.encode("utf-8"))
        return h.hexdigest()
    except Exception:
        return None


def parse_basic_credentials(b64_value: str) -> tuple[Optional[str], Optional[str]]:
    """Decode a Basic credential value into (username, secret)."""
    try:
        raw = base64.b64decode(b64_value).decode("utf-8")
        if ":" not in raw:
            return None, None
        user, secret = raw.split(":", 1)
        user = user.strip()
        secret = secret.strip()
        if not user or not secret:
            return None, None
        return user, secret
    except Exception:
        return None, None


def infer_logmech_from_header(auth_header: Optional[str], default_basic_logmech: str = "LDAP") -> tuple[str, str]:
    """Infer LOGMECH and the credential payload based on the header.

    Returns (logmech, payload) where:
      - If scheme == 'bearer' → ("JWT", <token>)
      - If scheme == 'basic'  → (default_basic_logmech, <secret>)
      - Otherwise → ("", "")
    """
    scheme, value = parse_auth_header(auth_header)
    if scheme == "bearer" and value:
        return "JWT", value
    if scheme == "basic" and value:
        return default_basic_logmech.upper(), value
    return "", ""

