import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional
import base64
import hashlib
import re
from typing import Tuple, Mapping


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

# ---------------------------------------------------------------------------
# Auth header utilities (parsing + helpers)
# ---------------------------------------------------------------------------

def parse_auth_header(auth_header: Optional[str]) -> tuple[str, str]:
    """Parse an HTTP Authorization header into (scheme, value).

    Returns ("", "") if header is missing or malformed. Scheme is lowercased
    and stripped. Value is stripped (but not decoded).
    """
    if not auth_header:
        return "", ""
    try:
        scheme, _, value = auth_header.partition(" ")
        return (scheme.strip().lower(), value.strip())
    except Exception:
        return "", ""


def compute_auth_token_sha256(auth_header: Optional[str]) -> Optional[str]:
    """Return a hex SHA-256 over the *value* portion of Authorization.

    Useful for query band audit without storing raw secrets. Returns None if
    the header is missing or empty.
    """
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
    """Decode a Basic credential value into (username, secret).

    Accepts the *credential* portion (i.e., after "Basic "). Returns (None, None)
    on any decoding error or if the payload does not contain a colon.
    """
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


def looks_like_jwt(s: Optional[str]) -> bool:
    """Heuristic check: does the string look like a JWT (three base64url parts)?"""
    return bool(s and s.count(".") == 2)


def b64url_decode(s: str) -> bytes:
    """Decode a base64url string with optional padding."""
    pad = (-len(s)) % 4
    if pad:
        s = s + ("=" * pad)
    return base64.urlsafe_b64decode(s)


def extract_unverified_jwt_claims(token: str) -> dict:
    """Extract JWT claims *without* verifying the signature.

    Returns an empty dict if parsing fails. Use only for non-security-critical
    mapping (e.g., selecting the db username after the DB has already validated
    the token via LOGMECH=JWT) or logging metadata.
    """
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return {}
        payload_b64 = parts[1]
        data = b64url_decode(payload_b64)
        return json.loads(data.decode("utf-8"))
    except Exception:
        return {}


def map_principal_from_claims(
    claims: Mapping[str, Any] | None,
    strategy: str = "claim:preferred_username",
    fallback: Optional[str] = None,
) -> Optional[str]:
    """Map an identity (db username) from JWT claims using a strategy.

    Strategies:
      - "claim:<name>": return claims[<name>] if present
      - "transform:sam": take preferred_username/upn/sub, strip domain or realm (split on '@' or '\\')
      - "username": return fallback
    If mapping fails, returns fallback.
    """
    if not claims:
        return fallback

    principal: Optional[str] = None
    if strategy.startswith("claim:"):
        claim_name = strategy.split(":", 1)[1]
        principal = claims.get(claim_name) if isinstance(claims, dict) else None
    elif strategy.startswith("transform:"):
        kind = strategy.split(":", 1)[1]
        if kind == "sam":
            val = None
            if isinstance(claims, dict):
                val = claims.get("preferred_username") or claims.get("upn") or claims.get("sub")
            if val is not None:
                principal = re.split(r"[@\\]", str(val))[0]
    elif strategy == "username":
        principal = fallback

    return principal or fallback


def infer_logmech_from_header(auth_header: Optional[str], default_basic_logmech: str = "LDAP") -> tuple[str, str]:
    """Infer Teradata LOGMECH and the credential payload based on the header.

    Returns (logmech, payload) where:
      - If scheme == 'bearer' → ("JWT", <token>)
      - If scheme == 'basic'  → (default_basic_logmech, <secret>)
        (The caller already has the username from parse_basic_credentials if needed.)
      - Otherwise → ("", "")
    """
    scheme, value = parse_auth_header(auth_header)
    if scheme == "bearer" and value:
        return "JWT", value
    if scheme == "basic" and value:
        # Caller should decode to get (user, secret); we return the secret as payload
        return default_basic_logmech.upper(), value
    return "", ""
