# Chat Completion Tools

Chat Completion tools let Teradata call [OpenAI‑compatible ChatCompletion table operators](https://downloads.teradata.com/download/extensibility/open-ai-api-connectivity-functions) via MCP tools. They are designed for:

- Running LLMs over data in Teradata (classification, summarization, labeling, etc.).
- Aggregating per‑row LLM outputs into compact distributions for analytics.
- Integrating with the OpenAI‑compatible Java Table Operators installed in your Teradata system.

---

## Dependencies

- Teradata >= 17.20.
- OpenAI‑compatible Java Table Operator `CompleteChat` installed in a database (for example, `openai_client.CompleteChat`).
- MCP server configured with:
  - Valid Teradata connection.
  - `chat_config.yml` in `src/teradata_mcp_server/config/`.

Optional:

- Environment variable `CHAT_API_KEY` if your inference server requires an API key.

---

## Available tools

### `chat_completeChat`

**What it does**

Executes the `CompleteChat` table operator over a user‑supplied SQL query that returns a `txt` column. The LLM is called once per row and returns `response_txt` plus optional diagnostics and headers.

**Typical use cases**

- Sentiment / intent classification.
- Short Q&A or summarization over many rows.
- Tagging or labeling customer emails, tickets, logs, etc.

**Inputs (tool parameters)**

- `sql` *(str, required)*  
  Teradata SQL statement that returns a table with a `txt` column.  
  Example:
  ```sql
  SELECT id, txt FROM emails.customer_emails
  ```

- `system_message` *(str, required)*  
  System prompt that defines the assistant’s behavior for each row.  
  Example:  
  > "You are a sentiment analyzer. Classify the sentiment as positive, negative, or neutral."

**Behavior**

- Cleans the input SQL:
  - Normalizes whitespace.
  - Removes a trailing `;` if present.
- Escapes the system message for safe use inside Teradata SQL.
- Builds a `CompleteChat` call using configuration from `chat_config.yml`.
- Casts `response_txt` to `VARCHAR(output_text_length)` (UNICODE) where `output_text_length` comes from config.
- Returns a JSON payload containing:
  - `results`: one row per input row with at least `response_txt` and the original columns.
  - `metadata`: tool name, model, base URL, database name, row counts, and other details.

**Configuration**

Reads from `chat_config.yml`. Key fields:

- **Connection / routing**
  - `base_url` *(required)* – URL of the inference server (e.g. `http://localhost:11434` or `https://api.openai.com`).
  - `model` *(required)* – model identifier (e.g. `qwen2.5-coder:7b`, `gpt-4`).
  - `http_proxy` *(optional)* – proxy in `host:port` format; if empty or omitted, no proxy is used.
  - `ignore_https_verification` *(optional, default `false`)* – disable TLS verification (dev/test only).

- **Authentication**
  - Environment variable `CHAT_API_KEY` *(optional)* – if set, used as `Authorization: Bearer <APIKEY>`.

- **Request options**
  - `custom_headers` – list of `{ key, value }` HTTP headers.
  - `body_parameters` – list of `{ key, value }` entries added to JSON body (e.g. `temperature`, `max_tokens`, `response_format`).
  - `pem_file_sql` – optional SQL used to select a TLS certificate as a second input; if empty/not set, it is not added to the generated SQL.

- **Rate limiting**
  - `delays` – comma‑separated retry delays in ms for HTTP 429 (default `"500"`).
  - `retries_number` – number of retries on HTTP 429 (default `0`).
  - `throw_error_on_rate_limit` – if `true`, the table operator errors after retries; otherwise returns empty diagnostics.

- **Output**
  - `output_text_length` – max length of `response_txt` (default `16000`, allowed 2–32000).
  - `remove_deepseek_thinking` – if `true`, strips `<think>...</think>` blocks for DeepSeek‑style models.
  - `output.include_diagnostics` – include rate‑limit diagnostics columns.
  - `output.include_tachyon_headers` – include Tachyon headers (`x_request_id`, `x_correlation_id`, etc.).

- **Databases**
  - `databases.function_db` *(required)* – database where the `CompleteChat` function is installed  
    (for example, `openai_client`).

**Error handling**

- If mandatory config parameters (`base_url`, `model`, `databases.function_db`) are missing, the tool:
  - Logs a configuration error.
  - Returns a JSON response with `status: "error"` and `error_type: "configuration_error"`.
  - Does not attempt to run any SQL.

---

### `chat_aggregatedCompleteChat`

**What it does**

Runs `CompleteChat` over a dataset and **aggregates** the outputs to show unique `response_txt` values and their counts. This is useful for quick label distributions and analytics.

**Typical use cases**

- Count how many rows are classified into each category (e.g. sentiment labels).
- Analyze main reasons or topics in feedback at a high level.
- Combine with prompts (for example, `chat_ai_mapreduce`) to build map‑reduce workflows.

**Inputs (tool parameters)**

- `sql` *(str, required)*  
  Teradata SQL statement that returns a `txt` column.

- `system_message` *(str, required)*  
  System prompt that instructs the LLM to return **short, discrete labels** per row, so the aggregation is meaningful.

**Behavior**

- Uses the same configuration and SQL‑preparation pipeline as `chat_completeChat`.
- Internally calls `CompleteChat`, then runs an aggregation query:
  - Filters out `NULL` and empty `response_txt` values.
  - Groups by `response_txt`.
  - Counts occurrences into `response_count`.
- Returns JSON with:
  - `results`: one row per unique `response_txt` with `response_count`.
  - `metadata`: model, base URL, database, total and unique response counts, and aggregation details.

**Error handling**

- Shares the same mandatory config validation as `chat_completeChat`.
- On configuration errors, returns `status: "error"` and `error_type: "configuration_error"` and does not execute SQL.

---

## Skills

The multi‑step workflow that used to be the `chat_ai_mapreduce` MCP prompt (building an SQL query, running aggregated completion, and synthesizing a final answer) is now the [`chat-mapreduce-analysis`](../../skills/README.md) Agent Skill.

---

## Configuration file

Chat Completion tools read their configuration from: `text src/teradata_mcp_server/config/chat_config.yml`


You must set at least:

- `base_url`
- `model`
- `databases.function_db`

If these are missing or invalid, Chat Completion tools will be loaded in a disabled state and will return a configuration error when called.

---

[Return to Main README](../../../../README.md)