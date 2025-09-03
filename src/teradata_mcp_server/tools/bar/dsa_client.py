"""DSA REST API client for BAR operations"""

import json
import logging
import os
from typing import Any, Dict, List, Optional
import requests
from urllib.parse import urljoin

logger = logging.getLogger("teradata_mcp_server")


class DSAClientError(Exception):
    """Base exception for DSA client errors"""
    pass


class DSAAuthenticationError(DSAClientError):
    """Authentication error with DSA system"""
    pass


class DSAConnectionError(DSAClientError):
    """Connection error with DSA system"""
    pass


class DSAAPIError(DSAClientError):
    """API error from DSA system"""
    pass


class DSAClient:
    """Client for interacting with Teradata DSA REST API"""
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        verify_ssl: Optional[bool] = None,
        timeout: Optional[float] = None
    ):
        """Initialize DSA client
        
        Args:
            base_url: Base URL for DSA API (defaults to environment variable)
            username: Username for authentication (defaults to environment variable)
            password: Password for authentication (defaults to environment variable)
            verify_ssl: Whether to verify SSL certificates (defaults to environment variable)
            timeout: Request timeout in seconds (defaults to environment variable)
        """
        # Handle both DSA_BASE_URL and individual DSA_HOST/DSA_PORT/DSA_PROTOCOL
        if base_url:
            self.base_url = base_url
        else:
            dsa_base_url = os.getenv("DSA_BASE_URL")
            if dsa_base_url:
                self.base_url = dsa_base_url
            else:
                # Use individual components
                dsa_host = os.getenv("DSA_HOST", "localhost")
                dsa_port = int(os.getenv("DSA_PORT", "9090"))
                dsa_protocol = os.getenv("DSA_PROTOCOL", "https")
                self.base_url = f"{dsa_protocol}://{dsa_host}:{dsa_port}/"
        
        self.username = username or os.getenv("DSA_USERNAME", "admin")
        self.password = password or os.getenv("DSA_PASSWORD", "admin")
        self.verify_ssl = verify_ssl if verify_ssl is not None else os.getenv("DSA_VERIFY_SSL", "true").lower() in ["true", "1", "yes"]
        self.timeout = timeout or float(os.getenv("DSA_CONNECTION_TIMEOUT", "30"))
        
        # Ensure base URL ends with /
        if not self.base_url.endswith('/'):
            self.base_url += '/'
            
        logger.info(f"Initialized DSA client for {self.base_url}")
    
    def _get_auth(self) -> Optional[tuple]:
        """Get authentication credentials if available"""
        if self.username and self.password:
            return (self.username, self.password)
        return None
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Make an HTTP request to the DSA API
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (relative to base URL)
            params: Query parameters
            data: Request body data
            headers: Additional headers
            
        Returns:
            Response data as dictionary
            
        Raises:
            DSAConnectionError: If connection fails
            DSAAuthenticationError: If authentication fails
            DSAAPIError: If API returns an error
        """
        url = urljoin(self.base_url, endpoint)
        
        # Prepare headers
        request_headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'User-Agent': 'Teradata-MCP-Server-BAR/1.0.0'
        }
        if headers:
            request_headers.update(headers)
        
        # Prepare authentication
        auth = self._get_auth()
        
        logger.debug(f"Making {method} request to {url} with params: {params}")
        
        try:
            response = requests.request(
                method=method,
                url=url,
                params=params,
                json=data,
                headers=request_headers,
                auth=auth,
                verify=self.verify_ssl,
                timeout=self.timeout
            )
            
            logger.debug(f"Response status: {response.status_code}")
            
            # Handle authentication errors
            if response.status_code == 401:
                raise DSAAuthenticationError("Authentication failed - check username and password")
            
            # Handle other client/server errors
            if response.status_code >= 400:
                error_msg = f"DSA API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise DSAAPIError(error_msg)
            
            # Parse JSON response
            try:
                return response.json()
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                raise DSAAPIError(f"Invalid JSON response from DSA API: {e}")
                
        except requests.exceptions.ConnectError as e:
            error_msg = f"Failed to connect to DSA server at {url}: {e}"
            logger.error(error_msg)
            raise DSAConnectionError(error_msg)
        except requests.exceptions.Timeout as e:
            error_msg = f"Request timeout connecting to DSA server: {e}"
            logger.error(error_msg)
            raise DSAConnectionError(error_msg)
        except requests.exceptions.RequestException as e:
            error_msg = f"HTTP error communicating with DSA server: {e}"
            logger.error(error_msg)
            raise DSAConnectionError(error_msg)
    
    def health_check(self) -> Dict[str, Any]:
        """Perform a health check on the DSA system
        
        Returns:
            Dictionary with health check results
        """
        try:
            # Try to make a simple API call to test connectivity
            response = self._make_request(
                'GET', 
                'dsa/components/backup-applications/disk-file-system'
            )
            
            return {
                "status": "healthy",
                "dsa_status": response.get("status", "unknown"),
                "message": "Successfully connected to DSA system"
            }
        except DSAAuthenticationError:
            return {
                "status": "unhealthy",
                "error": "authentication_failed",
                "message": "Authentication failed - check credentials"
            }
        except DSAConnectionError as e:
            return {
                "status": "unhealthy",
                "error": "connection_failed",
                "message": str(e)
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": "unknown_error",
                "message": str(e)
            }


# Global DSA client instance
dsa_client = DSAClient()
