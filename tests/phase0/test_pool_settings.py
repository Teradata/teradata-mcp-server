#!/usr/bin/env python3
"""
Regression test for issue #449: Pool settings from environment variables

Verifies that TD_POOL_SIZE, TD_MAX_OVERFLOW, and TD_POOL_TIMEOUT environment
variables are correctly propagated through parse_args_to_settings().
"""

import os
import sys
from unittest.mock import patch


def test_pool_settings_are_loaded_from_environment():
    """Test that pool settings from environment survive parse_args_to_settings()."""
    env_vars = {
        "TD_POOL_SIZE": "37",
        "TD_MAX_OVERFLOW": "4",
        "TD_POOL_TIMEOUT": "91",
    }

    with patch.dict(os.environ, env_vars):
        # Clear sys.argv to simulate CLI with no arguments
        original_argv = sys.argv
        try:
            sys.argv = ["teradata-mcp-server"]

            from teradata_mcp_server.server import parse_args_to_settings

            settings = parse_args_to_settings()

            assert settings.pool_size == 37, f"Expected pool_size=37, got {settings.pool_size}"
            assert settings.max_overflow == 4, f"Expected max_overflow=4, got {settings.max_overflow}"
            assert settings.pool_timeout == 91, f"Expected pool_timeout=91, got {settings.pool_timeout}"

            print("✓ Pool settings are correctly loaded from environment")
            return True
        finally:
            sys.argv = original_argv


def test_pool_settings_use_defaults_when_not_set():
    """Test that default pool values are used when environment variables are absent."""
    # Remove the environment variables if they exist
    env_vars_to_remove = {"TD_POOL_SIZE", "TD_MAX_OVERFLOW", "TD_POOL_TIMEOUT"}
    original_env = {}

    for var in env_vars_to_remove:
        original_env[var] = os.environ.pop(var, None)

    try:
        original_argv = sys.argv
        sys.argv = ["teradata-mcp-server"]

        from teradata_mcp_server.server import parse_args_to_settings

        settings = parse_args_to_settings()

        assert settings.pool_size == 5, f"Expected pool_size=5 (default), got {settings.pool_size}"
        assert settings.max_overflow == 10, f"Expected max_overflow=10 (default), got {settings.max_overflow}"
        assert settings.pool_timeout == 30, f"Expected pool_timeout=30 (default), got {settings.pool_timeout}"

        print("✓ Default pool settings are used when environment variables are absent")
        return True
    finally:
        sys.argv = original_argv
        # Restore original environment
        for var, val in original_env.items():
            if val is not None:
                os.environ[var] = val


def test_other_env_only_settings_are_propagated():
    """Test that other environment-only settings are also propagated."""
    env_vars = {
        "MCP_PING_INTERVAL": "60",
        "AUTH_RATE_LIMIT_ATTEMPTS": "10",
        "AUTH_RATE_LIMIT_WINDOW": "120",
        "REGISTRY_REFRESH_INTERVAL": "600",
    }

    with patch.dict(os.environ, env_vars):
        original_argv = sys.argv
        try:
            sys.argv = ["teradata-mcp-server"]

            from teradata_mcp_server.server import parse_args_to_settings

            settings = parse_args_to_settings()

            assert settings.ping_interval == 60, f"Expected ping_interval=60, got {settings.ping_interval}"
            assert (
                settings.auth_rate_limit_attempts == 10
            ), f"Expected auth_rate_limit_attempts=10, got {settings.auth_rate_limit_attempts}"
            assert (
                settings.auth_rate_limit_window == 120
            ), f"Expected auth_rate_limit_window=120, got {settings.auth_rate_limit_window}"
            assert (
                settings.registry_refresh_interval == 600
            ), f"Expected registry_refresh_interval=600, got {settings.registry_refresh_interval}"

            print("✓ Other environment-only settings are correctly propagated")
            return True
        finally:
            sys.argv = original_argv


def main():
    """Run all regression tests."""
    print("=" * 70)
    print("Regression tests for issue #449: Pool settings from environment")
    print("=" * 70)
    print()

    tests = [
        test_pool_settings_are_loaded_from_environment,
        test_pool_settings_use_defaults_when_not_set,
        test_other_env_only_settings_are_propagated,
    ]

    passed = 0
    failed = 0

    for test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
                print(f"✗ {test_func.__name__}")
        except Exception as e:
            failed += 1
            print(f"✗ {test_func.__name__}: {e}")
            import traceback

            traceback.print_exc()

    print()
    print("-" * 70)
    print(f"Summary: {passed} passed, {failed} failed")
    print()

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
