# Deploying and smoke-testing your customisation

## Config directory resolution

The server reads YAML from, in order:

1. `--config_dir <path>` CLI arg
2. `$CONFIG_DIR` env var
3. Current working directory (fallback)

It picks up **every `*.yml` file** in that directory, in addition to the packaged defaults shipped under `src/teradata_mcp_server/config/`. Your files override packaged objects by name; your `profiles.yml` replaces the packaged one at the top-level key.

Recommended layout:

```
~/my-mcp-config/
├── profiles.yml
├── dbc_objects.yml
└── domain_objects.yml
```

## Launching

```bash
# CLI args
teradata-mcp-server \
  --config_dir ~/my-mcp-config \
  --profile dbc_demo

# Or via env
export CONFIG_DIR=~/my-mcp-config
export PROFILE=dbc_demo
teradata-mcp-server
```

The database connection follows the standard precedence: `--database_uri` / `$DATABASE_URI` / `run.database_uri` in the active profile. Use env-var substitution (`teradata://${TD_USER}:${TD_PASSWORD}@host:1025`) so credentials never end up in YAML.

## Smoke-test: walk the MCP handshake with curl

The streamable-HTTP transport returns JSON inside SSE frames (`data: …` lines). The shell script below walks `initialize` → `notifications/initialized` → `tools/list` / `prompts/list` / `resources/list`, capturing the `Mcp-Session-Id` header between steps.

```bash
#!/usr/bin/env bash
set -euo pipefail

URL="${1:-http://localhost:8000/mcp/}"
H_FILE="$(mktemp)"; trap 'rm -f "$H_FILE"' EXIT

# 1. initialize — grab the session id from response headers
curl -sS -D "$H_FILE" -o /dev/null "$URL" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize",
       "params":{"protocolVersion":"2025-03-26",
                 "capabilities":{},
                 "clientInfo":{"name":"smoketest","version":"0"}}}'

SID="$(awk -F': ' 'tolower($1)=="mcp-session-id"{print $2}' "$H_FILE" | tr -d '\r')"
echo "Session: $SID"

# 2. notifications/initialized
curl -sS -o /dev/null "$URL" \
  -H "Mcp-Session-Id: $SID" \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","method":"notifications/initialized","params":{}}'

# 3. list each registry
for METHOD in tools/list prompts/list resources/list; do
  echo
  echo "== $METHOD =="
  curl -sS "$URL" \
    -H "Mcp-Session-Id: $SID" \
    -H 'Content-Type: application/json' \
    -H 'Accept: application/json, text/event-stream' \
    -d "{\"jsonrpc\":\"2.0\",\"id\":99,\"method\":\"$METHOD\",\"params\":{}}" \
    | sed -n 's/^data: //p' \
    | (command -v jq >/dev/null && jq . || cat)
done
```

Save as `mcp_list_tools.sh`, `chmod +x`, run against your server. You should see:

- Your `type: tool` and `type: cube` objects in `tools/list` (cubes carry the 6 auto-added args plus your custom ones).
- Your `type: prompt` objects in `prompts/list`.
- Your `type: glossary` entries in `resources/list`.

## Diagnosing missing objects

| Symptom | Likely cause |
|---|---|
| Object missing from all lists | YAML failed to parse → check server logs for `Failed to load YAML from …` |
| Tool present but not in your profile | Regex selector mismatch — `foo_*` is `foo` then zero-or-more underscores; you probably wanted `foo_.*` |
| Glossary missing | Glossary is selected by `resource:` not `tool:` |
| Cube tool errors with `ValueError: Measure '…' not found` | Caller passed a measure name that isn't in the cube's `measures:` dict — usually a typo in your prompt or a stale schema cache |
| `filter` ignored or causing parse errors | You wrote invalid SQL or used post-aggregation column names — use `res_filter` for those |
| Identifier interpolation produces `'DBC.AllSpaceV'` literal | You used `:database_name` instead of `{database_name}` for an identifier |

## Where to look in logs

The server logs at startup:

```
Configuration directory set to: <path>
Loading all YAML files (no specific profile): N files
Added custom tool: <name>
Added custom cube: <name>
Added custom prompt: <name>
Added custom glossary entries for: <name>.
```

If your object name doesn't show up in one of those lines, the file didn't load or the `type:` wasn't recognised.
