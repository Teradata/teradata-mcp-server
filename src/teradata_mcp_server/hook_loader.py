from __future__ import annotations

import importlib
import importlib.util
import logging
from pathlib import Path

from teradata_mcp_server.hooks import ServerHooks

_log = logging.getLogger("teradata_mcp_server.hook_loader")

_NO_HOOKS = ServerHooks()


def load_hooks(module_path: str) -> ServerHooks:
    """Return a ServerHooks instance loaded from *module_path*.

    *module_path* may be:
    - An absolute or relative file path ending in ``.py`` — loaded as an
      ad-hoc module named ``_teradata_mcp_user_hooks``.
    - A dotted Python import name (e.g. ``my_package.hooks``) — resolved
      via the normal import machinery.

    The target module must expose ``get_hooks() -> ServerHooks``.

    Returns ``ServerHooks()`` (all hooks disabled) on any error so that a
    misconfigured hooks module never prevents the server from starting.
    """
    if not module_path:
        return _NO_HOOKS

    try:
        path = Path(module_path)
        if path.suffix == ".py":
            spec = importlib.util.spec_from_file_location("_teradata_mcp_user_hooks", path.resolve())
            if spec is None or spec.loader is None:
                _log.error("Cannot create module spec from %s", module_path)
                return _NO_HOOKS
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)  # type: ignore[union-attr]
        else:
            mod = importlib.import_module(module_path)

        get_hooks = getattr(mod, "get_hooks", None)
        if not callable(get_hooks):
            _log.error("Hooks module %s must define get_hooks() -> ServerHooks", module_path)
            return _NO_HOOKS

        hooks = get_hooks()
        if not isinstance(hooks, ServerHooks):
            _log.error("get_hooks() in %s must return a ServerHooks instance, got %r", module_path, type(hooks))
            return _NO_HOOKS

        _log.info("Loaded server hooks from %s", module_path)
        return hooks

    except Exception as exc:
        _log.error("Failed to load hooks from %s: %s", module_path, exc, exc_info=True)
        return _NO_HOOKS
