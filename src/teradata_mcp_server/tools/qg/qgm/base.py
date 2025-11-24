"""
Base client class for QueryGrid Manager API.
"""

import logging
import os
from typing import Any

import requests


class BaseClient:
    """Base class for QueryGrid Manager API resource clients."""

    def __init__(self, session: requests.Session, base_url: str):
        self.session = session
        self.base_url = base_url.rstrip("/")
        self.logger = logging.getLogger(self.__class__.__module__)

    def _request(self, method: str, endpoint: str, **kwargs) -> Any:
        """Make a request to the QGM API."""
        url = f"{self.base_url}{endpoint}"
        self.logger.debug(f"Making {method} request to {url}")

        response = self.session.request(method, url, **kwargs)
        response.raise_for_status()

        try:
            return response.json()
        except ValueError:
            return response.text
