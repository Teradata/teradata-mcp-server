from __future__ import annotations

def sanitize_qb_value(val: str | None) -> str:
    if val is None:
        return ""
    s = str(val)
    s = s.replace(";", "_")
    s = s.replace("'", "''")
    return s.strip()


def build_queryband(
    application: str,
    profile: str | None,
    process_id: str,
    tool_name: str,
    request_context: object | None,
) -> str:
    parts: list[str] = []

    def add(key: str, value):
        if value is None:
            return
        parts.append(f"{key}={sanitize_qb_value(value)};")

    add("APPLICATION", application)
    add("PROFILE", profile)
    add("PROCESS_ID", process_id)
    add("TOOL_NAME", tool_name)

    if request_context is not None:
        add("REQUEST_ID", getattr(request_context, "request_id", None))
        add("SESSION_ID", getattr(request_context, "session_id", None))
        add("TENANT", getattr(request_context, "tenant", None))
        fwd = getattr(request_context, "forwarded_for", None)
        client_ip = None
        if isinstance(fwd, str) and fwd:
            client_ip = fwd.split(",")[0].strip()
        add("CLIENT_IP", client_ip)
        add("USER_AGENT", getattr(request_context, "user_agent", None))
        add("AUTH_SCHEME", getattr(request_context, "auth_scheme", None))
        auth_hash = getattr(request_context, "auth_token_sha256", None)
        if isinstance(auth_hash, str) and auth_hash:
            add("AUTH_HASH", auth_hash[:12])
        assume_user = getattr(request_context, "assume_user", None)
        if assume_user:
            add("PROXYUSER", assume_user)

    return "".join(parts)

