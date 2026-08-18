"""Guard-mode helpers for multi-step confirmation flows on destructive operations.

Provides utilities for tools marked with destructive_hint=True to require
explicit user confirmation before executing irreversible operations.

NOTE: The InputRequiredResult API from mcp>=2.0.0 is still evolving.
The helper functions below are PLACEHOLDERS and will be updated once
the v4 API stabilizes. For now, tools should return error messages
for destructive operations requiring confirmation rather than using
these helpers directly.

Example usage pattern (current workaround):

    async def handle_bar_drop_table(table_name: str) -> str:
        # For now, return an error message asking for confirmation
        # until InputRequiredResult API is stable
        return f"Drop table '{table_name}'? This is irreversible. " \
               f"Please confirm explicitly in a follow-up request."
"""


def require_confirmation(
    operation_name: str,
    description: str,
    risk_level: str = "high",
) -> dict:
    """Generate confirmation request for a destructive operation.

    NOTE: This is a PLACEHOLDER. The actual InputRequiredResult API
    in MCP v4 is still evolving. This currently returns a dict that
    can be converted to error message text.

    Args:
        operation_name: Human-readable name of the operation (e.g., "Drop Table")
        description: Detailed description of what will happen
        risk_level: "high" or "critical"; used to emphasize severity

    Returns:
        Dict with confirmation request details (for future InputRequiredResult)
    """
    prefix = "⚠️ WARNING" if risk_level == "high" else "🔴 CRITICAL"

    message = f"""{prefix}: {operation_name}

{description}

This action CANNOT be undone. Please confirm by typing 'yes' to proceed."""

    # TODO: Once InputRequiredResult API is stable in v4, replace with:
    # return InputRequiredResult(...)
    return {
        "type": "confirmation_required",
        "message": message,
        "operation": operation_name,
        "risk_level": risk_level,
    }


def check_confirmation(
    user_response: str,
    expected: str = "yes",
) -> bool:
    """Check if user confirmed a destructive operation.

    Args:
        user_response: The user's input (should be lowercase)
        expected: The confirmation string to match (default: "yes")

    Returns:
        True if user confirmed, False otherwise
    """
    return user_response.strip().lower() == expected.lower()
