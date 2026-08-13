# Phase 0 — Spike and Validation (2026-08-13)

This document tracks Phase 0 work items per the FastMCP v4 migration plan.

## Current Baseline
- FastMCP: 3.4.6 (latest stable: 3.4.7, beta: 4.0.0b2 shipped 2026-08-07)
- MCP SDK: 1.28.1 (latest stable: 2.0.0 GA since 2026-07-28)
- Server: 0.2.6

## Work Item 1: Isolated Evaluation Branch

### 1a. FastMCP 4.0.0b2 + MCP 2.0.0 Combo Test

**Test environment:** `pyproject-fastmcp4-eval.toml`
- Pin: `fastmcp==4.0.0b2`, `mcp[cli]>=2.0.0`
- Goal: Verify dependency graph resolves without conflicts

Status: [pending] Create override and test

### 1b. MCP 2.0.0 Alone (Current FastMCP 3.4.7)

**Test environment:** `pyproject-mcp2-eval.toml`
- Pin: `fastmcp==3.4.7`, `mcp[cli]>=2.0.0`
- Goal: Assess whether snake_case fix (§2.2) can land earlier, decoupled from FastMCP v4
- Importance: If this works, the ToolAnnotations camelCase→snake_case fix can land as its own PR before Phase 2

Status: [pending] Create override and test

---

## Work Item 2: Cold-Start Test

**Goal:** Confirm lifespan machinery, middleware registration, and tool decorator calls are compatible.

**Procedure:**
1. Create throwaway evaluation branch
2. Run server with `DATABASE_URI` unset in stdio mode
3. Verify: process starts, registers tools, exits cleanly
4. Capture: startup logs, tool list, shutdown behavior

Status: [pending]

---

## Work Item 3: Verify Internal FastMCP Module Paths

**Goal:** Confirm these internal paths still exist in `4.0.0b2` (not part of public API contract).

| Module Path | File Location | Status |
|---|---|---|
| `fastmcp.server.middleware.error_handling.ErrorHandlingMiddleware` | app.py:349 | [pending] |
| `fastmcp.server.middleware.ping.PingMiddleware` | app.py:365 | [pending] |
| `fastmcp.server.dependencies.get_http_headers` | middleware.py:23 | [pending] |
| `fastmcp.server.dependencies.get_context` | tools/utils/factory.py:8 | [pending] |
| `fastmcp.server.middleware.{CallNext, Middleware, MiddlewareContext}` | app.py, middleware.py | [pending] |
| `fastmcp.prompts.prompt` (deprecated shim) | app.py:30 | [pending] |

**Verification method:** Try importing each in `4.0.0b2` environment; document existence/deprecation status.

Status: [pending]

---

## Work Item 4: Check `mcp_camelcase_compat` Warning Output

**Goal:** Understand FastMCP's compat flag behavior when direct `mcp.types` construction is used.

**Rationale:** §1.2 of the plan notes that `app.py:31` imports `ToolAnnotations` directly from `mcp.types`, **bypassing FastMCP's compat layer entirely**. This flag may not apply to those call sites.

**Procedure:**
1. Set `fastmcp.settings.mcp_camelcase_compat = False` in test environment
2. Run a tool call with camelCase kwargs (`readOnlyHint=`, `destructiveHint=`, etc.)
3. Observe: do warnings/errors still occur?
4. Expected: Yes — the flag doesn't affect direct SDK usage

**Test code location:** `tests/phase0/test_camelcase_compat.py` (new)

Status: [pending]

---

## Work Item 5: Evaluate Beta Stability

**Goal:** Confirm FastMCP 4 GA release timeline to unblock Phase 1/2 sequencing.

**Procedure:**
- Run weekly check: `curl -s https://pypi.org/pypi/fastmcp/json | python3 -c "import json,sys; r=json.load(sys.stdin); print(f\"Latest: {r['info']['version']}\")"`
- Trigger: Once GA (version `4.0.0` without alpha/beta suffix) appears on PyPI, notify team and proceed to Phase 2 gating

**Last check:** 2026-08-13 — `4.0.0b2` is current beta. No GA date announced.

Status: [ongoing monitoring]

---

## Exit Criteria

- [pending] Server cold-starts successfully with `4.0.0b2` pinned
- [pending] All internal import paths verified against `4.0.0b2`
- [pending] `mcp>=2.0.0`-only evaluation (against FastMCP 3.4.7) documented
- [pending] `mcp_camelcase_compat` behavior confirmed empirically
- [pending] Findings report generated

---

## Key Decision Points Confirmed

Per the migration plan §1:
- **Phase 0 uses beta** (`4.0.0b2`) for de-risking; actual pin bump (Phase 2) **gated on GA**
- **MCP 2.0.0 independent** of FastMCP 4 — can be evaluated early if findings support early landing of §2.2 fix
- **No breaking change surprises expected**, but β→GA regression risk (low-medium) requires re-validation before Phase 2 merge

---

## Findings Log

### 2026-08-13 Initial Setup
- Created this evaluation plan
- Confirmed PyPI versions: latest stable FastMCP 3.4.7, mcp 2.0.0 GA, FastMCP beta 4.0.0b2
- Ready to begin work items 1–5
