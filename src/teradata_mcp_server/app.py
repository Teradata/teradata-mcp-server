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
import inspect
import os
import re
from importlib.resources import files as pkg_files
from typing import Any

import yaml
from fastmcp import FastMCP
from fastmcp.prompts.prompt import TextContent, Message
from pydantic import Field, BaseModel

from teradata_mcp_server.config import Settings
from teradata_mcp_server import utils as config_utils
from teradata_mcp_server.utils import setup_logging, format_text_response, format_error_response
from teradata_mcp_server.middleware import RequestContextMiddleware
from teradata_mcp_server.tools.utils.queryband import build_queryband
from sqlalchemy.engine import Connection
from fastmcp.server.dependencies import get_context
from teradataml.analytics.json_parser.json_store import _JsonStore
from teradata_mcp_server.tools.utils import (get_dynamic_function_definition,
                                             get_anlytic_function_signature,
                                             convert_tdml_docstring_to_mcp_docstring,
                                             execute_analytic_function)
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
    enableEVS = True if any(re.match(pattern, 'evs_*') for pattern in config.get('tool', [])) else False
    enableTDVS = True if any(re.match(pattern, 'tdvs_*') for pattern in config.get('tool', [])) else False

    # Initialize TD connection and optional teradataml/EFS context
    # Pass settings object to TDConn instead of just connection_url
    tdconn = td.TDConn(settings=settings)

    enable_analytic_functions = profile_name and profile_name == 'dataScientist'

    fs_config = None
    if enableEFS or enable_analytic_functions:

        try:
            import teradataml as tdml
        except (AttributeError, ImportError, ModuleNotFoundError) as e:
            logger.warning(f"teradataml not installed - disabling analytic functions: {e}")
            enable_analytic_functions = False

        # Only import FeatureStoreConfig (which depends on tdfs4ds) when EFS tools are enabled
        try:
            from teradata_mcp_server.tools.fs.fs_utils import FeatureStoreConfig
            fs_config = FeatureStoreConfig()
            # teradataml is optional; warn if unavailable but keep EFS enabled
            try:
                import teradataml as tdml
                try:
                    tdml.create_context(tdsqlengine=tdconn.engine)
                except Exception as e:
                    logger.warning(f"Error creating teradataml context: {e}")
            except (AttributeError, ImportError, ModuleNotFoundError):
                logger.warning("teradataml not installed; EFS tools will operate without a teradataml context")
        except (AttributeError, ImportError, ModuleNotFoundError) as e:
            logger.warning(f"Feature Store module not available - disabling EFS functionality: {e}")
            logger.warning(f"Analytic functions are not available.")
            enableEFS = False

    # EVS connection (optional)
    evs = None
    if len(os.getenv("VS_NAME", "").strip()) > 0:
        try:
            evs = td.get_evs()
            enableEVS = True
        except Exception as e:
            logger.error(f"Unable to establish connection to EVS, disabling: {e}")
            enableEVS = False
            
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

        params = [
            p for name, p in sig.parameters.items()
            if name not in removable and p.kind in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)
        ]
        new_sig = sig.replace(parameters=params)

        # Preserve annotations for Pydantic schema generation
        annotations = {}
        for name, p in sig.parameters.items():
            if name in removable:
                continue
            if p.kind not in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY):
                continue
            if p.annotation is not inspect._empty:
                annotations[name] = p.annotation

        def _exec(*args, **kwargs):
            return execute_db_tool(func, **inject_kwargs, **kwargs)

        _exec.__name__ = getattr(func, "__name__", "wrapped_tool")
        _exec.__signature__ = new_sig
        _exec.__doc__ = func.__doc__
        if annotations:
            _exec.__annotations__ = annotations
        return _exec

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
            wrapped = make_tool_wrapper(func)
            mcp.tool(name=tool_name, description=wrapped.__doc__)(wrapped)
            logger.info(f"Created tool: {tool_name}")
    else:
        logger.warning("No module loader available, skipping code-defined tool registration")

    from teradata_mcp_server.tools.constants import TD_ANALYTIC_FUNCS as funcs
    if enable_analytic_functions:

        tdml_processed_funcs = set(_JsonStore._get_function_list()[0].keys())

        for func_name in funcs:

            # Before adding the function, check if function is existed or not.
            # Connection is not mandatory for MCP server. If connection is not there, then
            # functions can not be added.
            if func_name not in tdml_processed_funcs:
                logger.info("Function {} is not available. Hence not adding it. ".format(func_name))
                continue

            func_metadata = _JsonStore.get_function_metadata(func_name)
            func_obj = getattr(tdml, func_name, None)

            inp_data = [t.get_lang_name() for t in func_metadata.input_tables]

            # Generate function argument string.
            func_args_str = get_anlytic_function_signature(
                func_metadata.function_params)

            func_name = "tdml_" + func_name
            func_str = get_dynamic_function_definition().format(
                analytic_function=func_name,
                doc_string=func_obj.__init__.__doc__,
                func_args_str=func_args_str,
                tables_to_df=json.dumps(inp_data)
            )

            doc_string = convert_tdml_docstring_to_mcp_docstring(
                func_obj.__init__.__doc__)

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
                type_hint_raw = meta.get("type_hint", str)
                if isinstance(type_hint_raw, str):
                    try:
                        type_hint = eval(type_hint_raw, {"str": str, "int": int, "float": float, "bool": bool})
                    except Exception:
                        type_hint = str
                else:
                    type_hint = type_hint_raw
                required = meta.get("required", True)
                desc_txt = meta.get("description", "")
                desc_txt += f" (type: {type_hint_raw})"
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
        param_defs = tool.get("parameters", {})
        parameters = []
        annotations = {}
        for param_name, p in param_defs.items():
            type_hint = p.get("type_hint", str)
            default = inspect.Parameter.empty if p.get("required", True) else p.get("default", None)
            parameters.append(
                inspect.Parameter(param_name, kind=inspect.Parameter.POSITIONAL_OR_KEYWORD, default=default, annotation=type_hint)
            )
            annotations[param_name] = type_hint
        sig = inspect.Signature(parameters)
        async def _dynamic_tool(**kwargs):
            missing = [n for n in annotations if n not in kwargs]
            if missing:
                raise ValueError(f"Missing parameters: {missing}")
            return execute_db_tool(td.handle_base_readQuery, tool["sql"], tool_name=name, **kwargs)
        _dynamic_tool.__signature__ = sig
        _dynamic_tool.__annotations__ = annotations
        return mcp.tool(name=name, description=tool.get("description", ""))(_dynamic_tool)

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
                f"{cube['sql'].strip()}\n"
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
        async def _dynamic_tool(dimensions, measures, dim_filters="", meas_filters="", order_by="", top=None):
            # Accept dimensions and measures as comma-separated strings, parse to lists
            return execute_db_tool(
                td.util_base_dynamicQuery,
                sql_generator=generate_cube_query_tool(name, cube),
                dimensions=dimensions,
                measures=measures,
                dim_filters=dim_filters,
                meas_filters=meas_filters,
                order_by=order_by,
                top=top
            )
        _dynamic_tool.__name__ = 'get_cube_' + name
        # Build allowed values and definitions for dimensions and measures
        dim_lines = []
        for n, d in cube.get('dimensions', {}).items():
            dim_lines.append(f"    - {n}: {d.get('description', '')}")
        measure_lines = []
        for n, m in cube.get('measures', {}).items():
            measure_lines.append(f"    - {n}: {m.get('description', '')}")
        
        # Create example strings for documentation
        dim_examples = [f"{d} {e}" for d, e in zip(list(cube.get('dimensions', {}))[:2], ["= 'value'", "in ('X', 'Y', 'Z')"])]
        dim_example = ' AND '.join(dim_examples)
        
        meas_examples = [f"{m} {e}" for m, e in zip(list(cube.get('measures', {}))[:2], ["> 1000", "= 100"])]
        meas_example = ' AND '.join(meas_examples)
        
        order_examples = [f"{d} {e}" for d, e in zip(list(cube.get('dimensions', {}))[:2], [" ASC", " DESC"])]
        order_example = ' , '.join(order_examples)
        
        _dynamic_tool.__doc__ = f"""
        Tool to query the cube '{name}'.
        {cube.get('description', '')}

        Expected inputs:
            * dimensions (str): Comma-separated dimension names to group by. Allowed values for dimensions\n:
    {chr(10).join(dim_lines)}

            * measures (str): Comma-separated measure names to aggregate. Allowed values for measures:
    {chr(10).join(measure_lines)}

            * dim_filters (str): Filter expression to apply to dimensions. Valid dimension names are: [{', '.join(cube.get('dimensions', {}).keys())}], use valid SQL expressions, for example:
    "{dim_example}"
            * meas_filters (str): Filter expression to apply to computed measures. Valid measure names are: [{', '.join(cube.get('measures', {}).keys())}], use valid SQL expressions, for example:
    "{meas_example}"
            * order_by (str): Order expression on any selected dimensions and measures. Use SQL syntax, for example:
    "{order_example}"
            top (int): Limit the number of rows returned, use a positive integer.

        Returns:
            Query result as a formatted response.
        """
        return mcp.tool(description=_dynamic_tool.__doc__)(_dynamic_tool)

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
    return mcp, logger
