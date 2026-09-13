# Bundled Agent Skills

Drop [Agent Skill](https://docs.claude.com/en/docs/agents-and-tools/agent-skills) folders in
here to have the running Teradata MCP server serve them to any connected MCP client, over
and above the tools/prompts/resources it already exposes.

This is distinct from `agentic/skills/` at the repo root, which is a Claude Code **plugin**
consumed by developers working on this repo (e.g. authoring YAML semantic layers). Skills
placed here are packaged with `teradata-mcp-server` and served at runtime — see
[`docs/server_guide/SKILLS.md`](../../../docs/server_guide/SKILLS.md) for the full picture.

## Layout

Each subdirectory is one skill. The bundled skills are worked examples — each walks an agent
through calling this server's tools for one reporting or assistant task. Most of them replace
what used to be MCP prompts in the corresponding module's `*_objects.yml` (a prompt required a
client with prompt-picker support and structured parameters; a skill works with any client that
can discover and read MCP resources, at the cost of the agent having to infer or ask for the
same inputs instead of filling in a form):

Skill folders are named `<module>-<topic>`, keeping the same module prefix the prompt used to
have (`dba_`, `base_`, `qlty_`, `chat_`, `tdvs_`):

**DBA** (from `tools/dba/dba_objects.yml`):
- `dba-dashboard` — 30-day system health dashboard (space, resource usage, flow control, sessions).
- `dba-user-activity-analysis` — 7-day user activity ranking and drill-down.
- `dba-table-archive-advisor` — finds large tables and drafts archive SQL.
- `dba-table-lineage` — traces table lineage from SQL history.
- `dba-table-drop-impact` — assesses who/what depends on a table before it's dropped.

**Base** (from `tools/base/base_objects.yml`):
- `base-sql-assistant` — general schema-discovery + query-generation assistant, with a Teradata SQL cheat sheet as a supporting file.
- `base-table-business-description` — plain-language description of one table from its DDL.
- `base-database-business-description` — plain-language description of a whole database from its tables' DDL.

**Data quality** (from `tools/qlty/qlty_objects.yml`):
- `qlty-database-quality-assessment` — per-table data quality dashboard for a database.

**Chat completion** (from `tools/chat/chat_objects.yml`):
- `chat-mapreduce-analysis` — answers a high-level question by map-reducing per-row LLM labels over text data.

**Vector Store** (from `tools/tdvs/tdvs_objects.yml`):
- `tdvs-vector-store-assistant` — routes a request to the right `tdvs_*` tool.
- `tdvs-vector-store-rag` — grounds answers strictly in vector store content.

`dba_systemVoice` stayed an MCP prompt rather than becoming a skill, because `examples/app-voice-agent` fetches it at runtime via `prompts/get` — skills are served as resources, not prompts, so they aren't a drop-in replacement for that use case.

```
skills/
├── dba-dashboard/
│   └── SKILL.md
├── base-sql-assistant/
│   ├── SKILL.md
│   └── reference/
│       └── teradata-sql-cheatsheet.md
└── my-skill/
    ├── SKILL.md          # required — YAML frontmatter (name, description) + instructions
    └── reference/        # optional supporting files (docs, scripts, templates, ...)
        └── notes.md
```

`SKILL.md` must start with frontmatter:

```markdown
---
name: my-skill
description: One sentence a client/model uses to decide when this skill is relevant.
---

Full instructions for the skill go here.
```

The folder name becomes the skill's name and its resource namespace
(`skill://my-skill/...`).

## How it's served

`create_mcp_app()` registers a `SkillsDirectoryProvider` (from
`fastmcp.server.providers.skills`) pointed at this directory. Each skill folder becomes a
set of MCP resources:

- `skill://<name>/SKILL.md` — the main skill file
- `skill://<name>/_manifest` — JSON listing of every file in the skill (path/size/hash)
- supporting files, readable on demand via a `skill://<name>/{path}` resource template

Users can also add their own skills without touching this package — see
`docs/server_guide/SKILLS.md` for the `<config_dir>/skills/` override location.
