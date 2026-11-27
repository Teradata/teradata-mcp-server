# Dependency security maintenance

This is the canonical procedure for maintainers and the repository-local `dependency-security` Codex skill. Dependabot detects issues; the owner retains merge, release and risk acceptance authority. A skill is not a scheduler. Follow applicable Teradata policies and repository instructions first.

## Scope and preflight

Check `git status -sb`, remote, HEAD, instructions, `gh auth status`, `uv --version`, Python and Docker availability. Fetch the default branch and work from its recorded SHA in a clean isolated worktree without altering user work. Confirm alert-read access and existing PRs (`gh pr list --state open --limit 100`). Treat API failures as unavailable inventory, never zero alerts. Keep raw data private and outside the repository; do not expose credentials to builds, tests or logs.

Root `pyproject.toml`/`uv.lock` and `tests/eval_test` are independent projects. Root has `fs`, `tdvs`, `bar`, and `dev` extras and a dev dependency group. Python support begins at 3.11; classifiers include 3.11–3.13. The evaluation tests can call Bedrock and a database: only run its documented offline unit tests without approval. The Dockerfile mixes uv and pip, installs floating `mcpo`, and uses a floating base; a lock fix alone does not establish image contents. Examples and `tests/mcp_bench` contain additional requirements files outside the existing Dependabot uv configuration. Check current coverage and report omissions rather than changing owner policy.

## Inventory and classification

Retrieve all pages, validate JSON and repo identity, remove the file even on failure. The following intentionally uses jq separately: `gh` versions may reject `--slurp` with `--jq`.

```sh
umask 077
alerts_file=$(mktemp)
trap 'rm -f "$alerts_file"' EXIT
if ! gh api --paginate --slurp 'repos/Teradata/teradata-mcp-server/dependabot/alerts?state=open&per_page=100' > "$alerts_file"; then
  echo 'Alert inventory unavailable' >&2; exit 1
fi
jq -e 'type == "array" and all(.[]; type == "array")' "$alerts_file" >/dev/null || exit 1
jq -r 'add // [] | .[] | [.number,.html_url,.security_advisory.ghsa_id,.security_vulnerability.severity,.dependency.package.ecosystem,.dependency.package.name,.dependency.manifest_path,(.dependency.scope // "unknown"),.security_vulnerability.vulnerable_version_range,(.security_vulnerability.first_patched_version.identifier // "NO PATCH")] | @tsv' "$alerts_file"
```

Record UTC time, base SHA, filters, alert ID, advisory, severity, manifest, scope, affected and patched ranges, each locked version, reverse paths, covering PR, candidate and outcome. Normalize package names and use PEP 440 comparisons, not string ordering; account for all versions and markers and multiple advisories per package. Verify public upstream advisories and package metadata. Prioritize critical/high runtime findings without dropping lower severities. Unknown exposure remains unknown. Check existing PRs and CI before producing duplicates; never close them yourself.

Use `uv tree --locked --invert --package PACKAGE` in each relevant project. A compatible targeted `uv lock --upgrade-package 'PACKAGE==VERSION'` can fix a transitive dependency; split independent fixes and inspect the resulting diff, sources, hashes, markers, and all versions. If blocked, try a compatible parent update; document concrete resolver conflicts. Never hand-edit lockfiles, bypass constraints, switch indexes or run an unrestricted upgrade. Changes that are breaking (including potentially breaking 0.x), broad, add a runtime dependency, change API/auth semantics or remove features require owner approval. No available patch requires investigation and a decision, not automatic dismissal or risk acceptance.

For direct runtime dependencies, check whether published `Requires-Dist` still allows vulnerable releases and raise a safe compatible lower bound when justified. For transitive runtime dependencies check parent metadata; a lockfile or uv-only constraint does not protect pip/uvx consumers. An added runtime constraint requires approval. Track source, merged, GitHub-confirmed and released fixes separately.

## Validation

Record PASS, FAIL, SKIPPED or NOT RUN and reason for each command, using the same toolchain for baseline and candidate. CI pins uv 0.13.10; verify syntax before updating it. Run, as applicable:

```sh
uv lock --check
uv sync --locked --extra dev
uv run --locked ruff check src/
uv run --locked ruff format --check src/
uv run --locked mypy src/
uv run --locked python tests/integration/middleware_transport_tests.py
uv build
(cd tests/eval_test && uv lock --check && uv sync --locked && uv run --locked pytest tests/test_checks.py tests/test_multi_turn.py tests/test_report.py tests/test_suggest_overrides.py tests/test_description_overrides.py)
uv audit --locked
(cd tests/eval_test && uv audit --locked)
```

Audit output is a full graph report, not a substitute for GitHub advisory matching. Findings have exit status 1; tool errors must fail the job and be investigated. Audit all supported markers/platforms as needed; OS/image and unlocked requirements need separate scanners. CI reports existing findings without masking scanner errors; dependency review blocks newly introduced high/critical findings when GitHub graph coverage is available. Verify graph coverage for both lockfiles in the PR UI. Do not add allowlists or relax enforcement without approval.

Test credential-free MCP initialization, registration and stdio/HTTP transport, configuration and relevant optional extras. Build a wheel, install it non-editably in a fresh environment, inspect `Requires-Dist`, resolve and audit consumer dependencies, including affected extras and minimum-version cases. Build and scan the final image when affected; inspect the actual runtime interpreter and installed packages. Run database integration only on an approved isolated test system; report missing credentials as skipped, not passed. Do not run untrusted code with secrets, privileged `pull_request_target`, or publication credentials. Report missing platform, extra, image, network or scanner coverage honestly. A passing lockfile audit alone is not proof of safe published or container artifacts.

## Handover and recurrence

Keep tooling and independent security patches in separate commits/branches. Report each alert (or grouped IDs) as COVERED_BY_EXISTING_PR, PATCH_PREPARED, PATCH_VALIDATED, BLOCKED_TESTS, BLOCKED_RESOLUTION, NEEDS_DECISION, NO_PATCH, ACCESS_BLOCKED, MERGED_PENDING_GITHUB or GITHUB_CONFIRMED_FIXED, with release status and evidence. For each decision state impact, viable alternatives, recommendation and the precise approval needed. Never print raw authenticated exports in public artifacts. Do not push or create PRs unless expressly authorized; never merge, release, dismiss or change GitHub settings without approval.

After merge, re-query alerts after graph processing, verify every manifest/version and inspect released wheel and image contents. Recommend release/rebuild where required. Suggested response targets pending Teradata policy: critical 24–48 hours, high 7 days, medium 30 days, low 60 days. Review exceptions weekly; record owner, expiry, advisory, exposure, mitigation and reconsideration trigger. No implicit risk acceptance.

Recurring prompts:

```text
Use $dependency-security to remediate all open Dependabot alerts. Apply safe targeted fixes, validate them, and prepare PR-ready changes. Continue independent fixes and consolidate decisions requiring my approval.
Use $dependency-security in audit mode to review open alerts and existing Dependabot PRs. Report what needs my attention; do not change files.
Use $dependency-security to review PR #NNN for security coverage and compatibility. Tell me whether it is ready for my merge.
Use $dependency-security in verify mode to check merged fixes, alert state and released artifacts.
```
