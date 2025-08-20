"""
Authentication and session management module for Teradata MCP Server.

This module provides session-aware database connections, authentication extraction
from HTTP headers, and request tracing capabilities using Teradata QueryBand.
"""

from .session_context import UserSession, SessionManager, current_session
from .middleware import SessionMiddleware, ensure_session
from .queryband import QueryBandBuilder, RequestTracer, request_tracer

__all__ = [
    'UserSession',
    'SessionManager', 
    'current_session',
    'SessionMiddleware',
    'ensure_session',
    'QueryBandBuilder',
    'RequestTracer',
    'request_tracer'
]