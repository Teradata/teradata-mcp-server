# Agent Skills

> **📍 Navigation:** [Documentation Home](../README.md) | [Server Guide](../README.md#-server-guide) | [Getting started](GETTING_STARTED.md) | [Architecture](ARCHITECTURE.md) | [Configuration](CONFIGURATION.md) | [Customization](CUSTOMIZING.md) | [<u>**Skills**</u>](SKILLS.md)

The Teradata MCP server can bundle and serve [Agent Skills](https://docs.claude.com/en/docs/agents-and-tools/agent-skills) — self-contained folders of instructions (and optional supporting files) that tell an agent how to carry out a specific task. Skills placed with the server are exposed as MCP **resources**, so any connected MCP client can discover and pull them at runtime, not just Claude Code.

This is a separate mechanism from the [declarative YAML customization](CUSTOMIZING.md) (tools/cubes/prompts/glossary) — skills carry instructions for an agent to follow, not new tools for it to call.

> **Note:** This is unrelated to `agentic/skills/` in the repository root, which is a Claude Code **plugin** used by developers working on this codebase (e.g. authoring semantic layers). That plugin is not packaged with `teradata-mcp-server` and is not served by the running server.

## Where skills live

There are two locations, loaded in this order (first match for a given skill name wins):

| Location | Purpose |
|---|---|
| `<config_dir>/skills/` | Your own skills, added without touching the package. Uses the same `--config_dir` / `CONFIG_DIR` directory as [custom YAML objects](CUSTOMIZING.md#configuration-directory). |
| `src/teradata_mcp_server/skills/` | Skills bundled with the `teradata-mcp-server` package itself, shipped to every installation. |

Each is a `SkillsDirectoryProvider` root; every subdirectory containing a `SKILL.md` becomes one skill.

## Skill folder layout

```
skills/
└── my-skill/
    ├── SKILL.md          # required
    └── reference/        # optional supporting files
        └── notes.md
```

`SKILL.md` starts with YAML frontmatter:

```markdown
---
name: my-skill
description: One sentence a client/model uses to decide when this skill is relevant.
---

Full instructions for the skill go here.
```

The folder name is the skill's name and becomes its resource namespace.

**Worked examples:** the server bundles twelve skills, most of which replace what used to be MCP prompts in a module's `*_objects.yml` (see [`src/teradata_mcp_server/skills/README.md`](../../src/teradata_mcp_server/skills/README.md) for the full rationale and the one prompt — `dba_systemVoice` — that stayed a prompt instead):

- [`dba-dashboard`](../../src/teradata_mcp_server/skills/dba-dashboard/SKILL.md) — 30-day system health dashboard.
- [`dba-user-activity-analysis`](../../src/teradata_mcp_server/skills/dba-user-activity-analysis/SKILL.md) — 7-day user activity ranking and drill-down.
- [`dba-table-archive-advisor`](../../src/teradata_mcp_server/skills/dba-table-archive-advisor/SKILL.md) — finds large tables and drafts archive SQL.
- [`dba-table-lineage`](../../src/teradata_mcp_server/skills/dba-table-lineage/SKILL.md) — traces table lineage from SQL history.
- [`dba-table-drop-impact`](../../src/teradata_mcp_server/skills/dba-table-drop-impact/SKILL.md) — assesses who/what depends on a table before it's dropped.
- [`base-sql-assistant`](../../src/teradata_mcp_server/skills/base-sql-assistant/SKILL.md) — schema discovery + query generation, with a Teradata SQL cheat sheet as a supporting file.
- [`base-table-business-description`](../../src/teradata_mcp_server/skills/base-table-business-description/SKILL.md) — plain-language description of one table from its DDL.
- [`base-database-business-description`](../../src/teradata_mcp_server/skills/base-database-business-description/SKILL.md) — plain-language description of a whole database from its tables' DDL.
- [`qlty-database-quality-assessment`](../../src/teradata_mcp_server/skills/qlty-database-quality-assessment/SKILL.md) — per-table data quality dashboard for a database.
- [`chat-mapreduce-analysis`](../../src/teradata_mcp_server/skills/chat-mapreduce-analysis/SKILL.md) — answers a high-level question by map-reducing per-row LLM labels over text data.
- [`tdvs-vector-store-assistant`](../../src/teradata_mcp_server/skills/tdvs-vector-store-assistant/SKILL.md) — routes a request to the right `tdvs_*` tool.
- [`tdvs-vector-store-rag`](../../src/teradata_mcp_server/skills/tdvs-vector-store-rag/SKILL.md) — grounds answers strictly in vector store content.

## Adding your own skill

```bash
mkdir -p my-teradata-config/skills/my-skill
# write my-teradata-config/skills/my-skill/SKILL.md
teradata-mcp-server --config_dir my-teradata-config
```

No server code changes or restart-time config are needed beyond `--config_dir` — the skills directory is scanned at startup alongside the packaged skills.

## How clients discover and read skills

Each skill folder is exposed as:

- `skill://<name>/SKILL.md` — the main resource (description + instructions)
- `skill://<name>/_manifest` — a JSON listing of every file in the skill, with size and hash
- supporting files — read on demand through a `skill://<name>/{path}` resource template (not enumerated in `list_resources()`, discovered via the manifest)

Any MCP client can list and read these like any other resource:

```python
from fastmcp import Client

async with Client("http://localhost:8001/mcp") as client:
    for r in await client.list_resources():
        if str(r.uri).startswith("skill://"):
            print(r.uri, "-", r.description)
```

FastMCP also ships client helpers for bulk discovery and download, useful for syncing skills served by an MCP server into a local `.claude/skills/`-style directory:

```python
from fastmcp import Client
from fastmcp.utilities.skills import list_skills, download_skill, sync_skills

async with Client("http://localhost:8001/mcp") as client:
    skills = await list_skills(client)
    await download_skill(client, "my-skill", "~/.claude/skills")
    # or grab everything the server offers:
    await sync_skills(client, "~/.claude/skills")
```

## Adding a skill to the package

To ship a skill with `teradata-mcp-server` itself:

1. Create `src/teradata_mcp_server/skills/<skill-name>/SKILL.md` (plus any supporting files).
2. That's it — the wheel/sdist build already includes everything under `src/teradata_mcp_server/skills/`, and `create_mcp_app()` registers the directory at startup.

See [`src/teradata_mcp_server/skills/README.md`](../../src/teradata_mcp_server/skills/README.md) for the in-tree convention notes.
