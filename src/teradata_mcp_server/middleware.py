from __future__ import annotations

"""Shared RequestContext middleware.

This middleware extracts per-request context (headers, auth, ids) and stores it
in the FastMCP context state under the key "request_context" so that tools can
access it at execution time (e.g., to build Teradata QueryBand).

Behavior by transport:
- stdio: fast-path, generates minimal request/session identifiers, skips headers/auth
- http/sse: parses headers, enforces auth when configured, caches principals per session
"""

import hashlib
import os
import re
from dataclasses import dataclass
from typing import Optional, Callable
from uuid import uuid4

from fastmcp.server.dependencies import get_http_headers
from fastmcp.server.middleware import Middleware, MiddlewareContext, CallNext
import mcp.types as mt


@dataclass
class RequestContext:
    headers: dict[str, str]
    request_id: str | None = None
    session_id: str | None = None
    forwarded_for: str | None = None
    user_agent: str | None = None
    tenant: Optional[str] = None
    auth_scheme: str | None = None
    auth_token_sha256: str | None = None
    user_id: Optional[str] = None
    client_session_id: str | None = None
    correlation_id: str | None = None
    assume_user: Optional[str] = None


class RequestContextMiddleware(Middleware):
    def __init__(
        self,
        logger,
        auth_cache,
        tdconn_supplier: Callable[[], object],
        auth_mode: str = "none",
        transport: str | None = None,
        registry_load_callback: Optional[Callable[[Optional[str]], Optional[str]]] = None,
    ) -> None:
        self.logger = logger
        self.auth_cache = auth_cache
        self.tdconn_supplier = tdconn_supplier
        self.auth_mode = (auth_mode or "none").lower()
        self.transport = (transport or "stdio").lower()
        self.registry_load_callback = registry_load_callback
        self.registry_tools_loaded_ts: Optional[str] = None
        self.logger.info(f"RequestContextMiddleware initialized: transport={self.transport}, auth_mode={self.auth_mode}, registry_callback={registry_load_callback is not None}")

    async def on_request(self, context: MiddlewareContext, call_next):
        self.logger.info(f"on_request: Called with transport={self.transport}")
        # stdio: generate lightweight context; do not touch stdout
        if self.transport == "stdio":
            try:
                rc = RequestContext(
                    headers={},
                    request_id=uuid4().hex,
                    session_id=(getattr(context.fastmcp_context, "session_id", None) if context.fastmcp_context else uuid4().hex),
                )
                if context.fastmcp_context:
                    context.fastmcp_context.set_state("request_context", rc)
                else:
                    self.logger.warning("No FastMCP context available - RequestContext not stored")
            except Exception as e:
                self.logger.debug(f"Error creating stdio RequestContext: {e}")
            return await call_next(context)

        # HTTP/SSE path: Extract headers
        try:
            raw_headers = get_http_headers() or {}
            headers = {str(k).lower(): v for k, v in dict(raw_headers).items()}
        except Exception as e:
            self.logger.debug(f"Error parsing headers: {e}")
            headers = {}

        auth_mode = self.auth_mode
        correlation_id = headers.get("x-correlation-id") or headers.get("correlation-id")
        client_session_id = headers.get("x-session-id")
        user_agent = headers.get("user-agent")
        tenant = headers.get("x-td-tenant") or headers.get("x-tenant")
        forwarded_for = headers.get("x-forwarded-for")

        auth_hdr = headers.get("authorization")
        auth_scheme = None
        auth_token_sha256 = None
        if auth_hdr:
            parts = auth_hdr.split(" ", 1)
            auth_scheme = parts[0]
            token = parts[1] if len(parts) > 1 else ""
            auth_token_sha256 = hashlib.sha256(token.encode("utf-8")).hexdigest()

        # request_id
        try:
            if context.fastmcp_context and getattr(context.fastmcp_context, "request_id", None):
                request_id = context.fastmcp_context.request_id
            else:
                request_id = uuid4().hex
        except Exception as e:
            self.logger.debug(f"Error getting request_id from context: {e}")
            request_id = uuid4().hex

        # session_id
        try:
            mcp_session = None
            if context.fastmcp_context:
                sid_attr = getattr(context.fastmcp_context, "session_id", None)
                mcp_session = sid_attr() if callable(sid_attr) else sid_attr
                self.logger.debug(
                    f"FastMCP context session_id: {mcp_session}, context id: {id(context.fastmcp_context)}"
                )
        except Exception as e:
            self.logger.debug(f"Error getting session_id from context: {e}")
            mcp_session = None
        session_id = mcp_session or request_id

        # AUTH
        assume_user = None
        if auth_mode == "none":
            assume_user_value = headers.get("x-assume-user")
            if assume_user_value is not None:
                if re.match(r"^[A-Za-z0-9_]{1,30}$", assume_user_value):
                    assume_user = assume_user_value
                    self.logger.info(f"AUTH_MODE=none: Using X-Assume-User: {assume_user}")
                else:
                    self.logger.warning("Invalid X-Assume-User header value; ignoring")
        elif auth_mode == "basic":
            if not auth_hdr or not auth_token_sha256:
                self.logger.warning("AUTH_MODE=basic but Authorization header is missing")
                raise PermissionError("Authentication required")

            cached_principal = self.auth_cache.get(session_id, auth_token_sha256)
            if cached_principal:
                assume_user = cached_principal
                self.logger.debug(f"Using cached principal for session {session_id}: {assume_user}")
            else:
                # Validate via TDConn helper
                scheme = (auth_scheme or "").lower()
                if scheme not in ("basic", "bearer"):
                    self.logger.warning(f"AUTH_MODE=basic but unsupported auth scheme: {auth_scheme}")
                    raise PermissionError("Unsupported auth scheme for basic mode")

                tdconn = self.tdconn_supplier()
                try:
                    validated_user = tdconn.validate_auth_header(auth_hdr)
                except Exception as e:
                    from teradata_mcp_server.tools.auth_validation import (
                        RateLimitExceededError, InvalidUsernameError, InvalidTokenFormatError,
                    )
                    if isinstance(e, RateLimitExceededError):
                        self.logger.warning(f"Rate limit exceeded for auth attempt: {e}")
                        raise PermissionError("Too many authentication attempts. Please try again later.")
                    elif isinstance(e, (InvalidUsernameError, InvalidTokenFormatError)):
                        self.logger.warning(f"Invalid auth format: {e}")
                        raise PermissionError("Invalid authentication format")
                    else:
                        self.logger.error(f"Validation error in TDConn.validate_auth_header: {e}")
                        validated_user = None
                if not validated_user:
                    raise PermissionError("Invalid credentials")
                assume_user = validated_user
                self.logger.info(
                    f"AUTH_MODE=basic: Validated identity of user {assume_user} from database."
                )
                self.auth_cache.set(session_id, validated_user, auth_token_sha256)

        # Build and set RequestContext in FastMCP state
        try:
            rc = RequestContext(
                headers=headers,
                request_id=request_id,
                session_id=session_id,
                forwarded_for=forwarded_for,
                user_agent=user_agent,
                tenant=tenant,
                auth_scheme=auth_scheme,
                auth_token_sha256=auth_token_sha256,
                client_session_id=client_session_id,
                correlation_id=correlation_id,
                assume_user=assume_user,
                user_id=assume_user,
            )
            if context.fastmcp_context:
                context.fastmcp_context.set_state("request_context", rc)
            else:
                self.logger.warning("No FastMCP context available - RequestContext not stored")
        except Exception as e:
            self.logger.debug(f"Error creating RequestContext: {e}")

        return await call_next(context)

    async def on_initialize(
        self,
        context: MiddlewareContext[mt.InitializeRequest],
        call_next: CallNext[mt.InitializeRequest, None],
    ) -> None:
        """
        Hook called when a client session initializes.

        This is the perfect place to refresh registry tools, as it happens once per session
        and after the database connection is available.
        """
        self.logger.info(f"on_initialize: Session initializing (registry_load_callback configured: {self.registry_load_callback is not None})")

        # Trigger registry tool refresh if callback is configured
        if self.registry_load_callback:
            try:
                self.logger.info(f"on_initialize: Refreshing registry tools (last_load_ts: {self.registry_tools_loaded_ts})")
                # Call the registry load callback with current timestamp watermark
                new_ts = self.registry_load_callback(self.registry_tools_loaded_ts)
                if new_ts:
                    self.registry_tools_loaded_ts = new_ts
                    self.logger.info(f"on_initialize: Registry tools refreshed successfully, new watermark: {new_ts}")
                else:
                    self.logger.info("on_initialize: Registry refresh completed, no new timestamp returned")
            except Exception as e:
                self.logger.error(f"on_initialize: Error refreshing registry tools: {e}", exc_info=True)
        else:
            self.logger.info("on_initialize: No registry_load_callback configured, skipping registry refresh")

        return await call_next(context)

