import os
import asyncio
import logging
import signal
import json
import yaml
from typing import Any, List, Optional
from pydantic import Field, BaseModel
import mcp.types as types
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.prompts.base import UserMessage, TextContent
from dotenv import load_dotenv
import tdfs4ds
import teradataml as tdml
import inspect
from sqlalchemy.engine import Connection
import argparse
import re
import functools

# Import the ai_tools module, clone-and-run friendly
try:
    from teradata_mcp_server import tools as td
except ImportError:
    import tools as td
import glob

load_dotenv()


# Parse command line arguments - if any they will override environment variables
parser = argparse.ArgumentParser(description="Teradata MCP Server")
parser.add_argument('--profile', type=str, required=False, help='Profile name to load from configure_tools.yml')
parser.add_argument('--database_uri', type=str, required=False, help='Database URI to connect to: teradata://username:password@host:1025/schemaname')
parser.add_argument('--mcp_transport', type=str, required=False, help='MCP transport method to use: stdio, streamable-http, sse')
parser.add_argument('--mcp_host', type=str, required=False, help='MCP host address')
parser.add_argument('--mcp_port', type=int, required=False, help='MCP port number')
parser.add_argument('--mcp_path', type=str, required=False, help='MCP path for the server')

# Extract known arguments and load them into the environment if provided
args, unknown = parser.parse_known_args()
for key, value in vars(args).items():
    if value is not None:
        os.environ[key.upper()] = str(value)

profile_name = os.getenv("PROFILE")

# Load tool configuration from YAML file
with open('profiles.yml', 'r') as file:
    all_profiles = yaml.safe_load(file)
    if not profile_name:
        print(f"No profile specified, load all tools, prompts and resources.")
        config={'tool': ['.*'], 'prompt': ['.*'], 'resource': ['.*']}
    elif profile_name not in all_profiles:
        raise ValueError(f"Profile '{profile_name}' not found in profiles.yml. Available: {list(all_profiles.keys())}.")
    else:
        config = all_profiles.get(profile_name)

# Set up logging
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(),
              logging.FileHandler(os.path.join("logs", "teradata_mcp_server.log"))],
)
logger = logging.getLogger("teradata_mcp_server")    
logger.info("Starting Teradata MCP server")

# Connect to MCP server
mcp = FastMCP("teradata-mcp-server")

#global shutdown flag
shutdown_in_progress = False

# Initiate connection to Teradata
_tdconn = td.TDConn()

#afm-defect:
_enableEVS = False
# Only attempt to connect to EVS is the system has an EVS installed/configured
if (len(os.getenv("VS_NAME", "").strip()) > 0):
    try:
        _evs    = td.get_evs()
        _enableEVS = True
    except:
        logger.error("Unable to establish connection to EVS, disabling")
        
#afm-defect: moved establish teradataml connection into main TDConn to enable auto-reconnect.
#td.teradataml_connection()



#------------------ Tool utilies  ------------------#
ResponseType = List[types.TextContent | types.ImageContent | types.EmbeddedResource]

def format_text_response(text: Any) -> ResponseType:
    """Format a text response."""
    if isinstance(text, str):
        try:
            # Try to parse as JSON if it's a string
            parsed = json.loads(text)
            return [types.TextContent(
                type="text", 
                text=json.dumps(parsed, indent=2, ensure_ascii=False)
            )]
        except json.JSONDecodeError:
            # If not JSON, return as plain text
            return [types.TextContent(type="text", text=str(text))]
    # For non-string types, convert to string
    return [types.TextContent(type="text", text=str(text))]

def format_error_response(error: str) -> ResponseType:
    """Format an error response."""
    return format_text_response(f"Error: {error}")

def execute_db_tool(tool, *args, **kwargs):
    """
    Execute a database tool with the given connection and arguments.
    Currently support both tools expecting DB API or SQLAlchemy engine:
      - If annotated Connection, pass SQLAlchemy engine
      - Otherwise, pass raw DB-API connection
    The second option should be eventually retired as all tools move to SQLAlchemy.
    """
    global _tdconn
    # (Re)initialize if needed
    if not getattr(_tdconn, "engine", None):
        logger.info("Reinitializing TDConn")
        _tdconn = td.TDConn()

    # Check is the first argument of the tool is a SQLAlchemy Connection
    sig = inspect.signature(tool)
    first_param = next(iter(sig.parameters.values()))
    ann = first_param.annotation
    use_sqla = inspect.isclass(ann) and issubclass(ann, Connection)

    try:
        if use_sqla:
            # Use a Connection that has .execute()
            with _tdconn.engine.connect() as conn:
                result = tool(conn, *args, **kwargs)
        else:
            # Raw DB-API path
            raw = _tdconn.engine.raw_connection()
            try:
                result = tool(raw, *args, **kwargs)
            finally:
                raw.close()

        return format_text_response(result)

    except Exception as e:
        logger.error(f"Error in execute_db_tool: {e}", exc_info=True)
        return format_error_response(str(e))

def execute_vs_tool(tool, *args, **kwargs) -> ResponseType:
    global _evs
    global _enableEVS

    if _enableEVS:
        try:
            return format_text_response(tool(_evs, *args, **kwargs))
        except Exception as e:
            if "401" in str(e) or "Session expired" in str(e):
                logger.warning("EVS session expired, refreshing …")
                _evs = td.evs_connect.refresh_evs()
                try:
                    return format_text_response(tool(_evs, *args, **kwargs))
                except Exception as retry_err:
                    logger.error(f"EVS retry failed: {retry_err}")
                    return format_error_response(f"After refresh, still failed: {retry_err}")
    
            logger.error(f"EVS tool error: {e}")
            return format_error_response(str(e))
    else:
        return format_error_response("Enterprise Vector Store is not available on this server.")

    

def make_tool_wrapper(func):
    """
    Given a handle_* function, return an async wrapper with:
    - the same signature minus the first 'connection' param
    - a call into execute_db_tool
    """

    sig = inspect.signature(func)
    # Drop first param (connection) and skip 'tool_name' if present
    first_param = next(iter(sig.parameters))
    params = [
        p for name, p in sig.parameters.items()
        if name != first_param
        and name != "tool_name" # skip tool_name if present as this allows to override the tool name for query tools declared in # the *_objects.yml files
        and p.kind in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)
    ]
    new_sig = sig.replace(parameters=params)

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        ba = new_sig.bind_partial(*args, **kwargs)
        ba.apply_defaults()

        return execute_db_tool(func, **ba.arguments)

    wrapper.__signature__ = new_sig
    return wrapper

#------------------ Register objects defined as code under ./src/teradata_mcp_server/tools/  ------------------#
def register_td_tools(config, td, mcp):
    patterns = config.get('tool', [])
    for name, func in inspect.getmembers(td, inspect.isfunction):
        if not name.startswith("handle_") or name.startswith("handle_fs_"):
            continue

        tool_name = name[len("handle_"):]
        if not any(re.match(p, tool_name) for p in patterns):
            continue

        wrapped = make_tool_wrapper(func)
        mcp.tool(name=tool_name, description=wrapped.__doc__)(wrapped)
        logger.info(f"Created tool: {tool_name}")


register_td_tools(config, td, mcp)


#------------------ Register tools, resources and prompts declared in .yml files ------------------#

custom_object_files = [file for file in os.listdir() if file.endswith("_objects.yaml")]

# Also include all .yml files under ./src/teradata_mcp_server/tools/*/*.yml
tool_yml_files = glob.glob(os.path.join(os.path.dirname(__file__), "tools", "*", "*.yml"))
custom_object_files.extend(tool_yml_files)

custom_objects = {}
custom_glossary = {}

for file in custom_object_files:
    with open(file) as f:
        loaded = yaml.safe_load(f)
        if loaded:
            custom_objects.update(loaded)  # Merge dictionaries


def make_custom_prompt(prompt_name: str, prompt: str, desc: str):
    async def _dynamic_prompt():
        # SQL is closed over without parameters
        return UserMessage(role="user", content=TextContent(type="text", text=prompt))
    _dynamic_prompt.__name__ = prompt_name
    return mcp.prompt(description=desc)(_dynamic_prompt)

def make_custom_query_tool(name, tool):
    param_defs = tool.get("parameters", {})
    # 1. Build Parameter objects
    parameters = []
    annotations = {}
    # param_defs is now a dict keyed by name
    for param_name, p in param_defs.items():
        type_hint = p.get("type_hint", str)    # e.g. int, float, str, etc.
        default = inspect.Parameter.empty if p.get("required", True) else p.get("default", None)
        parameters.append(
            inspect.Parameter(
                param_name,
                kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                default=default,
                annotation=type_hint
            )
        )
        annotations[param_name] = type_hint

    # 2. Create the new signature
    sig = inspect.Signature(parameters)

    # 3. Define your generic handler
    async def _dynamic_tool(**kwargs):
        """Dynamically generated tool for {name}"""
        missing = [n for n in annotations if n not in kwargs]
        if missing:
            raise ValueError(f"Missing parameters: {missing}")
        return execute_db_tool(td.handle_base_readQuery, tool["sql"], tool_name=name, **kwargs)

    # 4. Inject signature & annotations
    _dynamic_tool.__signature__   = sig
    _dynamic_tool.__annotations__ = annotations

    # 5. Register with FastMCP
    return mcp.tool(
        name=name,
        description=tool.get("description", "")
    )(_dynamic_tool)

def generate_cube_query_tool(name, cube):
    """
    Generate a function to create aggregation SQL from a cube definition.

    :param cube: The cube definition
    :return: A SQL query string generator function taking dimensions and measures as comma-separated strings.
    """
    def _cube_query_tool(dimensions: str, measures: str) -> str:
        """
        Generate a SQL query string for the cube using the specified dimensions and measures.

        Args:
            dimensions (str): Comma-separated dimension names (keys in cube['dimensions']).
            measures (str): Comma-separated measure names (keys in cube['measures']).

        Returns:
            str: The generated SQL query.
        """
        dim_list_raw = [d.strip() for d in dimensions.split(",") if d.strip()]
        met_list_raw = [m.strip() for m in measures.split(",") if m.strip()]
        # Get dimension expressions from dictionary
        dim_list = ",\n  ".join([
            cube["dimensions"][d]["expression"] if d in cube["dimensions"] else d
            for d in dim_list_raw
        ])
        met_lines = []
        for measure in met_list_raw:
            mdef = cube["measures"].get(measure)
            if mdef is None:
                raise ValueError(f"Measure '{measure}' not found in cube '{name}'.")
            expr = mdef["expression"]
            met_lines.append(f"{expr} AS {measure}")
        met_block = ",\n  ".join(met_lines)
        sql = (
            "SELECT\n"
            f"  {dim_list},\n"
            f"  {met_block}\n"
            "FROM (\n"
            f"{cube['sql'].strip()}\n"
            ") AS c\n"
            f"GROUP BY {', '.join(dim_list_raw)};"
        )
        return sql
    return _cube_query_tool

def make_custom_cube_tool(name, cube):
    async def _dynamic_tool(dimensions, measures):
        # Accept dimensions and measures as comma-separated strings, parse to lists
        return execute_db_tool(
            td.util_base_dynamicQuery,
            sql_generator=generate_cube_query_tool(name, cube),
            dimensions=dimensions,
            measures=measures
        )
    _dynamic_tool.__name__ = 'get_cube_' + name
    # Build allowed values and definitions for dimensions and measures
    dim_lines = []
    for name, d in cube.get('dimensions', {}).items():
        dim_lines.append(f"    - {name}: {d.get('description', '')}")
    measure_lines = []
    for name, m in cube.get('measures', {}).items():
        measure_lines.append(f"    - {name}: {m.get('description', '')}")
    _dynamic_tool.__doc__ = f"""
    Tool to query the cube '{name}'.
    {cube.get('description', '')}

    Expected inputs:
        dimensions (str): Comma-separated dimension names to group by. Allowed values:
{chr(10).join(dim_lines)}

        measures (str): Comma-separated measure names to aggregate (must match cube definition). Allowed values:
{chr(10).join(measure_lines)}

    Returns:
        Query result as a formatted response.
    """
    return mcp.tool(description=_dynamic_tool.__doc__)(_dynamic_tool)

# Instantiate custom query tools from YAML
custom_terms = []
for name, obj in custom_objects.items():
    obj_type = obj.get("type")
    if obj_type == "tool" and any(re.match(pattern, name) for pattern in config.get('tool',[])):
        fn = make_custom_query_tool(name, obj)
        globals()[name] = fn
        logger.info(f"Created tool: {name}")
    elif obj_type == "prompt"  and any(re.match(pattern, name) for pattern in config.get('prompt',[])):
        fn = make_custom_prompt(name, obj["prompt"], obj.get("description", ""))
        globals()[name] = fn
        logger.info(f"Created prompt: {name}")
    elif obj_type == "cube"  and any(re.match(pattern, name) for pattern in config.get('tool',[])):
        fn = make_custom_cube_tool(name, obj)
        globals()[name] = fn
        logger.info(f"Created cube: {name}")
    elif obj_type == "glossary"  and any(re.match(pattern, name) for pattern in config.get('resource',[])):
        # Remove the 'type' key to get just the terms
        custom_glossary = {k: v for k, v in obj.items() if k != "type"}
        logger.info(f"Added custom glossary entries for: {name}.")
    else:
        logger.info(f"Type {obj_type if obj_type else ''} for custom object {name} is {'unknown' if obj_type else 'undefined'}.")

    # Look for additional terms to add to the custom glossary (currently only measures and dimensions in cubes)
    for section in ("measures", "dimensions"):
        if section in obj and  any(re.match(pattern, name) for pattern in config.get('tool',[])):
            custom_terms.extend((term, details, name) for term, details in obj[section].items())

# Enrich glossary with terms from tools and cubes
for term, details, tool in custom_terms:
    term_key = term.strip()

    if term_key not in custom_glossary:
        # New glossary entry
        custom_glossary[term_key] = {
            "definition": details.get("description"),
            "synonyms": [],
            "tools": [tool]
        }
    else:
        # Existing glossary term → preserve definition, just add tool if missing
        if "tools" not in custom_glossary[term_key]:
            custom_glossary[term_key]["tools"] = []
        if tool not in custom_glossary[term_key]["tools"]:
            custom_glossary[term_key]["tools"].append(tool)

if custom_glossary:
    # Resource returning the entire glossary
    @mcp.resource("glossary://all")
    def get_glossary() -> ResponseType:
        """List all glossary terms."""
        return custom_glossary

    # Resource returning the entire glossary
    @mcp.resource("glossary://definitions")
    def get_glossary_definitions() -> ResponseType:
        """Returns all glossary terms with definitions."""
        return {term: details["definition"] for term, details in custom_glossary.items()}

    # Resource returning all information about a specific glossary term
    @mcp.resource("glossary://term/{term_name}")
    def get_glossary_term(term_name: str)  -> dict:
        """Return the definition, synonyms and associated tools of a specific glossary term."""
        term = custom_glossary.get(term_name)
        if term:
            return term
        else:
            return {"error": f"Glossary term not found: {term_name}"}



#------------------ Enterprise Vector Store Tools  ------------------#

# if config['evs']['allmodule']:
#     if config['evs']['tool']['evs_vectorStoreSimilaritySearch']:
#         @mcp.tool(description="Enterprise Vector Store similarity search")
#         async def evs_vectorStoreSimilaritySearch(
#             question: str = Field(description="Natural language question"),
#             top_k: int = Field(1, description="top matches to return"),
#         ) -> ResponseType:

#             return execute_vs_tool(
#                 td.evs_tools.handle_evs_vectorStoreSimilaritySearch,
#                 question=question,
#                 top_k=top_k,
#             )



#--------------- Feature Store Tools ---------------#
# Feature tools leveraging the tdfs4ds package.
# Run only if the EFS tools are defined in the config
if any(re.match(pattern, 'fs_*') for pattern in config.get('tool',[])):
    class FeatureStoreConfig(BaseModel):
        """
        Configuration class for the feature store. This model defines the metadata and catalog sources 
        used to organize and access features, processes, and datasets across data domains.
        """

        data_domain: Optional[str] = Field(
            default=None,
            description="The data domain associated with the feature store, grouping features within the same namespace."
        )

        entity: Optional[str] = Field(
            default=None,
            description="The list of entities, comma separated and in alphabetical order, upper case."
        )

        db_name: Optional[str] = Field(
            default=None,
            description="Name of the database where the feature store is hosted."
        )

        feature_catalog: Optional[str] = Field(
            default=None,
            description=(
                "Name of the feature catalog table. "
                "This table contains detailed metadata about features and entities."
            )
        )

        process_catalog: Optional[str] = Field(
            default=None,
            description=(
                "Name of the process catalog table. "
                "Used to retrieve information about feature generation processes, features, and associated entities."
            )
        )

        dataset_catalog: Optional[str] = Field(
            default=None,
            description=(
                "Name of the dataset catalog table. "
                "Used to list and manage available datasets within the feature store."
            )
        )

    fs_config = FeatureStoreConfig() 

    @mcp.tool(description="Reconnect to the Teradata database if the connection is lost.")
    async def reconnect_to_database() -> ResponseType:
        """Reconnect to Teradata database if connection is lost."""
        global _tdconn
        try:
            _tdconn = td.TDConn()
            td.teradataml_connection()
            return format_text_response("Reconnected to Teradata database successfully.")
        except Exception as e:
            logger.error(f"Error reconnecting to database: {e}")
            return format_error_response(str(e))

    @mcp.tool(description="Set or update the feature store configuration (database and data domain).")
    async def fs_setFeatureStoreConfig(
        data_domain: Optional[str] = None,
        db_name: Optional[str] = None,
        entity: Optional[str] = None,
    ) -> ResponseType:
        if db_name:
            if tdfs4ds.connect(database=db_name):
                logger.info(f"connected to the feature store of the {db_name} database")
                # Reset data_domain if DB name changes
                if not (fs_config.db_name and fs_config.db_name.upper() == db_name.upper()):
                    fs_config.data_domain = None
                
                fs_config.db_name = db_name
                logger.info(f"connected to the feature store of the {db_name} database")
                fs_config.feature_catalog = f"{db_name}.{tdfs4ds.FEATURE_CATALOG_NAME_VIEW}"
                logger.info(f"feature catalog {fs_config.feature_catalog}")
                fs_config.process_catalog = f"{db_name}.{tdfs4ds.PROCESS_CATALOG_NAME_VIEW}"
                logger.info(f"process catalog {fs_config.process_catalog}")
                fs_config.dataset_catalog = f"{db_name}.FS_V_FS_DATASET_CATALOG"  # <- fixed line
                logger.info(f"dataset catalog {fs_config.dataset_catalog}")

        if fs_config.db_name is not None and data_domain is not None:
            sql_query_ = f"SEL count(*) AS N FROM {fs_config.feature_catalog} WHERE UPPER(data_domain) = '{data_domain.upper()}'"
            logger.info(f"{sql_query_}")
            result = tdml.execute_sql(sql_query_)
            logger.info(f"{result}")
            if result.fetchall()[0][0] > 0:
                fs_config.data_domain = data_domain
            else:
                fs_config.data_domain = None

        if fs_config.db_name is not None and fs_config.data_domain is not None and entity is not None:
            sql_query_ = f"SEL count(*) AS N FROM {fs_config.feature_catalog} WHERE UPPER(data_domain) = '{data_domain.upper()}' AND ENTITY_NAME = '{entity.upper()}'"
            logger.info(f"{sql_query_}")
            result = tdml.execute_sql(sql_query_)
            logger.info(f"{result}")
            if result.fetchall()[0][0] > 0:
                fs_config.entity = entity
        return format_text_response(f"Feature store config updated: {fs_config.dict(exclude_none=True)}")

    @mcp.tool(description="Display the current feature store configuration (database and data domain).")
    async def fs_getFeatureStoreConfig() -> ResponseType:
        return format_text_response(f"Current feature store config: {fs_config.dict(exclude_none=True)}")

    @mcp.tool(description=("Check if a feature store is present in the specified database." ))
    async def fs_isFeatureStorePresent(
        db_name: str = Field(..., description="Name of the database to check for a feature store.")
    ) -> ResponseType:
        return execute_db_tool(td.handle_fs_isFeatureStorePresent, db_name=db_name)

    @mcp.tool(description=("Returns a summary of the feature store content. Use this to understand what data is available in the feature store"))
    async def fs_featureStoreContent(
    ) -> ResponseType:
        return execute_db_tool(td.handle_fs_featureStoreContent, fs_config=fs_config)

    @mcp.tool(description=( "List the available data domains. Requires a configured `db_name`  in the feature store config. Use this to explore which entities can be used when building a dataset."))
    async def fs_getDataDomains(
        entity: str = Field(..., description="The .")
    ) -> ResponseType:
        return execute_db_tool(td.handle_fs_getDataDomains, fs_config=fs_config)

    @mcp.tool(description=("List the list of features. Requires a configured `db_name` and  `data_domain` in the feature store config. Use this to explore the features available ."))
    async def fs_getFeatures(
    ) -> ResponseType:
        return execute_db_tool(td.handle_fs_getFeatures, fs_config=fs_config)

    @mcp.tool(description=("List the list of available datasets.Requires a configured `db_name` in the feature store config.Use this to explore the datasets that are available ."))
    async def fs_getAvailableDatasets(
    ) -> ResponseType:
        return execute_db_tool(td.handle_fs_getAvailableDatasets, fs_config=fs_config)

    @mcp.tool(description=("Return the schema of the feature store.Requires a feature store in the configured database (`db_name`)."))
    async def fs_getFeatureDataModel(
    ) -> ResponseType:
        return execute_db_tool(td.handle_fs_getFeatureDataModel, fs_config=fs_config)


    @mcp.tool(description=("List the available entities for a given data domain. Requires a configured `db_name` and `data_domain` and  `entity` in the feature store config. Use this to explore which entities can be used when building a dataset."))
    async def fs_getAvailableEntities(
    ) -> ResponseType:
        return execute_db_tool(td.handle_fs_getAvailableEntities, fs_config=fs_config)

    @mcp.tool( description=("Create a dataset using selected features and an entity from the feature store. The dataset is created in the specified target database under the given name. Requires a configured feature store and data domain. Registers the dataset in the catalog automatically. Use this when you want to build and register a new dataset for analysis or modeling." ) )
    async def fs_createDataset(
        entity_name: str = Field(..., description="Entity for which the dataset will be created. Available entities are reported in the feature catalog."),
        feature_selection: list[str] = Field(..., description="List of features to include in the dataset. Available features are reported in the feature catalog."),
        dataset_name: str = Field(..., description="Name of the dataset to create."),
        target_database: str = Field(..., description="Target database where the dataset will be created.")
    ) -> ResponseType:
        return execute_db_tool(td.handle_fs_createDataset, fs_config=fs_config, entity_name=entity_name, feature_selection=feature_selection, dataset_name=dataset_name, target_database=target_database)

#------------------ Main ------------------#
# Main function to start the MCP server
#     Description: Initializes the MCP server and sets up signal handling for graceful shutdown.
#         It creates a connection to the Teradata database and starts the server to listen for incoming requests.
#         The function uses asyncio to manage asynchronous operations and handle signals for shutdown.
#         If an error occurs during initialization, it logs a warning message.
async def main():
    global _tdconn
    
    mcp_transport = os.getenv("MCP_TRANSPORT", "stdio").lower()
    logger.info(f"MCP_TRANSPORT: {mcp_transport}")

    # Set up proper shutdown handling
    try:
        loop = asyncio.get_running_loop()
        signals = (signal.SIGTERM, signal.SIGINT)
        for s in signals:
            logger.info(f"Registering signal handler for {s.name}")
            loop.add_signal_handler(s, lambda s=s: asyncio.create_task(shutdown(s)))
    except NotImplementedError:
        # Windows doesn't support signals properly
        logger.warning("Signal handling not supported on Windows")
        pass
    
    # Start the MCP server
    if mcp_transport == "sse":
        mcp.settings.host = os.getenv("MCP_HOST")
        mcp.settings.port = int(os.getenv("MCP_PORT"))
        logger.info(f"Starting MCP server on {mcp.settings.host}:{mcp.settings.port}")
        await mcp.run_sse_async()
    elif mcp_transport == "streamable-http":
        mcp.settings.host = os.getenv("MCP_HOST")
        mcp.settings.port = int(os.getenv("MCP_PORT"))
        mcp.settings.streamable_http_path = os.getenv("MCP_PATH", "/mcp/")
        logger.info(f"Starting MCP server on {mcp.settings.host}:{mcp.settings.port} with path {mcp.settings.streamable_http_path}")
        await mcp.run_streamable_http_async()
    else:
        logger.info("Starting MCP server on stdin/stdout")
        await mcp.run_stdio_async()    

#------------------ Shutdown ------------------#
# Shutdown function to handle cleanup and exit
#     Arguments: sig (signal.Signals) - signal received for shutdown
#     Description: Cleans up resources and exits the server gracefully.
#         It sets a flag to indicate that shutdown is in progress and logs the received signal.
#         If the shutdown is already in progress, it forces an immediate exit.
#         The function uses os._exit to terminate the process with a specific exit code.
async def shutdown(sig=None):
    """Clean shutdown of the server."""
    global shutdown_in_progress, _tdconn
    
    logger.info("Shutting down server")
    if shutdown_in_progress:
        logger.info("Forcing immediate exit")
        os._exit(1)  # Use immediate process termination instead of sys.exit
    
    _tdconn.close()
    shutdown_in_progress = True
    if sig:
        logger.info(f"Received exit signal {sig.name}")
    os._exit(128 + sig if sig is not None else 0)


#------------------ Entry Point ------------------#
# Entry point for the script
#     Description: This script is designed to be run as a standalone program.
#         It loads environment variables, initializes logging, and starts the MCP server.
#         The main function is called to start the server and handle incoming requests.
#         If an error occurs during execution, it logs the error and exits with a non-zero status code.
if __name__ == "__main__":
    asyncio.run(main())