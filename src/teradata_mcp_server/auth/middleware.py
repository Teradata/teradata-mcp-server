"""
Session management for Teradata MCP Server.

Provides functions to create and manage user sessions from HTTP headers
without requiring complex middleware integration.
"""

import logging
from typing import Any, Optional, Dict

try:
    from mcp.server.fastmcp.dependencies import get_http_headers, get_http_request
except ImportError:
    # Fallback for different FastMCP versions
    def get_http_headers():
        return {}
    
    def get_http_request():
        return None

from .session_context import UserSession, session_manager, current_session

logger = logging.getLogger("teradata_mcp_server.auth")

class SessionMiddleware:
    """Session management helper for Teradata MCP Server."""
    
    def __init__(self, require_auth: bool = False):
        """
        Initialize session middleware.
        
        Args:
            require_auth: If True, reject requests without valid authentication
        """
        self.require_auth = require_auth
        logger.info(f"SessionMiddleware initialized (require_auth={require_auth})")
    
    def create_session_from_current_request(self) -> UserSession:
        """
        Create session from current HTTP request context.
        
        Returns:
            UserSession object with extracted authentication and context
        """
        try:
            # Get HTTP request information using FastMCP dependencies
            headers_dict = get_http_headers()
            
            # Validate we have some headers (not just empty dict)
            if not headers_dict:
                logger.debug("No HTTP headers available, creating anonymous session")
                headers_dict = {}
            
            # Get client IP if available
            client_ip = None
            try:
                request = get_http_request()
                if request and hasattr(request, 'client') and request.client:
                    client_ip = request.client.host
            except Exception as e:
                logger.debug(f"Could not get client IP: {e}")
            
            # Create session from headers
            session = session_manager.create_session_from_headers(
                headers=headers_dict,
                client_ip=client_ip
            )
            
            # Check authentication requirement
            if self.require_auth and not session.is_authenticated():
                logger.warning("Request rejected: authentication required", extra={
                    "session_id": session.session_id,
                    "client_ip": client_ip,
                    "has_auth_headers": any(h.lower().startswith('authorization') or h.lower().startswith('x-') 
                                          for h in headers_dict.keys())
                })
                raise ValueError("Authentication required")
            
            # Update activity timestamp
            session.update_activity()
            
            # Log successful session creation
            logger.info("Session created from request", extra={
                "session": session.to_dict(),
                "request_headers": list(headers_dict.keys())
            })
            
            return session
            
        except Exception as e:
            if self.require_auth:
                raise
            
            # Create anonymous session as fallback for backward compatibility
            logger.debug(f"Failed to create authenticated session, using anonymous: {e}")
            fallback_session = session_manager.create_session_from_headers(
                headers={},
                client_ip=None
            )
            logger.info("Created anonymous fallback session", extra={
                "session": fallback_session.to_dict()
            })
            return fallback_session
    
    def get_current_session(self) -> Optional[UserSession]:
        """Get the current session from context."""
        return current_session.get()

# Global middleware instance
session_middleware = SessionMiddleware()

def ensure_session() -> UserSession:
    """
    Ensure a session exists for the current request.
    
    This is the main entry point for tools to get session context.
    Creates a session from the current HTTP request if one doesn't exist.
    
    Returns:
        UserSession object (authenticated or anonymous)
    """
    # Check if we already have a session in context
    existing_session = current_session.get()
    if existing_session:
        existing_session.update_activity()
        return existing_session
    
    # Create new session from current request
    try:
        return session_middleware.create_session_from_current_request()
    except Exception as e:
        logger.debug(f"Could not create session from request context: {e}")
        # Return a minimal anonymous session as fallback
        import uuid
        from .session_context import UserSession
        fallback_session = UserSession(
            session_id=str(uuid.uuid4()),
            user_id=None,
            username=None,
            auth_type=None
        )
        current_session.set(fallback_session)
        return fallback_session