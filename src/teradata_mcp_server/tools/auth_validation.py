"""
Input validation and rate limiting for authentication attempts.
"""

import re
import time
import hashlib
import threading
from collections import defaultdict, deque
from typing import Optional
from functools import wraps


class AuthValidator:
    """Input validation for authentication parameters."""
    
    # Username pattern: alphanumeric + underscore, 1-30 chars (Teradata standard)
    USERNAME_PATTERN = re.compile(r'^[A-Za-z0-9_]{1,30}$')
    
    @classmethod
    def validate_username(cls, username: str) -> bool:
        """Validate database username format."""
        return bool(username and cls.USERNAME_PATTERN.match(username))
    
    @classmethod
    def validate_jwt_format(cls, token: str) -> bool:
        """Basic JWT format validation (three base64url parts)."""
        if not token:
            return False
        parts = token.split('.')
        return len(parts) == 3 and all(part for part in parts)
    
    @classmethod
    def validate_basic_token(cls, b64_token: str) -> bool:
        """Validate Basic auth token is proper base64."""
        if not b64_token:
            return False
        try:
            import base64
            decoded = base64.b64decode(b64_token)
            # Should be valid UTF-8 and contain a colon
            decoded_str = decoded.decode('utf-8')
            return ':' in decoded_str
        except Exception:
            return False


class RateLimiter:
    """Thread-safe rate limiter using sliding window."""
    
    def __init__(self, max_attempts: int = 5, window_seconds: int = 60):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._attempts: dict[str, deque] = defaultdict(deque)
        self._lock = threading.RLock()
    
    def is_allowed(self, client_id: str) -> bool:
        """Check if client is allowed to make a request."""
        current_time = time.time()
        window_start = current_time - self.window_seconds
        
        with self._lock:
            # Clean old attempts
            attempts_queue = self._attempts[client_id]
            while attempts_queue and attempts_queue[0] < window_start:
                attempts_queue.popleft()
            
            # Check if under limit
            if len(attempts_queue) >= self.max_attempts:
                return False
            
            # Record this attempt
            attempts_queue.append(current_time)
            return True
    
    def get_remaining_attempts(self, client_id: str) -> int:
        """Get number of remaining attempts for client."""
        current_time = time.time()
        window_start = current_time - self.window_seconds
        
        with self._lock:
            attempts_queue = self._attempts[client_id]
            # Clean old attempts
            while attempts_queue and attempts_queue[0] < window_start:
                attempts_queue.popleft()
            
            return max(0, self.max_attempts - len(attempts_queue))
    
    def clear_client(self, client_id: str):
        """Clear rate limit history for client (e.g., successful auth)."""
        with self._lock:
            self._attempts.pop(client_id, None)
    
    def cleanup_old_entries(self) -> int:
        """Remove old entries and return count of cleaned clients."""
        current_time = time.time()
        window_start = current_time - self.window_seconds
        cleaned_count = 0
        
        with self._lock:
            clients_to_remove = []
            for client_id, attempts_queue in self._attempts.items():
                # Clean old attempts
                while attempts_queue and attempts_queue[0] < window_start:
                    attempts_queue.popleft()
                
                # Remove empty queues
                if not attempts_queue:
                    clients_to_remove.append(client_id)
            
            for client_id in clients_to_remove:
                del self._attempts[client_id]
                cleaned_count += 1
        
        return cleaned_count


def generate_client_id(auth_header: str, forwarded_for: Optional[str] = None) -> str:
    """Generate a client ID for rate limiting based on auth header and IP."""
    # Use hash of auth header (without revealing credentials) + IP for rate limiting
    identifier_parts = []
    
    if auth_header:
        # Hash the auth header to avoid storing credentials
        auth_hash = hashlib.sha256(auth_header.encode()).hexdigest()[:16]
        identifier_parts.append(auth_hash)
    
    if forwarded_for:
        # Use first IP in X-Forwarded-For chain
        client_ip = forwarded_for.split(',')[0].strip()
        identifier_parts.append(client_ip)
    
    if not identifier_parts:
        # Fallback - this shouldn't happen but prevents errors
        identifier_parts.append("unknown")
    
    return ":".join(identifier_parts)


class AuthValidationError(Exception):
    """Base exception for authentication validation errors."""
    pass


class InvalidUsernameError(AuthValidationError):
    """Invalid username format."""
    pass


class InvalidTokenFormatError(AuthValidationError):
    """Invalid token format."""
    pass


class RateLimitExceededError(AuthValidationError):
    """Rate limit exceeded."""
    def __init__(self, retry_after_seconds: int):
        self.retry_after_seconds = retry_after_seconds
        super().__init__(f"Rate limit exceeded. Try again in {retry_after_seconds} seconds.")


def rate_limited_auth(rate_limiter: RateLimiter):
    """Decorator to apply rate limiting to authentication functions."""
    def decorator(func):
        @wraps(func)
        def wrapper(self, auth_header: str, *args, **kwargs):
            # Generate client ID from auth header and any available IP info
            client_id = generate_client_id(auth_header)
            
            # Check rate limit
            if not rate_limiter.is_allowed(client_id):
                remaining_time = rate_limiter.window_seconds
                raise RateLimitExceededError(remaining_time)
            
            try:
                # Execute the auth function
                result = func(self, auth_header, *args, **kwargs)
                
                # Clear rate limit on successful authentication
                if result:
                    rate_limiter.clear_client(client_id)
                
                return result
            except Exception as e:
                # Don't clear rate limit on failures - let it accumulate
                raise
        
        return wrapper
    return decorator