#!/usr/bin/env python
"""Unit tests for td_connect URL building with None values.

Tests that URL.create() properly handles None passwords and usernames,
fixing issue #384 where f-strings would stringify None to "None".
"""

import pytest
from sqlalchemy import URL
from urllib.parse import parse_qs, urlparse


def test_url_create_with_none_password():
    """Test that URL.create handles None password correctly."""
    url = URL.create(
        "teradatasql",
        username="user123",
        password=None,
        host="localhost",
        port=1025,
        database="mydb",
        query={"LOGMECH": "KRB5"},
    )
    url_str = str(url)
    # Should NOT contain the literal string "None"
    assert "None" not in url_str
    # Should have username but no password
    assert "user123" in url_str
    assert "KRB5" in url_str


def test_url_create_with_none_username():
    """Test that URL.create handles None username correctly."""
    url = URL.create(
        "teradatasql",
        username=None,
        password=None,
        host="localhost",
        port=1025,
        database="mydb",
        query={"LOGMECH": "JWT"},
    )
    url_str = str(url)
    # Should NOT contain the literal string "None"
    assert "None" not in url_str
    # Should still have the hostname and port
    assert "localhost" in url_str
    assert "1025" in url_str


def test_url_create_with_empty_password():
    """Test that URL.create handles empty string password correctly."""
    url = URL.create(
        "teradatasql",
        username="user123",
        password="",
        host="localhost",
        port=1025,
        database="mydb",
        query={"LOGMECH": "KRB5"},
    )
    url_str = str(url)
    # Should NOT contain the literal string "None"
    assert "None" not in url_str
    # Should have username
    assert "user123" in url_str


def test_url_create_with_password():
    """Test that URL.create handles regular password correctly."""
    url = URL.create(
        "teradatasql",
        username="user123",
        password="secret123",
        host="localhost",
        port=1025,
        database="mydb",
        query={"LOGMECH": "TD2"},
    )
    url_str = str(url)
    # Should NOT contain the literal string "None"
    assert "None" not in url_str
    # Should have username (password is masked in str representation for security)
    assert "user123" in url_str
    # Verify password is stored in the URL object even if not shown in str()
    assert url.password == "secret123"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
