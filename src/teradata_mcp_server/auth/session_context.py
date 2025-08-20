"""
Session context management for Teradata MCP Server.

Provides session tracking, user identification, and authentication context
that persists across tool calls within a single request.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from contextvars import ContextVar
import uuid
from datetime import datetime
import logging

logger = logging.getLogger("teradata_mcp_server.auth")

@dataclass
class UserSession:
    """Represents a user session with authentication and context information."""
    
    session_id: str
    user_id: Optional[str] = None
    username: Optional[str] = None
    auth_token: Optional[str] = None
    auth_type: Optional[str] = None
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_authenticated(self) -> bool:
        """Check if the session has valid authentication."""
        return self.user_id is not None and self.auth_token is not None
    
    def update_activity(self):
        """Update the last activity timestamp."""
        self.last_activity = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary for logging."""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "username": self.username,
            "auth_type": self.auth_type,
            "client_ip": self.client_ip,
            "authenticated": self.is_authenticated(),
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat()
        }

# Global context variable for the current session
current_session: ContextVar[Optional[UserSession]] = ContextVar('current_session', default=None)

class SessionManager:
    """Manages user sessions and authentication extraction from HTTP headers."""
    
    def __init__(self):
        self.sessions: Dict[str, UserSession] = {}
        logger.debug("SessionManager initialized")
    
    def _extract_bearer_token_auth(self, headers: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Extract authentication from Bearer token in Authorization header."""
        auth_header = headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            return None
        
        token = auth_header.replace("Bearer ", "")
        
        # For Phase 1, we'll do basic token extraction without JWT validation
        # In Phase 2, we'll add proper JWT validation with signature verification
        try:
            # Simple base64 decode attempt to extract basic info
            # This is a placeholder - real implementation would validate JWT signature
            import base64
            import json
            
            # Try to decode JWT payload (without signature verification for Phase 1)
            parts = token.split('.')
            if len(parts) == 3:  # JWT format
                # Add padding if needed
                payload = parts[1]
                padding = 4 - len(payload) % 4
                if padding != 4:
                    payload += '=' * padding
                
                decoded_bytes = base64.urlsafe_b64decode(payload)
                decoded = json.loads(decoded_bytes)
                
                return {
                    "user_id": decoded.get("sub"),
                    "username": decoded.get("preferred_username") or decoded.get("username"),
                    "token": token,
                    "auth_type": "jwt_bearer",
                    "claims": decoded
                }
        except Exception as e:
            logger.debug(f"Could not decode Bearer token as JWT: {e}")
        
        # Fallback: treat as opaque token
        return {
            "user_id": f"bearer_user_{hash(token) % 10000}",
            "username": f"bearer_user_{hash(token) % 10000}",
            "token": token,
            "auth_type": "bearer_token"
        }
    
    def _extract_service_account_auth(self, headers: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Extract service account authentication from custom headers."""
        service_account = headers.get("x-service-account")
        service_token = headers.get("x-service-token")
        
        if service_account and service_token:
            return {
                "user_id": service_account,
                "username": service_account,
                "token": service_token,
                "auth_type": "service_account"
            }
        return None
    
    def _extract_api_key_auth(self, headers: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Extract API key authentication from custom headers."""
        api_key = headers.get("x-api-key")
        user_id = headers.get("x-user-id")
        
        if api_key:
            return {
                "user_id": user_id or f"api_user_{hash(api_key) % 10000}",
                "username": user_id or f"api_user_{hash(api_key) % 10000}",
                "token": api_key,
                "auth_type": "api_key"
            }
        return None
    
    def extract_auth_from_headers(self, headers: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Extract authentication information from HTTP headers."""
        # Try different authentication methods in order of preference
        auth_extractors = [
            self._extract_bearer_token_auth,
            self._extract_service_account_auth,
            self._extract_api_key_auth
        ]
        
        for extractor in auth_extractors:
            auth_info = extractor(headers)
            if auth_info:
                logger.debug(f"Extracted auth using {extractor.__name__}: {auth_info.get('auth_type')}")
                return auth_info
        
        logger.debug("No authentication found in headers")
        return None
    
    def create_session_from_headers(self, headers: Dict[str, str], client_ip: Optional[str] = None) -> UserSession:
        """Create a new session from HTTP headers and request information."""
        # Get or generate session ID
        session_id = headers.get("x-session-id") or str(uuid.uuid4())
        
        # Extract authentication
        auth_info = self.extract_auth_from_headers(headers)
        
        # Create session
        session = UserSession(
            session_id=session_id,
            user_id=auth_info.get("user_id") if auth_info else None,
            username=auth_info.get("username") if auth_info else None,
            auth_token=auth_info.get("token") if auth_info else None,
            auth_type=auth_info.get("auth_type") if auth_info else None,
            client_ip=client_ip,
            user_agent=headers.get("user-agent"),
            metadata=auth_info or {}
        )
        
        # Store session
        self.sessions[session_id] = session
        
        # Set in context
        current_session.set(session)
        
        logger.info("Session created", extra={"session": session.to_dict()})
        return session
    
    def get_session(self, session_id: str) -> Optional[UserSession]:
        """Get session by ID."""
        return self.sessions.get(session_id)
    
    def cleanup_expired_sessions(self, max_age_hours: int = 24):
        """Clean up sessions older than max_age_hours."""
        cutoff = datetime.utcnow().replace(hour=datetime.utcnow().hour - max_age_hours)
        expired_sessions = [
            session_id for session_id, session in self.sessions.items()
            if session.last_activity < cutoff
        ]
        
        for session_id in expired_sessions:
            del self.sessions[session_id]
            
        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")

# Global session manager instance
session_manager = SessionManager()