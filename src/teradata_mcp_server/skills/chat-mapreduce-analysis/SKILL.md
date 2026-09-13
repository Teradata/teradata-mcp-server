---
name: chat-mapreduce-analysis
description: Use when asked a high-level question that needs an answer synthesized across many rows of text stored in Teradata (e.g. "why are customers unhappy?") — builds a SQL query, runs per-row LLM labeling with chat_aggregatedCompleteChat, then synthesizes a global answer from the label counts.
---

You are answering a high-level question over text data stored in Teradata, using a connected `teradata-mcp-server` with the `chat_*` tools available (requires the server's chat completion module to be configured — see `src/teradata_mcp_server/tools/chat/README.md`).

Answer the question in three steps, in order. Do not invent your own steps.

## Step 1 — Build the SQL query

- Write a Teradata SQL query that selects the texts relevant to the question. The query must return a single column, renamed to `txt`.
- If reasonable, filter rows to keep only texts relevant to the question. If filtering isn't clearly possible or meaningful, skip it and explain why in your reasoning (not in the SQL).
- Use the available tools (e.g. `base_tableList`, `base_columnDescription`) to discover actual databases, tables, and columns before writing the final query — don't guess names.
- Unless the question explicitly says there should be no sampling, add a `SAMPLE 1000` clause after any filtering to limit row count.
- No trailing semicolon. Only simple UTF-8 characters.
- Output only the SQL for this step — nothing else.

## Step 2 — Run aggregated chat completion

Call `chat_aggregatedCompleteChat(sql=..., system_message=...)` using the SQL from Step 1. For `system_message`, write a system prompt that:

- Focuses on one text row at a time (never asks about the whole dataset at once).
- Guides the model toward a short label that helps answer the original high-level question, from that one text's perspective.
- Strongly enforces a very short response — no more than 2–3 words.
- Instructs the model to return an empty string if the text isn't relevant to the question.
- May give example responses but must not restrict output to a fixed closed list.
- Only simple UTF-8 characters.

## Step 3 — Synthesize the answer

Using the aggregated `response_txt` values and their counts from Step 2:

- Remember these labels are LLM-generated, so different labels can mean the same thing (e.g. "bad quality" vs "poor quality") — merge or interpret similar responses together where appropriate.
- Produce a clear, concise summary explaining the dominant patterns and insights that answer the original question.
