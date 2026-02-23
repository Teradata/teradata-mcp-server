# Roadmap: Teradata MCP Server — Wildcard Imports Cleanup

## Overview

Replace `from .module import *` wildcard imports with explicit named imports and `__all__` export lists across all 11 tool package `__init__.py` files. The work proceeds in a deliberate order — audit first, low-risk packages to validate the pattern, medium-risk packages with known complications, utility-dependent packages with extra decisions, and finally ruff enforcement to lock in correctness permanently.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Audit** - Document all current exports and `td.*` consumers before touching any code
- [x] **Phase 2: Low-Risk Conversions** - Convert tmpl, sec, rag, dba, qlty — simplest packages, validates the pattern
- [x] **Phase 3: Medium-Risk Conversions** - Convert chat, base, bar — each has a known complication requiring care
- [x] **Phase 4: Utility-Dependent Conversions** - Convert fs, plot, sql_opt — require non-trivial decisions beyond mechanical swap
- [ ] **Phase 5: Ruff Enforcement** - Remove F403/F401 suppressions and confirm clean enforcement

## Phase Details

### Phase 1: Audit
**Goal**: Know exactly what each package currently exports and what downstream code accesses via `td.*` before any `__init__.py` is touched
**Depends on**: Nothing (first phase)
**Requirements**: AUDIT-01, AUDIT-02
**Success Criteria** (what must be TRUE):
  1. A documented baseline exists listing every name exported by each of the 11 affected packages
  2. Every `td.*` attribute access in `app.py` and `tools/__init__.py` is mapped to the package that must export it
  3. `td.handle_base_readQuery` and `td.FeatureStoreConfig` are confirmed as the critical `td.*` accesses that must not be broken
  4. `tdvs/__init__.py` is confirmed as the correct reference implementation for the explicit-import-plus-`__all__` pattern
**Plans**: 1 plan

Plans:
- [x] 01-01-PLAN.md — Capture baseline exports for all 11 packages and map `td.*` consumer accesses

### Phase 2: Low-Risk Conversions
**Goal**: Replace wildcard imports with explicit named imports and `__all__` in the five cleanest packages, validating the pattern end-to-end with no compatibility risk
**Depends on**: Phase 1
**Requirements**: IMPORT-01, IMPORT-02, IMPORT-03, IMPORT-04, IMPORT-05, RESOURCE-01
**Success Criteria** (what must be TRUE):
  1. `tmpl`, `sec`, `rag`, `dba`, and `qlty` `__init__.py` files each have explicit `from .module import fn1, fn2` lines and a matching `__all__` list
  2. No wildcard imports remain in any of the 5 converted packages
  3. All `from ._resources import *` lines in packages with empty `_resources.py` files are removed
  4. `pytest` passes with no regressions after all 5 conversions
  5. `ruff check` is clean on all 5 converted `__init__.py` files (with suppressions still in place globally)
**Plans**: 2 plans

Plans:
- [x] 02-01-PLAN.md — Convert tmpl and sec to explicit imports with __all__ (1 + 3 handlers)
- [x] 02-02-PLAN.md — Convert rag, dba, and qlty to explicit imports with __all__ (1 + 6 + 7 handlers); full Phase 2 verification

### Phase 3: Medium-Risk Conversions
**Goal**: Replace wildcard imports in chat, base, and bar — packages with known complications — and confirm critical `td.handle_base_readQuery` access is unbroken
**Depends on**: Phase 2
**Requirements**: IMPORT-06, IMPORT-07, IMPORT-08, COMPAT-01
**Success Criteria** (what must be TRUE):
  1. `chat`, `base`, and `bar` `__init__.py` files each have explicit imports and a matching `__all__` list
  2. `td.handle_base_readQuery` is accessible via `tools/__init__.py` after `base` package conversion
  3. `bar/__init__.py` does not re-export `DSAClient` or any other non-handler name
  4. Server starts and responds correctly with the `chat` profile active after `chat` conversion
**Plans**: 2 plans

Plans:
- [x] 03-01-PLAN.md -- Convert chat to explicit imports with __all__ (2 handlers, verify CHAT_CONFIG side-effect preserved)
- [x] 03-02-PLAN.md -- Convert base (8 handlers, smoke-test td.handle_base_readQuery) and bar (6 handlers, exclude DSAClient); cross-verify all 8 packages

### Phase 4: Utility-Dependent Conversions
**Goal**: Replace wildcard imports in fs, plot, and sql_opt — packages requiring judgment calls about what to re-export — and confirm `td.FeatureStoreConfig` access is unbroken
**Depends on**: Phase 3
**Requirements**: IMPORT-09, IMPORT-10, IMPORT-11, COMPAT-02
**Success Criteria** (what must be TRUE):
  1. `fs`, `plot`, and `sql_opt` `__init__.py` files each have explicit imports and a matching `__all__` list
  2. `td.FeatureStoreConfig` is accessible via `tools/__init__.py` after `fs` package conversion
  3. `plot/__init__.py` does not re-export names from `plot_utils` via wildcard; only `handle_*` functions are exported
  4. `sql_opt/__init__.py` does not re-export local duplicate utility functions (`create_response`, `rows_to_json`, `serialize_teradata_types`)
  5. All 11 packages are converted — no wildcard imports remain in any tool package `__init__.py`
**Plans**: 2 plans

Plans:
- [x] 04-01-PLAN.md — Convert plot and fs to explicit imports with __all__ (4 + 8+1 handlers); smoke-test td.FeatureStoreConfig
- [x] 04-02-PLAN.md — Convert sql_opt to explicit imports with __all__ (3 handlers, exclude local duplicate utilities); comprehensive 11-package cross-verification

### Phase 5: Ruff Enforcement
**Goal**: Remove ruff F403/F401 suppressions and confirm clean enforcement, making wildcard imports in `__init__.py` files impossible to reintroduce undetected
**Depends on**: Phase 4
**Requirements**: COMPAT-03, RUFF-01, RUFF-02, RUFF-03
**Success Criteria** (what must be TRUE):
  1. `pyproject.toml` no longer contains F403 or F401 suppression entries for `__init__.py` files
  2. `ruff check` passes with zero import-related warnings across all modified files
  3. All `handle_*` functions currently discoverable by `ModuleLoader` remain discoverable after all cleanups
  4. A developer introducing a new wildcard import in any `__init__.py` will see an immediate ruff failure
**Plans**: 2 plans

Plans:
- [ ] 05-01-PLAN.md — Fix all 24 F401 violations (21 removals + 3 noqa annotations) and add __all__ to tdvs/__init__.py
- [ ] 05-02-PLAN.md — Remove F403/F401 suppressions from pyproject.toml; verify ruff check clean; confirm ModuleLoader discovers all handlers

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Audit | 1/1 | ✓ Complete | 2026-02-22 |
| 2. Low-Risk Conversions | 2/2 | ✓ Complete | 2026-02-22 |
| 3. Medium-Risk Conversions | 2/2 | ✓ Complete | 2026-02-22 |
| 4. Utility-Dependent Conversions | 2/2 | ✓ Complete | 2026-02-22 |
| 5. Ruff Enforcement | 0/2 | Not started | - |
