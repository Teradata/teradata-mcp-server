
# Customizing the MCP Server: Semantic Layers

> **📍 Navigation:** [Documentation Home](../README.md) | [Server Guide](../README.md#-server-guide) | [Getting started](GETTING_STARTED.md) | [Architecture](ARCHITECTURE.md) | [Installation](INSTALLATION.md) | [Configuration](CONFIGURATION.md) | [Security](SECURITY.md) | [<u>**Customization**</u>](CUSTOMIZING.md) | [Client Guide](../client_guide/CLIENT_GUIDE.md)


The Teradata MCP server enables rapid creation of domain-focused semantic layers by allowing you to declaratively define custom tools, prompts, cubes, and glossary terms. No code change needed, you can customize the server by placing YAML files in your current working directory. This approach empowers admins and data teams to tailor the MCP experience to specific business domains—without writing Python code or modifying the server itself.

You may use the [MCP Customization Agent Skill](https://github.com/Teradata/teradata-mcp-server/blob/main/agentic/skills/teradata-mcp-customisation/SKILL.md) to create semantic layer configuration based on your existing documentation.

## Key principles

- **Domain Focus:** Build MCP servers that speak your users' language and provide business-relevant tools and explanations.
- **Controlled Access:** Predefine queries, semantic layers, and resources to ensure correctness, security, and optimal resource utilization.
- **Declarative Workflow:** All customization is done via YAML—no code changes required. Admins can add, update, or remove domain logic by editing a single file.
- **Trustworthy Outcomes:** By specifying queries and logic up front, you avoid the risks of LLMs repeatedly "guessing" at database structure, ensuring reliable, consistent and auditable results.

### Semantic Layer
A semantic layer in this context is a collection of custom tools, prompts, cubes, and glossary terms focused on a specific business domain (e.g., sales, finance, HR). It provides:
- **Custom Tools:** Parameterized SQL queries exposed as callable MCP tools.
- **Cubes:** Semantic container defining business metrics and associated dimensions. Compiles and execute SQL at runtime.
- **Prompts:** Predefined user prompts for natural language interactions.
- **Glossary:** Domain-specific terms, definitions, and synonyms, automatically enriched from cubes and tools.
- **Profiles:** Named sets of tools, prompts, and resources that enable domain-specific server instantiations.

### Declarative Specification
All custom objects can be defined in an object YAML file (e.g., `sales_objects.yml`, `finance_objects.yml`). The file is a dictionary keyed by object name, with each entry specifying its type and details:

```yaml
sales_by_region:
  type: cube
  description: Sales metrics by region and product
  sql: |
    SELECT region, product, amount AS total_sales FROM sales_data
  dimensions:
    region:
      description: Sales region
      expression: region
    product:
      description: Product name
      expression: product
  measures:
    total_sales:
      description: Total sales amount
      expression: SUM(amount)

dbc_space_cube:
  type: cube
  description: Teradata space usage cube with optional table metadata.
  sql: |
    SELECT
      DataBaseName,
      TableName,
      CurrentPerm,
      PeakPerm,
      MaxPerm
    FROM DBC.AllSpaceV
    WHERE TableName <> 'All'
  joins:
    - name: databases
      sql: DBC.DatabasesV
      on: "dbc_space_cube.DataBaseName = databases.DatabaseName"
      type: left
      optional: false
    - name: tables
      sql: DBC.TablesV
      on: >-
        dbc_space_cube.DataBaseName = tables.DatabaseName
        AND dbc_space_cube.TableName = tables.TableName
        AND COALESCE(:tablekind, tables.TableKind) = tables.TableKind
      type: left
      optional: true
  dimensions:
    database_name:
      description: Database name.
      expression: dbc_space_cube.DataBaseName
    owner_name:
      description: Database owner.
      expression: databases.OwnerName
    table_kind:
      description: Object kind from DBC.TablesV.
      expression: tables.TableKind
  measures:
    current_perm_bytes:
      description: Current permanent space in bytes.
      expression: SUM(dbc_space_cube.CurrentPerm)
  parameters:
    tablekind:
      description: Optional object kind filter, for example T or V.
      optional: true

get_top_customers:
  type: tool
  description: Get top N customers by sales
  sql: |
    SELECT customer, SUM(amount) AS total FROM sales_data GROUP BY customer ORDER BY total DESC LIMIT %(limit)s
  parameters:
    limit:
      description: Number of top customers to return

sales_analyst:
  type: prompt
  description: Customer sales analysis prompt
  prompt: "You are a helpful sales data analyst, you make sure that all your statements are backed by actual data and are ready to share details of your analysis."

glossary:
  type: glossary
  customer:
    definition: A person or company that purchases goods or services.
    synonyms: 
     - client
     - buyer
```

## Configuration Files and Loading

The server uses a **layered configuration system** that loads and merges configurations from multiple sources. See the [Configuration Guide](CONFIGURATION.md#layered-configuration-strategy) for full details.

### Configuration Directory

You can specify a custom configuration directory using the `--config_dir` parameter or `CONFIG_DIR` environment variable:

```bash
# Using command line
teradata-mcp-server --config_dir /path/to/my/config --profile sales

# Using environment variable
export CONFIG_DIR=/path/to/my/config
teradata-mcp-server --profile sales
```

**Default:** If not specified, the current working directory is used.

### Profiles Configuration

**Default profiles** are packaged with the server installation in `src/teradata_mcp_server/config/profiles.yml`. You can override or extend these by creating a `profiles.yml` file in your **configuration directory**.

The server uses a **simple override strategy**, so your custom `profiles.yml` can:
- Add new profiles
- Override existing profiles entirely (top-level keys are replaced completely)

Each profile defines which tools, prompts, and resources are enabled for a given context (e.g., user group, domain, or use case). Profiles use regular expression patterns to match tool, prompt, and resource names, allowing flexible grouping and reuse.

**Example `profiles.yml` in your config directory:**
```yaml
sales:
  tool:
    - sales_.*
  prompt:
    - sales_.*
  resource:
    - sales_.*
dba:
  tool:
    - dba_.*
    - base_.*
    - sec_.*
  prompt:
    - dba_.*
```

**Configuration loading priority:**
1. **Packaged defaults** - Built-in profiles shipped with the package
2. **Config directory** - Your `profiles.yml` in the config directory (top-level keys replace packaged profiles)

### Running with Profiles

You can run the MCP server with the `--profile` command-line argument or the `PROFILE` environment variable to select a profile at startup. If the profile is unspecified or set to `all`, all tools, resources, and prompts are loaded by default.

**Examples:**
```bash
# PyPI installation
teradata-mcp-server --profile dba

# Development build  
uv run teradata-mcp-server --profile sales
```

## Custom Objects Implementation Details

### Custom Objects Loading

The server loads custom objects (tools, cubes, prompts, glossaries) from multiple sources:

**Configuration loading priority:**
1. **Packaged defaults** - Built-in objects from `src/tools/*/*.yml` (shipped with package)
2. **Config directory** - Any `*_objects.yml` files in your config directory (overrides packaged objects by name)

**File naming:** Custom object files in your config directory should be named `*_objects.yml` (e.g., `sales_objects.yml`, `finance_objects.yml`, `my_custom_objects.yml`). The special config files (`profiles.yml`, `chat_config.yml`, `rag_config.yml`, `sql_opt_config.yml`) are handled separately using the layered configuration system.

### Supported Object Types and Attribute Rules
Each entry in the YAML file is keyed by its name and must specify a `type`. Supported types and their required/optional attributes:

#### Tool
- **Required:**
  - `type`: Must be `tool`
  - `sql`: SQL query string (it can be a prepared statement with parameters)
- **Optional:**
  - `parameters`: Dictionary of parameter name (key) and properties (dictionary with `description`, `default`, `type_hint`}) - if used in the sql
  - `description`: Text description of the tool

#### Cube
- **Required:**
  - `type`: Must be `cube`
  - `sql`: SQL base query or table
  - `dimensions`: Dictionary of dimension definitions (each with `expression`)
  - `measures`: Dictionary of measure definitions (each with `expression`)
- **Optional:**
  - `description`: Text description of the cube
  - `joins`: List of relations definitions add related tables/views to the model. Joins are materialized by the compiler only when needed for a selected dimension/metric requested otherwise.
  - `parameters`: Dictionary of parameter name (key) and properties (dictionary with `description`, `default`, `optional`, `required`, `type_hint`) - if used in the sql or join conditions

Cube definitions are exposed as MCP tools. The server generates the tool signature from the cube definition:

```python
my_cube(
    dimensions: str,   # comma-separated dimension names to group by
    measures: str,     # comma-separated measure names to aggregate
    filter: str = "",  # pre-aggregation SQL filter
    res_filter: str = "",  # post-aggregation result filter
    order_by: str = "",
    top: int | None = None,
    # plus custom parameters declared under parameters:
)
```

`dimensions` and `measures` must use the public names listed in the cube definition. Unknown dimension or measure names fail before SQL is sent to the database, with an error listing allowed names.

##### Cube filters

Cubes support two filter phases:

- `filter`: Runs before aggregation. Use it to reduce the base row set before `GROUP BY`. It can reference cube dimension names even when those dimensions are not selected in `dimensions`. The server rewrites dimension names to their configured SQL expressions and materializes any optional join referenced by those expressions.
- `res_filter`: Runs after aggregation. Use it to filter computed result columns, such as `current_perm_bytes > 1000000000`.

Example:

```yaml
# Tool call arguments
dimensions: "database_name"
measures: "current_perm_bytes"
filter: "table_kind = 'T'"
```

If `table_kind` is defined as `tables.TableKind`, the generated pre-aggregation filter uses:

```sql
WHERE tables.TableKind = 'T'
```

and the optional `tables` join is materialized even though `table_kind` is not part of the grouping dimensions.

##### Cube joins

`joins` add related sources at the same query level as the cube's base SQL, making join aliases available to dimension and measure expressions.

Each join supports:

- `name`: Join alias. Dimension and measure expressions reference this alias, for example `tables.TableKind`.
- `sql`: Table/view name or SQL subquery to join.
- `on`: Join condition.
- `type`: Join type, such as `left` or `inner`. Defaults to `inner`.
- `optional`: When `false`, the join is always materialized. When `true` or omitted, the join is materialized only if selected dimensions, selected measures, `filter`, or meaningful custom parameters require it.

Optional parameters can be declared with `optional: true`, `required: false`, or a `default`. For nullable optional parameters, blank values and common placeholders such as `No value`, `NULL`, `None`, `NA`, and `N/A` are treated as SQL `NULL`.
  
#### Prompt
- **Required:**
  - `type`: Must be `prompt`
  - `prompt`: Text of the prompt
- **Optional:**
  - `parameters`: Dictionary of parameter name (key) and definitions (value) - if used in the prompt
  - `description`: Text description of the prompt

#### Glossary
- **Required:**
  - `type`: Must be `glossary`
  - Each glossary term must have a `definition`
- **Optional:**
  - `synonyms`: List of synonyms for the term


### Dynamic Registration and Glossary Enrichment
- All objects are registered dynamically at server startup—no code changes required.
- You can add, update, or remove tools, cubes, prompts, or glossary terms by creating/editing YAML files in your **config directory** and restarting the server.
- Config directory files override packaged defaults by object name, so you can customize existing objects or add new ones.
- The server will register each tool, prompt, and cube using the dictionary key as its name.
- Glossary terms are automatically enriched with references from cubes and tools.

### Quick Start for Customization

1. **Install from PyPI:** `pip install teradata-mcp-server`
2. **Create config directory:** `mkdir my-teradata-config`
3. **Create custom objects:** Add your `*_objects.yml` files (e.g., `my_objects.yml`) to the config directory
4. **Optionally customize profiles:** Create `profiles.yml` in config directory to override default profiles
5. **Run server:** `teradata-mcp-server --config_dir my-teradata-config --profile my_profile`

The server will automatically load packaged defaults plus your custom configurations from the config directory.


## Database Tool Registry

As an alternative to YAML files, you can register tools directly in the Teradata database. This is useful when tool definitions live alongside the database objects they wrap, or when you want to control tool availability through database-level permissions.

The registry reads two views from a designated database schema (`mcp` by default):
- **`mcp_list_tools`** — one row per tool (name, target object, description)
- **`mcp_list_toolParams`** — one row per parameter (type, position, required flag)

Supported object types: UDFs (`F`), Macros (`M`), Tables (`T`), Views (`V`).

### Enabling the Registry

Add a `registry` key to your profile in `profiles.yml`:

```yaml
my-registry-profile:
  registry: "mcp"   # database schema containing the registry views
  tool:
    - "^base_.*"    # code-based tools to load alongside registry tools
  prompt:
    - ".*"
```

Then start the server with that profile:

```bash
teradata-mcp-server --profile my-registry-profile
```

Registry tools are loaded on the first database connection. They are always loaded in full — profile `tool` patterns apply only to code-based tools, not registry tools.

### User Filtering

Use `WHERE USER IN (...)` in your `mcp_list_tools` view to expose only the tools relevant to the connecting database user. This enables per-server or per-user tool sets from a shared registry.

See the [registry developer guide](../developer_guide/REGISTRY_IMPLEMENTATION.md) and the [example SQL setup](../../examples/server-customization/registry_setup.sql) for full schema details and worked examples.

## Best Practices

- **Organize by domain:** Use separate YAML files for each business domain (e.g., `sales_objects.yml`, `finance_objects.yml`)
- **Use descriptive names:** Clear, descriptive names for each tool, cube, and prompt help users understand their purpose
- **Document everything:** Add descriptions to all parameters, dimensions, and measures
- **Config directory approach:** Create a dedicated directory for your custom configurations and use `--config_dir` to point to it
- **Version control:** Keep your custom YAML files in version control for change tracking
- **Test profiles:** Create profiles that match your user groups' needs and permissions

## Examples

### Working Directory Structure
```
my-teradata-config/
├── profiles.yml           # Custom profiles (optional)
├── sales_objects.yml      # Sales domain tools and cubes
├── finance_objects.yml    # Finance domain objects
└── hr_objects.yml         # HR domain tools
```

### Complete Example
See the provided [`custom_objects.yml`](../../examples/server-customisation/custom_objects.yml) in the repository for a complete working example.

### Running with Custom Configuration
```bash
# Run server with config directory and profile
teradata-mcp-server --config_dir my-teradata-config --profile sales

# Server automatically loads (layered):
# 1. Packaged defaults (from installation)
# 2. Your custom YAML files (from config directory)
# 3. Your custom profiles.yml (if present, top-level keys override packaged)
```
