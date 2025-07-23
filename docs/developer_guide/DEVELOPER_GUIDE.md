
# Development Conventions

This document provides guidelines for developing new tools for the Teradata MCP server.
<br>

## Directory Structure & File Naming

The directory structure will follow the following conventions
[root directory](./) - will contain:
- README.md - this will be the main readme file, outlining scope of project, grouping of tools, installation instructions, how to use instructions.
- LICENSE file - MIT license
- pyproject.toml - Project metadata
- uv.lock - uv package lock file contains detailed package information
- .gitignore - list of files and directories that should not be loaded into github
- .python-version - python version
- env - example environments file
- custom_tools.yaml - this will enable the deployment of custom tools as defined in the yaml file.

[logs directory](./logs/) - will contain log files, the detail of the log file will be determined in the server.py file.  Default is set to INFO.  This can be changed to DEBUG for very detailed logging.

[src/teradata_mcp_server](./src/teradata_mcp_server) - this will contain all source code.
- __init__.py - will contain server imports
- server.py - contains the main server script and will decorate tools, prompts, and resources.


[src/teradata_mcp_server/tools](./src/teradata_mcp_server/tools) - this will contain code to connect to the database as well as the modules.
- __init__.py - will contain tool module imports
- td_connect.py - contains the code responsible for connecting to Teradata.


We will modularize the tool sets so that users will have the ability to add the tool sets that they need to the server.  It is expected that groupings of tools will have a consistent naming convention so that they can be easily associated.  

[src/teradata_mcp_server/tools/base](./src/teradata_mcp_server/tools/base) - this will contain the base tool set:
- __init__.py - will contain library imports
- base_tools.py - will contain the tool handle code
- base_prompts.yml - will contain the object (e.g. prompts, etc) code
- base_resources.py - will contain the resource handle code
- README.md - will describe the tools, prompts, resources, and package dependencies

[src/teradata_mcp_server/tools/dba](./src/teradata_mcp_server/tools/dba) - this will contain DBA focused tools set:
- __init__.py - will contain library imports
- dba_tools.py - will contain the tool handle code
- dba_objects.yml - will contain the object (e.g. prompts, etc) code
- dba_resources.py - will contain the resource handle code
- README.md - will describe the tools, prompts, resources, and package dependencies

[src/teradata_mcp_server/tools/qlty](./src/teradata_mcp_server/tools/qlty) - this will contain data quality tool set:
- __init__.py - will contain library imports
- qlty_tools.py - will contain the tool handle code
- qlty_objects.yml - will contain the object (e.g. prompts, etc) code
- qlty_resources.py - will contain the resource handle code
- README.md - will describe the tools, prompts, resources, and package dependencies

[src/teradata_mcp_server/tools/sec](./src/teradata_mcp_server/tools/sec) - this will contain security tool set:
- __init__.py - will contain library imports
- sec_tools.py - will contain the tool handle code
- sec_objects.yml - will contain the object (e.g. prompts, etc) code
- sec_resources.py - will contain the resource handle code
- README.md - will describe the tools, prompts, resources, and package dependencies

[src/teradata_mcp_server/tools/fs](./src/teradata_mcp_server/tools/fs) - this will contain feature store (tdfs4ds package) tool set:
- __init__.py - will contain library imports
- fs_tools.py - will contain the tool handle code
- fs_prompts.py - will contain the prompt handle code
- fs_resources.py - will contain the resource handle code
- README.md - will describe the tools, prompts, resources, and package dependencies


[src/teradata_mcp_server/tools/rag](./src/teradata_mcp_server/tools/rag) - this will contain vector store tool set:
- __init__.py - will contain library imports
- rag_tools.py - will contain the tool handle code
- rag_prompts.py - will contain the prompt handle code
- rag_resources.py - will contain the resource handle code
- README.md - will describe the tools, prompts, resources, and package dependencies


**New tools sets**
New tool sets can be created in one of two ways:
1. Custom tools - this approach allows the custom_tools.yaml file to register allthe tool information.  This approach is suitable for tools that run predefined SQL against Teradata.
- using the custom_tools.yaml template 
- rename the the yaml file to the name of your tool set, ensuring that it ends in _tools.yaml
- ensure that the tool names correspond to the tool naming convention

2. New tool libraries - this approach requires changes to the server code, as defined below.
- grouping name should start with up to 4 characters that describes the module function
- Template code can be found in:
[src/teradata_mcp_server/tools/tmpl](./src/teradata_mcp_server/tools/tmpl) - this will contain template tool set:
- __init__.py - will contain library imports
- tmpl_tools.py - will contain the tool handle code
- tmpl_prompts.py - will contain the prompt handle code
- tmpl_resources.py - will contain the resource handle code
- README.md - will describe the tools, prompts, resources, and package dependencies

The template code should be copied and prefixes for directory name and files should be modified to align to your grouping name.  Refer to other tool sets for examples.

[src/test/](./src/test/) - this will contain client tools for testing the server functionality

[docs](./docs/) - contains package documentation.
- CHANGE_LOG.md - maintains the change log of releases.
- CLIENT_GUIDE.md - explains how to connect common clients to the server.
- CONTRIBUTING.md - guidelines for contributors
- GETTING_STARTED.md - explains how to get the server up and running
- SECURITY.md - explains how to register security issues

[docs/developer_guide](./docs/developer_guide) - contains developer package documentation.
- DEVELOPER_GUIDE.md - explains structural elements of the server for developers.
- HOW_TO_ADD_YOUR_FUNCTION.md - explains how to add tools to a module


<br>

## Tool/Prompt/Resource Naming Convention
To assist tool users we would like to align tool, prompt, and resources to a naming convention, this will assist MCP clients to group tools and understand its function.

- tool/prompt/resource name starts the grouping identifier (e.g. base).
- The tool/prompt/resource should have a descriptive name that is short, use lowercase with captials for new words.  (e.g. base_databaseList, qlty_missingValues, dba_tableSpace, dba_resusageUserSummary)

Two guides have been created to show how to add tools and prompts:
- [How to add new modules of tools](./HOW_TO_ADD_YOUR_FUNCTION.md)


<br>

## Tools testing
Every module will have at least one prompt that would be responsible for testing all of the tools in the module.  The following template should be used in the module_objects.ylm file, the name of the testig prompt should be test_\<module name\>Tools:

```
test_baseTools:
  type: prompt
  description: "Test all base tools in the Teradata MCP server."
  prompt: |
   You are a Testor who is an expert in testing the functionality of tools in the base module. You will test all tools in the module.
   ## your role will work through the phases
   Perform the phases in order, and do not skip any phase.
   
   ## Phase 0 - Get a list of databases
   - Get a list of databases from the user. Use the base_databaseList function to get the list.  The tool should return a list of databases in the Teradata system.
   ## Phase 1 - Get the list of tables in each database
   - For the DBC database, get the list of tables. Use the base_tableList function to get the list. The tool should return a list of tables in the DBC database.
   ## Phase 2 - Create a test table in your default database
   - Create a customer table in your default database called test_customer, the table should have an Cust_id column. Use the base_writeQuery function to create the table. A test_customer table should be created.
   - Add 10 rows to the test_customer table. Use the base_writeQuery function to add the rows.
   ## Phase 3 - Test the query tool
   - test the query tool by running a query on the test_customer table. Use the base_readQuery function to run the query. The query should return the 10 rows you added in the previous phase.
   - test the query tool by running a query on the test_customer table with a filter. Use the base_readQuery function to run the query. The query should return only the rows that match the filter. (example of a filter is Cust_id > 5)
   ## Phase 4 - Test the table DDL tool
   - Get the DDL of the test_customer table. Use the base_tableDDL function to get the DDL. The tool should return the DDL of the test_customer table.
   ## Phase 5 - Test the column description tool
   - Get the column description of the test_customer table. Use the base_columnDescription function to get the columns description. The tool should return the column description of the test_customer table.
   ## Phase 6 - Test the table preview tool
   - Get the preview of the test_customer table. Use the base_tablePreview function to get the preview. The tool should return the first 5 rows of the test_customer table and the column information.
   ## Phase 7 - Test the table affinity tool
   - Get the table affinity of the test_customer table. Use the base_tableAffinity function to get the affinity. The tool should return the table affinity of the test_customer table.
   ## Phase 8 - Test the table usage tool
   - Get the table usage of the test_customer table. Use the base_tableUsage function to get the usage. The tool should return the table usage of the test_customer table.
   ## Phase 9 - Clean up
   - Drop the test_customer table. Use the base_writeQuery function to drop the table. The tool should return a success message.
   ## Communication guidelines:
         - Be concise but informative in your explanations
         - Clearly indicate which phase the process is currently in
         - summarize the success of the phase before moving to the next phase
   ## Final output guidelines:
         - return in markdown results for all phases
         - Example:
         ***Phase 0:*** list databases:  Successful
         ***Phase 1:*** list tables in DBC database:  Successful
         ***Phase 2:*** Create test_customer table:  Successful

```

<br><br><br>

# Development Cycle

## Requesting Capabilities
- Go to github Issues tab
- click on New Issue
- click on Feature Request
- Fill out Feature Request form
    - Create a title
    - Add a description

## Raising incidents
- Go to github Issues tab
- click on New Issue
- click on Bug report
- Fill out Bug Report form
    - Create a title
    - Add a description


## Submitting Code
All contributions to the repository should be made through the Github pull request process.   [Contributing to a project step by step instuctions](https://docs.github.com/en/get-started/exploring-projects-on-github/contributing-to-a-project)

The repository admins will review the code for compliance and either provide feedback or merge the code.
