
# Customizing the Teradata MCP Server: Semantic Layers

The Teradata MCP server enables rapid creation of domain-focused semantic layers by allowing you to declaratively define custom tools, prompts, cubes, and glossary terms. This approach empowers admins and data teams to tailor the MCP experience to specific business domains—without writing Python code or modifying the server itself.

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
All custom objects can be defined in a YAML file (e.g., `sales_objects.yaml`, `finance_objects.yaml`). The file is a dictionary keyed by object name, with each entry specifying its type and details:

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

Profiles are specified in the `profiles.yml` file at the project root. Each profile defines which tools, prompts, and resources are enabled for a given context (e.g., user group, domain, or use case). Profiles use regular expression patterns to match tool, prompt, and resource names, allowing flexible grouping and reuse. 

For example, the following `profiles.yml` enables different sets of tools for two contexts (sales and dba):

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

You can run the MCP server with the `--profile` command-line argument or the `PROFILE` environment variable to select a profile at startup. If the profile is unspecified or set to `all`, all tools, resources, and prompts are loaded by default.

For example, to run the server with the pre-defined dba profile:

`teradata-mcp-server --profile dba`

## Custom Objects Implementation Details

### File Naming and Loading
All customizations must be defined in files named `*_objects.yaml` (e.g., `sales_objects.yaml`, `finance_objects.yaml`).

### Supported Object Types and Attribute Rules
Each entry in the YAML file is keyed by its name and must specify a `type`. Supported types and their required/optional attributes:

#### Tool
- **Required:**
  - `type`: Must be `tool`
  - `sql`: SQL query string (it can be a prepared statement with parameters)
  - `parameters`: Dictionary of parameter definitions
- **Optional:**
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
  - `description`: Text description of the prompt

#### Glossary
- **Required:**
  - `type`: Must be `glossary`
  - Each glossary term must have a `definition`
- **Optional:**
  - `synonyms`: List of synonyms for the term


### Dynamic Registration and Glossary Enrichment
- All objects are registered dynamically at server startup—no code changes required.
- You can add, update, or remove tools, cubes, prompts, or glossary terms by editing the YAML file and restarting the server.
- The server will register each tool, prompt, and cube using the dictionary key as its name.
- Glossary terms are automatically enriched with references from cubes.


## Best Practices

- Use separate YAML files for each domain for modularity and maintainability.
- Use clear, descriptive names for each tool, cube, and prompt.
- Document each parameter, dimension, and measure with a description.
- Keep glossary terms up to date, remember that measures and dimensions will automatically be reflected.

## Example

See the provided [`custom_objects.yaml`](../custom_objects.yaml) (or your domain-specific YAML file) for a complete example.
