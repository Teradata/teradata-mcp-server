from __future__ import annotations

"""Application factory for the Teradata MCP server.

High-level architecture:
- server.py is a thin entrypoint that parses CLI/env into a Settings object and
  calls create_mcp_app(settings), then runs the chosen transport.
- create_mcp_app builds a FastMCP instance, configures logging, adds middleware
  to capture per-request context (including stdio fast-path), sets up Teradata
  connections (and optional teradataml Feature Store), and registers tools,
  prompts and resources from both Python modules and YAML files.
- Tool handlers are plain Python functions named handle_<toolName> living under
  src/teradata_mcp_server/tools/*. They remain protocol-agnostic. At startup,
  we auto-wrap them with a small adapter so they appear as MCP tools with clean
  signatures. The adapter injects a DB connection and sets QueryBand from the
  request context when using HTTP.
"""
import asyncio
import inspect
import os
import re
import sys
from importlib.resources import files as pkg_files
from typing import Annotated, Any

import yaml
from fastmcp import FastMCP
from fastmcp.prompts.prompt import TextContent, Message
from pydantic import Field, BaseModel

from teradata_mcp_server.config import Settings
from teradata_mcp_server import utils as config_utils
from teradata_mcp_server.utils import setup_logging, format_text_response, format_error_response, resolve_type_hint
from teradata_mcp_server.middleware import RequestContextMiddleware
from teradata_mcp_server.tools.utils.queryband import build_queryband
from sqlalchemy.engine import Connection
from fastmcp.server.dependencies import get_context
from teradata_mcp_server.tools.utils import (get_dynamic_function_definition,
                                             get_anlytic_function_signature,
                                             convert_tdml_docstring_to_mcp_docstring,
                                             execute_analytic_function,
                                             get_partition_col_order_col_doc_string)
import json


def create_mcp_app(settings: Settings):
    """Create and configure the FastMCP app with middleware, tools, prompts, resources."""
    logger = setup_logging(settings.logging_level, settings.mcp_transport)

    # Load tool module loader via teradata tools package
    try:
        from teradata_mcp_server import tools as td
    except ImportError:
        import tools as td  # dev fallback

    mcp = FastMCP("teradata-mcp-server")

    # Profiles (load via utils to honor packaged + working-dir overrides)
    profile_name = settings.profile
    if not profile_name:
        logger.info("No profile specified, load all tools, prompts and resources.")
    config = config_utils.get_profile_config(profile_name)

    # Feature flags from profiles
    enableEFS = True if any(re.match(pattern, 'fs_*') for pattern in config.get('tool', [])) else False
    enableTDVS = True if any(re.match(pattern, 'tdvs_*') for pattern in config.get('tool', [])) else False
    enableBAR = True if any(re.match(pattern, 'bar_*') for pattern in config.get('tool', [])) else False
    enableQG = True if any(re.match(pattern, 'qg_*') for pattern in config.get('tool', [])) else False

    # Initialize TD connection and optional teradataml/EFS context
    # Pass settings object to TDConn instead of just connection_url
    tdconn = td.TDConn(settings=settings)

    enable_analytic_functions = profile_name and profile_name == 'dataScientist'

    fs_config = None
    if enableEFS or enable_analytic_functions:

        try:
            import teradataml as tdml
            tdml.create_context(tdsqlengine=tdconn.engine)
        except (AttributeError, ImportError, ModuleNotFoundError) as e:
            logger.warning(f"teradataml not installed - disabling analytic functions: {e}")
            enable_analytic_functions = False
        except Exception as e:
            logger.warning(f"Error creating teradataml context - disabling analytic functions: {e}")
            enable_analytic_functions = False

        # Only import FeatureStoreConfig (which depends on tdfs4ds) when EFS tools are enabled
        try:
            from teradata_mcp_server.tools.fs.fs_utils import FeatureStoreConfig
            fs_config = FeatureStoreConfig()
            # teradataml is optional; warn if unavailable but keep EFS enabled
            try:
                import teradataml as tdml
            except (AttributeError, ImportError, ModuleNotFoundError):
                logger.warning("teradataml not installed; EFS tools will operate without a teradataml context")
        except (AttributeError, ImportError, ModuleNotFoundError) as e:
            logger.warning(f"Feature Store module not available - disabling EFS functionality: {e}")
            enableEFS = False

            
    # TeradataVectorStore connection (optional)
    tdvs = None
    if len(os.getenv("TD_BASE_URL", "").strip()) > 0:
        try:
            from teradata_mcp_server.tools.tdvs.tdvs_utilies import create_teradataml_context
            create_teradataml_context()
            enableTDVS = True
        except Exception as e:
            logger.error(f"Unable to establish connection to Teradata Vector Store, disabling: {e}")
            enableTDVS = False

    # BAR (Backup and Restore) system dependencies (optional)
    if enableBAR:
        try:
            # Check for BAR system availability by importing required modules
            import requests
            from teradata_mcp_server.tools.bar.dsa_client import DSAClient
            # Verify DSA connection if environment variables are set
            dsa_base_url = os.getenv("DSA_BASE_URL")
            dsa_host = os.getenv("DSA_HOST")
            dsa_port = os.getenv("DSA_PORT")
            if dsa_base_url or (dsa_host and dsa_port):
                logger.info("BAR system configured with DSA connection")
            else:
                logger.warning("BAR tools enabled but DSA connection not configured (missing DSA_BASE_URL or DSA_HOST/DSA_PORT) - disabling BAR functionality")
                enableBAR = False
        except (AttributeError, ImportError, ModuleNotFoundError) as e:
            logger.warning(f"BAR system dependencies not available - disabling BAR functionality: {e}")
            enableBAR = False

    # QueryGrid dependencies (optional)
    qg_manager = None
    if enableQG:
        try:
            # Check for QG system availability by importing required modules
            import requests
            from teradata_mcp_server.tools.qg.qgm.querygrid_manager import QueryGridManager
            qg_manager = QueryGridManager()
        except (AttributeError, ImportError, ModuleNotFoundError) as e:
            logger.warning(f"QG system dependencies not available - disabling QG functionality: {e}")
            enableQG = False

    # Middleware (auth + request context)
    from teradata_mcp_server.tools.auth_cache import SecureAuthCache
    auth_cache = SecureAuthCache(ttl_seconds=settings.auth_cache_ttl)

    def get_tdconn(recreate: bool = False):
        nonlocal tdconn, fs_config
        if recreate:
            tdconn = td.TDConn(settings=settings)
            if enableEFS:
                try:
                    import teradataml as tdml
                    fs_config = td.FeatureStoreConfig()
                    try:
                        tdml.create_context(tdsqlengine=tdconn.engine)
                    except Exception:
                        pass
                except Exception:
                    pass
        return tdconn

    middleware = RequestContextMiddleware(
        logger=logger,
        auth_cache=auth_cache,
        tdconn_supplier=get_tdconn,
        auth_mode=settings.auth_mode,
        transport=settings.mcp_transport,
    )
    mcp.add_middleware(middleware)

    # Adapters (inlined for simplicity)
    import socket
    hostname = socket.gethostname()
    process_id = f"{hostname}:{os.getpid()}"

    def execute_db_tool(tool, *args, **kwargs):
        """Execute a handler with a DB connection and MCP concerns.

        - Detects whether the handler expects a SQLAlchemy Connection or a raw
          DB-API connection and injects appropriately.
        - For HTTP transport, builds and sets Teradata QueryBand per request using
          the RequestContext captured by middleware.
        - Formats return values into FastMCP content and captures exceptions with
          context for easier debugging.
        """
        tool_name = kwargs.pop('tool_name', getattr(tool, '__name__', 'unknown_tool'))
        tdconn_local = get_tdconn()

        if not getattr(tdconn_local, "engine", None):
            logger.info("Reinitializing TDConn")
            tdconn_local = get_tdconn(recreate=True)

        sig = inspect.signature(tool)
        first_param = next(iter(sig.parameters.values()))
        ann = first_param.annotation
        use_sqla = inspect.isclass(ann) and issubclass(ann, Connection)

        try:
            if use_sqla:
                from sqlalchemy import text
                with tdconn_local.engine.connect() as conn:
                    # Always attempt to set QueryBand when a request context is present
                    ctx = get_context()
                    request_context = ctx.get_state("request_context") if ctx else None
                    if request_context is not None:
                        qb = build_queryband(
                            application=mcp.name,
                            profile=profile_name,
                            process_id=process_id,
                            tool_name=tool_name,
                            request_context=request_context,
                        )
                        try:
                            conn.execute(text(f"SET QUERY_BAND = '{qb}' FOR SESSION"))
                            logger.debug(f"QueryBand set: {qb}")
                            logger.debug(f"Tool request context: {request_context}")
                        except Exception as qb_error:
                            logger.debug(f"Could not set QueryBand: {qb_error}")
                            # If in Basic auth, do not run the tool without proxying
                            if str(getattr(request_context, "auth_scheme", "")).lower() == "basic":
                                return format_error_response(
                                    f"Cannot run tool '{tool_name}': failed to set QueryBand for Basic auth. Error: {qb_error}"
                                )
                    result = tool(conn, *args, **kwargs)
            else:
                raw = tdconn_local.engine.raw_connection()
                try:
                    # Always attempt to set QueryBand when a request context is present
                    ctx = get_context()
                    request_context = ctx.get_state("request_context") if ctx else None
                    if request_context is not None:
                        qb = build_queryband(
                            application=mcp.name,
                            profile=profile_name,
                            process_id=process_id,
                            tool_name=tool_name,
                            request_context=request_context,
                        )
                        try:
                            cursor = raw.cursor()
                            # Apply at session scope so it persists across statements
                            cursor.execute(f"SET QUERY_BAND = '{qb}' FOR SESSION")
                            cursor.close()
                            logger.debug(f"QueryBand set: {qb}")
                            logger.debug(f"Tool request context: {request_context}")
                        except Exception as qb_error:
                            logger.debug(f"Could not set QueryBand: {qb_error}")
                            if str(getattr(request_context, "auth_scheme", "")).lower() == "basic":
                                return format_error_response(
                                    f"Cannot run tool '{tool_name}': failed to set QueryBand for Basic auth. Error: {qb_error}"
                                )
                    result = tool(raw, *args, **kwargs)
                finally:
                    raw.close()
            return format_text_response(result)
        except Exception as e:
            logger.error(f"Error in execute_db_tool: {e}", exc_info=True, extra={"session_info": {"tool_name": tool_name}})
            return format_error_response(str(e))

    def create_mcp_tool(
        *,
        executor_func=None,
        signature,
        inject_kwargs=None,
        validate_required=False,
        tool_name="mcp_tool",
        tool_description=None,
    ):
        """
        Unified factory for creating async MCP tool functions.

        All tool functions use asyncio.to_thread to execute blocking database operations.

        Args:
            executor_func: Callable that will be executed. Should be a function that
                          calls execute_db_tool with appropriate arguments.
            signature: The inspect.Signature for the MCP tool function.
            inject_kwargs: Dict of kwargs to inject when calling executor_func.
            validate_required: Whether to validate required parameters are present.
            tool_name: Name to assign to the MCP tool function.
            tool_description: Description/docstring for the MCP tool function.

        Returns:
            An async function suitable for use as an MCP tool.
        """
        inject_kwargs = inject_kwargs or {}

        # Extract annotations from signature parameters
        annotations = {
            name: param.annotation
            for name, param in signature.parameters.items()
            if param.annotation is not inspect.Parameter.empty
        }

        if validate_required:
            # Build list of required parameter names (those without defaults)
            required_params = [
                name for name, param in signature.parameters.items()
                if param.default is inspect.Parameter.empty
            ]

            async def _mcp_tool(**kwargs):
                missing = [n for n in required_params if n not in kwargs]
                if missing:
                    raise ValueError(f"Missing required parameters: {missing}")
                merged_kwargs = {**inject_kwargs, **kwargs}
                return await asyncio.to_thread(executor_func, **merged_kwargs)
        else:
            async def _mcp_tool(**kwargs):
                merged_kwargs = {**inject_kwargs, **kwargs}
                return await asyncio.to_thread(executor_func, **merged_kwargs)

        _mcp_tool.__name__ = tool_name
        _mcp_tool.__signature__ = signature
        _mcp_tool.__doc__ = tool_description
        _mcp_tool.__annotations__ = annotations

        return _mcp_tool

    def make_tool_wrapper(func):
        """Create an MCP-facing wrapper for a handle_* function.

        - Removes internal parameters (conn, tool_name, fs_config) from the MCP
          signature while still injecting them into the underlying handler.
        - Preserves the handler's parameter names and types so MCP clients can
          render friendly forms.
        """
        sig = inspect.signature(func)
        inject_kwargs = {}
        removable = {"conn", "tool_name"}
        if "fs_config" in sig.parameters:
            inject_kwargs["fs_config"] = fs_config
            removable.add("fs_config")

        if "qg_manager" in sig.parameters:
            inject_kwargs["qg_manager"] = qg_manager
            removable.add("qg_manager")

        params = [
            p for name, p in sig.parameters.items()
            if name not in removable and p.kind in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)
        ]
        new_sig = sig.replace(parameters=params)

        # Create executor function that will be run in thread
        def executor(**kwargs):
            return execute_db_tool(func, **kwargs)

        return create_mcp_tool(
            executor_func=executor,
            signature=new_sig,
            inject_kwargs=inject_kwargs,
            validate_required=False,
            tool_name=getattr(func, "__name__", "wrapped_tool"),
            tool_description=func.__doc__,
        )

    # Register code tools via module loader
    module_loader = td.initialize_module_loader(config)
    if module_loader:
        all_functions = module_loader.get_all_functions()
        for name, func in all_functions.items():
            if not (inspect.isfunction(func) and name.startswith("handle_")):
                continue
            tool_name = name[len("handle_"):]
            if not any(re.match(p, tool_name) for p in config.get('tool', [])):
                continue
            # Skip template tools (used for developer reference only)
            if tool_name.startswith("tmpl_"):
                logger.debug(f"Skipping template tool: {tool_name}")
                continue
            # Skip BAR tools if BAR functionality is disabled
            if tool_name.startswith("bar_") and not enableBAR:
                logger.info(f"Skipping BAR tool: {tool_name} (BAR functionality disabled)")
                continue
            # Skip QueryGrid tools if the functionality is disabled
            if tool_name.startswith("qg_") and not enableQG:
                logger.info(f"Skipping QueryGrid tool: {tool_name} (functionality disabled)")
                continue
            wrapped = make_tool_wrapper(func)
            mcp.tool(name=tool_name, description=wrapped.__doc__)(wrapped)
            logger.info(f"Created tool: {tool_name}")
            logger.debug(f"Tool Docstring: {wrapped.__doc__}")
    else:
        logger.warning("No module loader available, skipping code-defined tool registration")

    from teradata_mcp_server.tools.constants import TD_ANALYTIC_FUNCS as funcs
    if enable_analytic_functions:

        tdml_processed_funcs = set(tdml.analytics.json_parser.json_store._JsonStore._get_function_list()[0].keys())

        for func_name in funcs:

            # Before adding the function, check if function is existed or not.
            # Connection is not mandatory for MCP server. If connection is not there, then
            # functions can not be added.
            if func_name not in tdml_processed_funcs:
                logger.warning("Function {} is not available. Hence not adding it. ".format(func_name))
                continue

            func_metadata = tdml.analytics.json_parser.json_store._JsonStore.get_function_metadata(func_name)
            func_obj = getattr(tdml, func_name, None)
            func_params = func_metadata.function_params

            inp_data = [t.get_lang_name() for t in func_metadata.input_tables]
            # Add partition_by parameters for func parameters.
            additional_args_docs = []
            for table in inp_data:
                func_params["{}_partition_column".format(table)] = None
                func_params["{}_order_column".format(table)] = None
                additional_args_docs.append(get_partition_col_order_col_doc_string(table))

            # Generate function argument string.
            func_args_str = get_anlytic_function_signature(func_params)

            func_name = "tdml_" + func_name
            func_str = get_dynamic_function_definition().format(
                analytic_function=func_name,
                doc_string=func_obj.__init__.__doc__,
                func_args_str=func_args_str,
                tables_to_df=json.dumps(inp_data)
            )

            doc_string = convert_tdml_docstring_to_mcp_docstring(
                func_obj.__init__.__doc__, additional_args_docs)

            # Execute the generated function definition in the global scope.
            # Global scope will have all other functions. So reference to other functions will work.
            exec(func_str, globals())

            # Register the function as a tool in MCP server.
            func = globals()[func_name]

            mcp.tool(name=func_name, description=doc_string)(func)

    # Load YAML-defined tools/resources/prompts
    custom_object_files = [file for file in os.listdir() if file.endswith("_objects.yml")]
    if module_loader and profile_name:
        profile_yml_files = module_loader.get_required_yaml_paths()
        custom_object_files.extend(profile_yml_files)
        logger.info(f"Loading YAML files for profile '{profile_name}': {len(profile_yml_files)} files")
    else:
        tool_yml_resources = []
        tools_pkg_root = pkg_files("teradata_mcp_server").joinpath("tools")
        if tools_pkg_root.is_dir():
            for subpkg in tools_pkg_root.iterdir():
                if subpkg.is_dir():
                    for entry in subpkg.iterdir():
                        if entry.is_file() and entry.name.endswith('.yml'):
                            tool_yml_resources.append(entry)
        custom_object_files.extend(tool_yml_resources)
        logger.info(f"Loading all YAML files (no specific profile): {len(tool_yml_resources)} files")

    custom_objects: dict[str, Any] = {}
    custom_glossary: dict[str, Any] = {}
    for file in custom_object_files:
        try:
            if hasattr(file, "read_text"):
                text = file.read_text(encoding='utf-8')
            else:
                with open(file, encoding='utf-8', errors='replace') as f:
                    text = f.read()
            loaded = yaml.safe_load(text)
            if loaded:
                custom_objects.update(loaded)
        except Exception as e:
            logger.error(f"Failed to load YAML from {file}: {e}")

    # Prompt helpers
    def make_custom_prompt(prompt_name: str, prompt: str, desc: str, parameters: dict | None = None):
        if parameters is None or len(parameters) == 0:
            async def _dynamic_prompt():
                return Message(role="user", content=TextContent(type="text", text=prompt))
            _dynamic_prompt.__name__ = prompt_name
            return mcp.prompt(description=desc)(_dynamic_prompt)
        else:
            param_objects: list[inspect.Parameter] = []
            annotations: dict[str, Any] = {}
            for param_name, meta in parameters.items():
                meta = meta or {}
                type_hint_raw = meta.get("type_hint", "str")
                type_hint = resolve_type_hint(type_hint_raw)
                required = meta.get("required", True)
                desc_txt = meta.get("description", "")
                # Get the type name for display
                type_name = type_hint.__name__ if hasattr(type_hint, '__name__') else str(type_hint_raw)
                desc_txt += f" (type: {type_name})"
                if required and "default" not in meta:
                    default_value = Field(..., description=desc_txt)
                else:
                    default_value = Field(default=meta.get("default", None), description=desc_txt)
                param_objects.append(
                    inspect.Parameter(
                        param_name,
                        kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                        default=default_value,
                        annotation=type_hint,
                    )
                )
                annotations[param_name] = type_hint
            sig = inspect.Signature(param_objects)
            async def _dynamic_prompt(**kwargs):
                missing = [name for name, meta in parameters.items() if (meta or {}).get("required", True) and name not in kwargs]
                if missing:
                    raise ValueError(f"Missing parameters: {missing}")
                formatted_prompt = prompt.format(**kwargs)
                return Message(role="user", content=TextContent(type="text", text=formatted_prompt))
            _dynamic_prompt.__signature__ = sig
            _dynamic_prompt.__annotations__ = annotations
            _dynamic_prompt.__name__ = prompt_name
            return mcp.prompt(description=desc)(_dynamic_prompt)

    def make_custom_query_tool(name, tool):
        description = tool.get("description", "")
        param_defs = tool.get("parameters", {})
        parameters = []
        if param_defs:
            description += "\nArguments:"
        for param_name, p in param_defs.items():
            param_description = p.get("description", "")
            type_hint_raw = p.get("type_hint", "str")
            type_hint = resolve_type_hint(type_hint_raw)  # Convert type string to actual type class
            annotation = Annotated[type_hint, param_description] if param_description else type_hint
            default = p.get("default", inspect.Parameter.empty)  # inspect.Parameter.empty if p.get("required", True) else p.get("default", None)

            parameters.append(
                inspect.Parameter(param_name, kind=inspect.Parameter.POSITIONAL_OR_KEYWORD, default=default, annotation=annotation)
            )

            # Append parameter name and description to function description
            # Disabled as already included in Annotations (consider introducing a way to toggle this if clients can't see annotations)
            if False:
                type_name = type_hint.__name__ if hasattr(type_hint, '__name__') else str(type_hint_raw)
                description += f"\n    * {param_name}"
                description += f": {param_description}" if param_description else ""
                description += f" (type: {type_name})"
        sig = inspect.Signature(parameters)

        # Create executor function that will be run in thread
        def executor(**kwargs):
            return execute_db_tool(td.handle_base_readQuery, tool["sql"], tool_name=name, **kwargs)

        tool_func = create_mcp_tool(
            executor_func=executor,
            signature=sig,
            validate_required=True,
            tool_name=name,
        )
        return mcp.tool(name=name, description=description)(tool_func)

    """
    Generate a SQL generation function that returns a query string for a given cube definition and tool parameters (grain, measures, filters...).
    """
    def generate_cube_query_tool(name, cube):
        """
        Generate a function to create aggregation SQL from a cube definition.

        :param cube: The cube definition
        :return: A SQL query string generator function taking dimensions and measures as comma-separated strings.
        """
        def _cube_query_tool(dimensions: str, measures: str, dim_filters: str, meas_filters: str, order_by: str, top: int) -> str:
            """
            Generate a SQL query string for the cube using the specified dimensions and measures.

            Args:
                dimensions (str): Comma-separated dimension names (keys in cube['dimensions']).
                measures (str): Comma-separated measure names (keys in cube['measures']).
                dim_filters (str): Filter SQL expressions on dimensions.
                meas_filters (str): Filter SQL expressions on computed measures.
                order_by (str): Order SQL expressions on selected dimensions and measures.
                top (int): Filters the top N results.

            Returns:
                str: The generated SQL query.
            """
            dim_list_raw = [d.strip() for d in dimensions.split(",") if d.strip()]
            mes_list_raw = [m.strip() for m in measures.split(",") if m.strip()]
            # Get dimension expressions from dictionary
            dim_list = ",\n  ".join([
                cube["dimensions"][d]["expression"] if d in cube["dimensions"] else d
                for d in dim_list_raw
            ])
            mes_lines = []
            for measure in mes_list_raw:
                mdef = cube["measures"].get(measure)
                if mdef is None:
                    raise ValueError(f"Measure '{measure}' not found in cube '{name}'.")
                expr = mdef["expression"]
                mes_lines.append(f"{expr} AS {measure}")
            meas_list = ",\n  ".join(mes_lines)
            top_clause = f"TOP {top}" if top else ""
            dim_comma = ",\n  " if dim_list.strip() else ""
            where_dim_clause = f"WHERE {dim_filters}" if dim_filters else ""
            where_meas_clause = f"WHERE {meas_filters}" if meas_filters else ""
            order_clause = f"ORDER BY {order_by}" if order_by else ""
            
            sql = (
                f"SELECT {top_clause} * from\n"
                "(SELECT\n"
                f"  {dim_list}{dim_comma}"
                f"  {meas_list}\n"
                "FROM (\n"
                f"sel * from ({cube['sql'].strip()}) a \n"
                f"{where_dim_clause}"
                ") AS c\n"
                f"GROUP BY {', '.join(dim_list_raw)}"
                ") AS a\n"
                f"{where_meas_clause}"
                f"{order_clause}"
                ";"            
            )
            return sql
        return _cube_query_tool

    def make_custom_cube_tool(name, cube):
        # Build allowed values and examples FIRST so we can use them in annotations
        dimensions_dict = cube.get('dimensions', {})
        measures_dict = cube.get('measures', {})

        # Build dimension list with descriptions
        dim_list = [f"{n}: {d.get('description', '')}" for n, d in dimensions_dict.items()]
        dim_names = list(dimensions_dict.keys())
        dimensions_desc = f"Comma-separated dimension names to group by. Allowed: {', '.join(dim_names)}"

        # Build measure list with descriptions
        meas_list = [f"{n}: {m.get('description', '')}" for n, m in measures_dict.items()]
        meas_names = list(measures_dict.keys())
        measures_desc = f"Comma-separated measure names to aggregate. Allowed: {', '.join(meas_names)}"

        # Build filter examples
        dim_examples = [f"{d} {e}" for d, e in zip(dim_names[:2], ["= 'value'", "in ('X', 'Y', 'Z')"])] if dim_names else []
        dim_example = ' AND '.join(dim_examples) if dim_examples else "dimension_name = 'value'"
        dim_filters_desc = f"Filter expression to apply to dimensions. Valid dimension names: [{', '.join(dim_names)}]. Example: {dim_example}"

        meas_examples = [f"{m} {e}" for m, e in zip(meas_names[:2], ["> 1000", "= 100"])] if meas_names else []
        meas_example = ' AND '.join(meas_examples) if meas_examples else "measure_name > 1000"
        meas_filters_desc = f"Filter expression to apply to computed measures. Valid measure names: [{', '.join(meas_names)}]. Example: {meas_example}"

        # Build order example
        order_examples = [f"{d} {e}" for d, e in zip(dim_names[:2], ["ASC", "DESC"])] if dim_names else []
        order_example = ', '.join(order_examples) if order_examples else "dimension_name ASC"
        order_by_desc = f"Order expression on dimensions and measures. Example: {order_example}"

        # Now build custom parameters
        param_defs = cube.get("parameters", {})
        parameters = []
        required_custom_params = []
        for param_name, p in param_defs.items():
            param_description = p.get("description", "")
            type_hint_raw = p.get("type_hint", "str")
            type_hint = resolve_type_hint(type_hint_raw)  # Convert to actual type class
            annotation = Annotated[type_hint, param_description] if param_description else type_hint
            default = p.get("default", inspect.Parameter.empty)
            parameters.append(
                inspect.Parameter(param_name, kind=inspect.Parameter.POSITIONAL_OR_KEYWORD, default=default, annotation=annotation)
            )
            # Track required custom params for validation
            if default is inspect.Parameter.empty:
                required_custom_params.append(param_name)

        # Build the combined signature: fixed cube parameters + custom parameters
        # Fixed cube parameters with detailed annotated descriptions
        cube_params = [
            inspect.Parameter("dimensions", kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                            annotation=Annotated[str, dimensions_desc]),
            inspect.Parameter("measures", kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                            annotation=Annotated[str, measures_desc]),
            inspect.Parameter("dim_filters", kind=inspect.Parameter.POSITIONAL_OR_KEYWORD, default="",
                            annotation=Annotated[str, dim_filters_desc]),
            inspect.Parameter("meas_filters", kind=inspect.Parameter.POSITIONAL_OR_KEYWORD, default="",
                            annotation=Annotated[str, meas_filters_desc]),
            inspect.Parameter("order_by", kind=inspect.Parameter.POSITIONAL_OR_KEYWORD, default="",
                            annotation=Annotated[str, order_by_desc]),
            inspect.Parameter("top", kind=inspect.Parameter.POSITIONAL_OR_KEYWORD, default=None,
                            annotation=Annotated[int, "Limit the number of rows returned (positive integer)"]),
        ]

        # Separate required and optional custom parameters
        all_params = cube_params + parameters
        required_params = [p for p in all_params if p.default is inspect.Parameter.empty]
        optional_params = [p for p in all_params if p.default is not inspect.Parameter.empty]

        # Combine: required first, then optional (Python requirement)
        sig = inspect.Signature(required_params + optional_params)

        # Debug: log the signature parameters
        logger.debug(f"Cube tool '{name}' signature parameters: {list(sig.parameters.keys())}")
        for param_name, param in sig.parameters.items():
            logger.debug(f"  {param_name}: annotation={param.annotation}, default={param.default}")

        # Create executor function that will be run in thread
        def executor(dimensions, measures, dim_filters="", meas_filters="", order_by="", top=None, **kwargs):
            # Validate custom parameters
            missing = [n for n in required_custom_params if n not in kwargs]
            if missing:
                raise ValueError(f"Missing required parameters: {missing}")

            sql_generator = generate_cube_query_tool(name, cube)
            return execute_db_tool(
                td.handle_base_readQuery,
                sql=sql_generator(
                    dimensions=dimensions,
                    measures=measures,
                    dim_filters=dim_filters,
                    meas_filters=meas_filters,
                    order_by=order_by,
                    top=top
                ),
                tool_name=name,
                **kwargs
            )

        # Build detailed dimension and measure lists for docstring
        dim_lines = [f"\t\t- {item}" for item in dim_list]
        measure_lines = [f"\t\t- {item}" for item in meas_list]

        # Build custom parameters documentation
        custom_param_lines = []
        for param_name, p in param_defs.items():
            param_desc = p.get('description', '')
            type_hint_raw = p.get('type_hint', 'str')
            type_hint = resolve_type_hint(type_hint_raw)
            param_type = type_hint.__name__ if hasattr(type_hint, '__name__') else str(type_hint_raw)
            is_required = p.get('default', inspect.Parameter.empty) is inspect.Parameter.empty
            required_text = " (required)" if is_required else " (optional)"
            custom_param_lines.append(f"    * {param_name} ({param_type}){required_text}: {param_desc}")

        # Build custom parameters section if there are any
        custom_params_section = ""
        if custom_param_lines:
            custom_params_section = "\n" + chr(10).join(custom_param_lines) + "\n"

        doc_string = f"""
{cube.get('description', '')}
This is an OLAP cube tool that presents selected measures at a specified level of aggregation and filtering.

Expected inputs:
    * dimensions (str): {dimensions_desc}
{chr(10).join(dim_lines)}

    * measures (str): {measures_desc}
{chr(10).join(measure_lines)}

    * dim_filters (str): {dim_filters_desc}
    * meas_filters (str): {meas_filters_desc}
    * order_by (str): {order_by_desc}
    * top (int): Limit the number of rows returned (positive integer)
{custom_params_section}
Returns:
    Query result as a formatted response.
        """

        tool_func = create_mcp_tool(
            executor_func=executor,
            signature=sig,
            validate_required=False,  # Validation happens inside executor for custom params
            tool_name='get_cube_' + name,
            tool_description=doc_string,
        )
        return mcp.tool(name=name, description=doc_string)(tool_func)

    # Register custom objects
    custom_terms: list[tuple[str, Any, str]] = []
    for name, obj in custom_objects.items():
        obj_type = obj.get("type")
        if obj_type == "tool" and any(re.match(pattern, name) for pattern in config.get('tool',[])):
            fn = make_custom_query_tool(name, obj)
            globals()[name] = fn
            logger.info(f"Created tool: {name}")
        elif obj_type == "prompt"  and any(re.match(pattern, name) for pattern in config.get('prompt',[])):
            fn = make_custom_prompt(name, obj["prompt"], obj.get("description", ""), obj.get("parameters", {}))
            globals()[name] = fn
            logger.info(f"Created prompt: {name}")
        elif obj_type == "cube"  and any(re.match(pattern, name) for pattern in config.get('tool',[])):
            fn = make_custom_cube_tool(name, obj)
            globals()[name] = fn
            logger.info(f"Created cube: {name}")
        elif obj_type == "glossary"  and any(re.match(pattern, name) for pattern in config.get('resource',[])):
            custom_glossary = {k: v for k, v in obj.items() if k != "type"}
            logger.info(f"Added custom glossary entries for: {name}.")
        else:
            logger.info(f"Type {obj_type if obj_type else ''} for custom object {name} is {'unknown' if obj_type else 'undefined'}.")

        for section in ("measures", "dimensions"):
            if section in obj and  any(re.match(pattern, name) for pattern in config.get('tool',[])):
                custom_terms.extend((term, details, name) for term, details in obj[section].items())

    # Enrich glossary
    for term, details, tool_name in custom_terms:
        term_key = term.strip()
        if term_key not in custom_glossary:
            custom_glossary[term_key] = {"definition": details.get("description"), "synonyms": [], "tools": [tool_name]}
        else:
            if "tools" not in custom_glossary[term_key]:
                custom_glossary[term_key]["tools"] = []
            if tool_name not in custom_glossary[term_key]["tools"]:
                custom_glossary[term_key]["tools"].append(tool_name)

    if custom_glossary:
        @mcp.resource("glossary://all")
        def get_glossary() -> dict:
            return custom_glossary

        @mcp.resource("glossary://definitions")
        def get_glossary_definitions() -> dict:
            return {term: details["definition"] for term, details in custom_glossary.items()}

        @mcp.resource("glossary://term/{term_name}")
        def get_glossary_term(term_name: str)  -> dict:
            term = custom_glossary.get(term_name)
            if term:
                return term
            else:
                return {"error": f"Glossary term not found: {term_name}"}

    # Return the configured app and some handles used by the entrypoint if needed
    def cleanup():
        if qg_manager:
            qg_manager.close()
    
    return mcp, logger, cleanup
