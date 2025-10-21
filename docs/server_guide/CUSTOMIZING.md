
# Customizing the MCP Server: Semantic Layers

> **📍 Navigation:** [Documentation Home](../README.md) | [Server Guide](../README.md#-server-guide) | [Getting started](GETTING_STARTED.md) | [Architecture](ARCHITECTURE.md) | [Installation](INSTALLATION.md) | [Configuration](CONFIGURATION.md) | [Security](SECURITY.md) | [<u>**Customization**</u>](CUSTOMIZING.md) | [Client Guide](../client_guide/CLIENT_GUIDE.md)


The Teradata MCP server enables rapid creation of domain-focused semantic layers by allowing you to declaratively define custom tools, prompts, cubes, and glossary terms. No code change needed, you can customize the server by placing YAML files in your current working directory. This approach empowers admins and data teams to tailor the MCP experience to specific business domains—without writing Python code or modifying the server itself.

## Key principles

- **Domain Focus:** Build MCP servers that speak your users' language and provide business-relevant tools and explanations.
- **Controlled Access:** Predefine queries, aggregations, and resources to ensure correctness, security, and optimal resource utilization.
- **Declarative Workflow:** All customization is done via YAML—no code changes required. Admins can add, update, or remove domain logic by editing a single file.
- **Trustworthy Outcomes:** By specifying queries and logic up front, you avoid the risks of LLMs repeatedly "guessing" at database structure, ensuring reliable, consistent and auditable results.

### Semantic Layer
A semantic layer in this context is a collection of custom tools, prompts, cubes, and glossary terms focused on a specific business domain (e.g., sales, finance, HR). It provides:
- **Custom Tools:** Parameterized SQL queries exposed as callable MCP tools.
- **Prompts:** Predefined user prompts for natural language interactions.
- **Cubes:** Aggregation templates for business metrics, with dimensions and measures.
- **Glossary:** Domain-specific terms, definitions, and synonyms, automatically enriched from cubes and tools.
- **Profiles:** Named sets of tools, prompts, and resources that enable domain-specific server instantiations.

### Declarative Specification
All custom objects can be defined in a YAML file (e.g., `sales_objects.yml`, `finance_objects.yml`). The file is a dictionary keyed by object name, with each entry specifying its type and details:

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

The server uses a hierarchical configuration system that loads configurations from multiple sources:

### Profiles Configuration

**Default profiles** are packaged with the server installation. You can override or extend these by creating a `profiles.yml` file in your **current working directory** (where you run the server from).

Each profile defines which tools, prompts, and resources are enabled for a given context (e.g., user group, domain, or use case). Profiles use regular expression patterns to match tool, prompt, and resource names, allowing flexible grouping and reuse.

**Example `profiles.yml` in your working directory:**
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
2. **Working directory** - Your local `profiles.yml` (overrides packaged profiles)

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
2. **Working directory** - Any `*.yml` files in your current working directory (overrides packaged objects)

**File naming:** Custom object files should be named `*.yml` (e.g., `sales_objects.yml`, `finance_objects.yml`, `my_custom_tools.yml`). The `profiles.yml` file is handled separately.

### Supported Object Types and Attribute Rules
Each entry in the YAML file is keyed by its name and must specify a `type`. Supported types and their required/optional attributes:

#### Tool
- **Required:**
  - `type`: Must be `tool`
  - `sql`: SQL query string (it can be a prepared statement with parameters)
- **Optional:**
  - `parameters`: Dictionary of parameter name (key) and definitions (value) - if used in the sql
  - `description`: Text description of the tool

#### Cube
- **Required:**
  - `type`: Must be `cube`
  - `sql`: SQL base query
  - `dimensions`: Dictionary of dimension definitions (each with `expression`)
  - `measures`: Dictionary of measure definitions (each with `expression`)
- **Optional:**
  - `description`: Text description of the cube

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
- You can add, update, or remove tools, cubes, prompts, or glossary terms by creating/editing YAML files in your **current working directory** and restarting the server.
- Working directory files override packaged defaults, so you can customize existing objects or add new ones.
- The server will register each tool, prompt, and cube using the dictionary key as its name.
- Glossary terms are automatically enriched with references from cubes and tools.

### Quick Start for Customization

1. **Install from PyPI:** `pip install teradata-mcp-server`
2. **Create working directory:** `mkdir my-teradata-config && cd my-teradata-config`
3. **Create custom objects:** Add your `*.yml` files (e.g., `my_tools.yml`)
4. **Optionally customize profiles:** Create `profiles.yml` to override default profiles
5. **Run server:** `teradata-mcp-server --profile my_profile`

The server will automatically load packaged defaults plus your custom configurations.


## Best Practices

- **Organize by domain:** Use separate YAML files for each business domain (e.g., `sales_tools.yml`, `finance_metrics.yml`)
- **Use descriptive names:** Clear, descriptive names for each tool, cube, and prompt help users understand their purpose  
- **Document everything:** Add descriptions to all parameters, dimensions, and measures
- **Working directory approach:** Create a dedicated directory for your custom configurations to keep them organized
- **Version control:** Keep your custom YAML files in version control for change tracking
- **Test profiles:** Create profiles that match your user groups' needs and permissions

## Examples

### Working Directory Structure
```
my-teradata-config/
├── profiles.yml           # Custom profiles (optional)
├── sales_objects.yml      # Sales domain tools and cubes
├── finance_metrics.yml    # Finance domain objects
└── hr_tools.yml          # HR domain tools
```

### Complete Example
See the provided [`custom_objects.yml`](../custom_objects.yml) in the repository for a complete working example.

### Running with Custom Configuration
```bash
# Navigate to your config directory
cd my-teradata-config

# Run server with custom objects and profiles
teradata-mcp-server --profile sales

# Server automatically loads:
# 1. Packaged defaults (from installation)
# 2. Your custom YAML files (from current directory)
# 3. Your custom profiles.yml (if present)
```
