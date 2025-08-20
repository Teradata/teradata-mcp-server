"""
QueryBand support for Teradata request tracing and audit.

Provides functionality to build QueryBand strings with session context
and track request execution for audit and debugging purposes.
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from .session_context import UserSession, current_session

logger = logging.getLogger("teradata_mcp_server.auth")

class QueryBandBuilder:
    """Builds Teradata QueryBand strings with session and request context."""
    
    @staticmethod
    def build_queryband(
        session: Optional[UserSession] = None,
        tool_name: Optional[str] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Build QueryBand string with session and execution context.
        
        Args:
            session: User session (defaults to current session from context)
            tool_name: Name of the tool being executed
            additional_context: Additional key-value pairs to include
            
        Returns:
            QueryBand string formatted for Teradata
        """
        bands = []
        session = session or current_session.get()
        
        # Core identification - always present
        bands.append("APPLICATION=teradata-mcp-server")
        bands.append(f"REQUEST_ID={uuid.uuid4().hex[:8]}")
        bands.append(f"TIMESTAMP={datetime.utcnow().strftime('%Y%m%d_%H%M%S')}")
        
        # Session information - if available
        if session:
            if session.user_id:
                # Sanitize user_id for QueryBand (max 64 chars, alphanumeric + underscore)
                clean_user_id = QueryBandBuilder._sanitize_value(session.user_id)[:64]
                bands.append(f"USER_ID={clean_user_id}")
                
            if session.username and session.username != session.user_id:
                clean_username = QueryBandBuilder._sanitize_value(session.username)[:64]
                bands.append(f"USERNAME={clean_username}")
                
            if session.session_id:
                # Use first 16 chars of session ID to stay within QueryBand limits
                clean_session_id = QueryBandBuilder._sanitize_value(session.session_id)[:16]
                bands.append(f"SESSION_ID={clean_session_id}")
                
            if session.client_ip:
                bands.append(f"CLIENT_IP={session.client_ip}")
                
            if session.auth_type:
                clean_auth_type = QueryBandBuilder._sanitize_value(session.auth_type)[:32]
                bands.append(f"AUTH_TYPE={clean_auth_type}")
        else:
            bands.append("USER_ID=anonymous")
            bands.append("AUTH_TYPE=none")
        
        # Tool context
        if tool_name:
            clean_tool_name = QueryBandBuilder._sanitize_value(tool_name)[:64]
            bands.append(f"TOOL_NAME={clean_tool_name}")
        
        # Additional context
        if additional_context:
            for key, value in additional_context.items():
                if len(bands) >= 20:  # Teradata QueryBand has limits
                    logger.debug("QueryBand size limit reached, truncating additional context")
                    break
                    
                clean_key = QueryBandBuilder._sanitize_value(str(key)).upper()[:32]
                clean_value = QueryBandBuilder._sanitize_value(str(value))[:64]
                bands.append(f"{clean_key}={clean_value}")
        
        queryband = ";".join(bands) + ";"
        logger.debug(f"Built QueryBand: {queryband}")
        return queryband
    
    @staticmethod
    def _sanitize_value(value: str) -> str:
        """
        Sanitize value for use in QueryBand.
        
        QueryBand values must be alphanumeric, underscore, or dash.
        Other characters are replaced with underscore.
        """
        if not value:
            return "unknown"
            
        # Replace invalid characters with underscore
        sanitized = ""
        for char in str(value):
            if char.isalnum() or char in ['_', '-']:
                sanitized += char
            else:
                sanitized += '_'
        
        return sanitized or "unknown"

class RequestTracer:
    """Tracks request execution for audit and debugging."""
    
    def __init__(self):
        self.active_requests: Dict[str, Dict[str, Any]] = {}
        logger.debug("RequestTracer initialized")
    
    def start_request(self, tool_name: str, parameters: Optional[Dict[str, Any]] = None) -> str:
        """
        Start tracking a database request.
        
        Args:
            tool_name: Name of the tool being executed
            parameters: Tool parameters (sensitive values will be redacted)
            
        Returns:
            Request ID for tracking
        """
        session = current_session.get()
        request_id = uuid.uuid4().hex[:8]  # Short ID for logging
        
        # Redact sensitive parameters
        safe_parameters = self._redact_sensitive_data(parameters or {})
        
        start_time = datetime.utcnow()
        request_info = {
            "request_id": request_id,
            "tool_name": tool_name,
            "parameters": safe_parameters,
            "session": {
                "session_id": session.session_id if session else None,
                "user_id": session.user_id if session else None,
                "auth_type": session.auth_type if session else None,
                "client_ip": session.client_ip if session else None
            },
            "start_time": start_time,
            "start_time_iso": start_time.isoformat(),
            "status": "running"
        }
        
        self.active_requests[request_id] = request_info
        
        # Create JSON-safe version for logging
        log_safe_info = {
            "request_id": request_info["request_id"],
            "tool_name": request_info["tool_name"],
            "parameters": request_info["parameters"],
            "session": request_info["session"],
            "start_time": request_info["start_time_iso"],
            "status": request_info["status"]
        }
        
        logger.info("Request started", extra={
            "request_trace": log_safe_info
        })
        
        return request_id
    
    def complete_request(
        self, 
        request_id: str, 
        result_summary: Optional[str] = None, 
        error: Optional[str] = None,
        row_count: Optional[int] = None
    ):
        """
        Mark request as completed and log final status.
        
        Args:
            request_id: Request ID returned from start_request
            result_summary: Brief summary of results (will be truncated)
            error: Error message if request failed
            row_count: Number of rows returned/affected
        """
        if request_id not in self.active_requests:
            logger.warning(f"Attempted to complete unknown request: {request_id}")
            return
            
        request_info = self.active_requests[request_id]
        end_time = datetime.utcnow()
        duration = (end_time - request_info["start_time"]).total_seconds()
        
        request_info.update({
            "end_time": end_time,
            "end_time_iso": end_time.isoformat(),
            "status": "error" if error else "completed",
            "result_summary": result_summary[:200] if result_summary else None,  # Truncate for logging
            "error": error,
            "row_count": row_count,
            "duration_seconds": round(duration, 3)
        })
        
        # Create JSON-safe version for logging (exclude datetime objects)
        log_safe_info = {
            "request_id": request_info["request_id"],
            "tool_name": request_info["tool_name"],
            "parameters": request_info["parameters"],
            "session": request_info["session"],
            "start_time": request_info["start_time_iso"],
            "end_time": request_info["end_time_iso"],
            "status": request_info["status"],
            "result_summary": request_info["result_summary"],
            "error": request_info["error"],
            "row_count": request_info["row_count"],
            "duration_seconds": request_info["duration_seconds"]
        }
        
        # Log completion
        log_level = logging.ERROR if error else logging.INFO
        logger.log(log_level, "Request completed", extra={
            "request_trace": log_safe_info
        })
        
        # Clean up
        del self.active_requests[request_id]
    
    def _redact_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Redact sensitive information from parameters for logging."""
        if not isinstance(data, dict):
            return {}
            
        redacted = {}
        sensitive_keys = {'password', 'token', 'secret', 'key', 'auth', 'credential'}
        
        for key, value in data.items():
            key_lower = str(key).lower()
            if any(sensitive in key_lower for sensitive in sensitive_keys):
                redacted[key] = "[REDACTED]"
            elif isinstance(value, str) and len(value) > 1000:
                # Truncate very long values
                redacted[key] = value[:100] + "...[TRUNCATED]"
            else:
                redacted[key] = value
                
        return redacted
    
    def get_active_requests(self) -> Dict[str, Dict[str, Any]]:
        """Get currently active requests (for debugging)."""
        return self.active_requests.copy()

# Global request tracer instance
request_tracer = RequestTracer()