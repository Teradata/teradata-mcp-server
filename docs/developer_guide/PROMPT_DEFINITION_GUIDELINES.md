# MCP Workflow Prompt Guidelines

To ensure that LLMs and Clients can reliably parse and execute multi-step workflows in an efficient "headless" mode, all workflow prompts must adhere to the following structural and semantic guidelines.

---

## 1. Core Principles

* **Clarity over cleverness**: The plan should be written as a simple, unambiguous set of instructions. Avoid complex prose or implicit steps.

* **Structure is mandatory**: The parser relies on specific Markdown elements (headers, lists) and keywords to understand the plan's logic.

* **One action per step**: Each bullet point should correspond to a single tool call.

---

## 2. Structural Requirements

### a. Overall Structure

The prompt should be divided into logical **Phases** using Markdown H2 headers. Each phase represents a major stage of the workflow.

* `# Name: [Prompt Name]`

* `# Description: [High-level description of the prompt's purpose]`

* `## Phase 1 - [Descriptive Name of Phase]`

* `...`

* `## Phase 2 - [Descriptive Name of Phase]`

* `...`

### b. Steps

Within each phase, individual actions **must** be specified as bullet points (`-`). Each bullet point represents a single step in the sequence.

#### Example: Phase 2 - Collect Table Information

* **Step 1**: Get the table structure using the `base_tableDDL` tool.

* **Step 2**: Gather column statistics using the `qlty_columnSummary` tool.

### c. Loops

Loops **must** be explicitly declared using one of the following keyword phrases:

* `Cycle through the list of [items]...`

* `For each [item] in the list...`

The placeholder `[items]` (e.g., "tables", "columns") is crucial for the parser to understand what it is iterating over. The steps to be executed inside the loop should be defined in an indented list immediately following the loop declaration.

#### Example: Phase 2 - Collect Table Information

Cycle through the list of tables, for each table do the following steps in order:

* **Step 1**: Get the table structure using the `base_tableDDL` tool.

* **Step 2**: Gather column statistics using the `qlty_columnSummary` tool.

---

## 3. Semantic Requirements

### a. Explicit Tool Naming

Every action step **must** explicitly name the tool to be used with the phrase `...using the [tool_name] tool`. The `[tool_name]` must match the exact name of a tool available on the MCP server.

### b. Parameter Placeholders

When a tool's argument should be filled in dynamically from the context of a loop, use the singular form of the loop item as a placeholder. The headless executor's **Authoritative Context Stack** will automatically substitute this at runtime.

* If the loop is `For each table...`, the steps inside can refer to `table_name`.

* If the loop is `For each column...`, the steps inside can refer to `column_name`.

* **Do not** hardcode specific values inside a loop's definition.

### c. Best Practices for Parameter Definition on MCP Server

For effective and robust workflows, parameters should be clearly defined within the MCP environment, often resembling a YAML schema. Here's an example:

```yaml
# Example Parameter Definition for an MCP Tool
tool_parameters:
  database_name:
    description: "The name of the database to connect to."
    type: "string"
    required: true
    default: "default_db" # Optional: provides a fallback if not specified
  table_name:
    description: "The name of the table to perform operations on."
    type: "string"
    required: false # Can be omitted if a default is provided or it's genuinely optional
  analysis_level:
    description: "A numeric value indicating the depth or intensity of the analysis (e.g., 1 for basic, 5 for comprehensive)."
    type: "integer" # Using an integer type
    required: true
    default: 3
  output_format:
    description: "The desired format for the output data."
    type: "string"
    required: false
    default: "json"
```

In this structure:

* `description`: Provides a human-readable explanation of the parameter's purpose.

* `type`: Specifies the data type expected for the parameter (e.g., `string`, `integer`, `boolean`, `enum`).

* `required`: A boolean (`true`/`false`) indicating whether the parameter **must** be provided for the tool to execute.

* `default`: An optional value that will be used if the parameter is not explicitly provided in the workflow step.

---

## 4. Example: Complete Workflow Prompt

Here is a complete example of a well-formed workflow prompt that adheres to all guidelines from Chapters 1, 2, and 3. This structure enables specialised clients to parse the entire plan once and then execute it deterministically, only calling the LLM if an error occurs.

### Workflow Prompt Parameters

These are the parameters that the workflow prompt itself accepts as input:

```yaml
workflow_parameters:
  db_name:
    description: "The name of the database to be audited."
    type: "string"
    required: true
```

### Workflow Prompt

```markdown
# Name: Database Schema and Quality Audit
# Description:
You are a Teradata DBA performing a full schema and quality audit on a given database.

## Phase 1 - Get Database Objects
- Get a list of tables in the {db_name} database using the `base_tableList` tool.

## Phase 2 - Detailed Table Analysis
Cycle through the list of tables, for each table do the following steps in order:
  - Step 1: Get the table's DDL using the `base_tableDDL` tool.
  - Step 2: Get a summary of all columns in the table using the `base_columnDescription` tool.
  - Step 3: Check for missing values in the table using the `qlty_missingValues` tool.

## Phase 3 - Final Summary
- You have now collected all the necessary data. Synthesize the results to provide a final report.
