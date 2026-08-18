"""Guard-mode helpers for multi-step confirmation flows on destructive operations.

Provides utilities for tools marked with destructive_hint=True to require
explicit user confirmation before executing irreversible operations.

Example usage in a tool handler:

    from mcp import Context
    from teradata_mcp_server.tools.utils.guard_mode import require_confirmation, check_confirmation

    async def handle_bar_drop_table(table_name: str, ctx: Context) -> str:
        # Check if user has already confirmed
        if not ctx.input_responses:
            # First invocation: ask for confirmation
            return require_confirmation(
                operation_name="Drop Table",
                description=f"Drop table '{table_name}'? All data will be lost permanently.",
                risk_level="critical",
            )

        # Second invocation: user has confirmed (or not)
        user_response = ctx.input_responses[0]
        if not check_confirmation(user_response):
            return f"Operation cancelled."

        # Proceed with the destructive operation
        # ... actual drop table logic ...
        return f"Successfully dropped table '{table_name}'"
"""

from mcp.types import InputRequiredResult


def require_confirmation(
    operation_name: str,
    description: str,
    risk_level: str = "high",
) -> InputRequiredResult:
    """Generate an InputRequiredResult for a destructive operation confirmation.

    Args:
        operation_name: Human-readable name of the operation (e.g., "Drop Table")
        description: Detailed description of what will happen (e.g., "Drop table 'customers'? This is irreversible.")
        risk_level: "high" or "critical"; used to emphasize severity

    Returns:
        InputRequiredResult that the client will present to the user for confirmation
    """
    prefix = "⚠️ WARNING" if risk_level == "high" else "🔴 CRITICAL"

    message = f"""{prefix}: {operation_name}

{description}

This action CANNOT be undone. Please confirm by typing 'yes' to proceed."""

    return InputRequiredResult(
        message=message,
        response_type="string",  # type: ignore[arg-type]
    )


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
