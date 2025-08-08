import tdfs4ds
from tdfs4ds.utils.lineage import crystallize_view
from teradataml import create_context, DataFrame, execute_sql, db_list_tables
from urllib.parse import urlparse
import argparse
import os
import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools

def main():
    parser = argparse.ArgumentParser(description="Teradata MCP Server")
    parser.add_argument('--database_uri', type=str, required=False, help='Database URI to connect to: teradata://username:password@host:1025/schemaname')
    parser.add_argument('--action', type=str, choices=['setup', 'cleanup', 'test'], required=True, help='Action to perform: setup, test or cleanup')
    # Extract known arguments and load them into the environment if provided
    args, unknown = parser.parse_known_args()

    database_name = 'demo_user'
    data_domain = 'demo_dba'
    connection_url = args.database_uri or os.getenv("DATABASE_URI")

    if args.action in ['setup', 'cleanup']:
        if not connection_url:
            raise ValueError("DATABASE_URI must be provided either as an argument or as an environment variable.")

        parsed_url = urlparse(connection_url)
        user = parsed_url.username
        password = parsed_url.password
        host = parsed_url.hostname
        port = parsed_url.port or 1025
        database = parsed_url.path.lstrip('/') or user

        eng = create_context(host = host, username=user, password = password)

    if args.action=='setup':
        # Set up the feature store
        tdfs4ds.setup(database=database_name)
        tdfs4ds.connect(database=database_name)

        # Define the feature store domain
        tdfs4ds.DATA_DOMAIN=data_domain
        tdfs4ds.VARCHAR_SIZE=50

        # Create features (table space and skew)
        df=DataFrame.from_query("SELECT databasename||'.'||tablename tablename, SUM(currentperm) currentperm, CAST((100-(AVG(currentperm)/MAX(currentperm)*100)) AS DECIMAL(5,2)) AS skew_pct FROM dbc.tablesizev GROUP BY 1;")
        df = crystallize_view(df, view_name = 'efs_demo_dba_space', schema_name = database_name,output_view=True)

        # upload the features in the physical feature store
        tdfs4ds.upload_features(
            df,
            entity_id     = ['tablename'],
            feature_names = df.columns[1::],
            metadata      = {'project': 'dba'}
        )

        # Display our features
        tdfs4ds.feature_catalog()

    elif args.action == 'test':
        # test branch
        tdfs4ds.feature_store.schema = database_name
        mcp_client = MultiServerMCPClient({
            "mcp_server": {
                "url": "http://127.0.0.1:8001/mcp",
                "transport": "streamable_http"
            }
        })
        async def runner():
            async with mcp_client.session("mcp_server") as mcp_session:
                tools = await load_mcp_tools(mcp_session)
                fs_tools = [t for t in tools if t.name.startswith('fs_')]
                print("Available fs_ tools:", [t.name for t in fs_tools])

                # Map tool names for quick access
                tool_by_name = {t.name: t for t in fs_tools}

                import json as _json

                async def _call(name: str, payload: dict | None = None):
                    if name not in tool_by_name:
                        raise RuntimeError(f"Tool {name} not found")
                    tool = tool_by_name[name]
                    tool_input = payload or {}
                    # StructuredTool expects a single positional/named argument: tool_input
                    resp = await tool.arun(tool_input=tool_input)
                    # Try to parse JSON text if needed
                    if isinstance(resp, str):
                        try:
                            return _json.loads(resp)
                        except Exception:
                            return resp
                    return resp

                # 1) fs_isFeatureStorePresent
                print("\n[1/8] fs_isFeatureStorePresent…")
                r1 = await _call('fs_isFeatureStorePresent', {"db_name": database_name})
                print("fs_isFeatureStorePresent →", r1)

                # 2) fs_setFeatureStoreConfig
                print("\n[2/8] fs_setFeatureStoreConfig…")
                r_set = await _call('fs_setFeatureStoreConfig', {"db_name": database_name, "data_domain": data_domain})
                print("fs_setFeatureStoreConfig →", r_set)

                # 3) fs_getDataDomains
                print("\n[3/8] fs_getDataDomains…")
                r2 = await _call('fs_getDataDomains')
                print("fs_getDataDomains →", r2)

                # 4) fs_getAvailableDatasets
                print("\n[4/8] fs_getAvailableDatasets…")
                r3 = await _call('fs_getAvailableDatasets')
                print("fs_getAvailableDatasets →", r3)

                # 5) fs_getAvailableEntities
                print("\n[5/8] fs_getAvailableEntities…")
                r4 = await _call('fs_getAvailableEntities')
                print("fs_getAvailableEntities →", r4)

                # 6) fs_setFeatureStoreConfig (entity)
                print("\n[6/8] fs_setFeatureStoreConfig (entity)…")
                def _extract_entity_name(payload):
                    res = payload.get("results") if isinstance(payload, dict) else payload
                    if isinstance(res, list) and res and isinstance(res[0], dict):
                        for key in ("ENTITY_NAME", "entity_name", "entity", "name"):
                            if key in res[0] and res[0][key]:
                                return res[0][key]
                    if isinstance(res, str):
                        lines = [ln.strip() for ln in res.splitlines() if ln.strip()]
                        if lines:
                            parts = lines[-1].split()
                            if parts:
                                return parts[-1]
                    return None
                entity_name = _extract_entity_name(r4) or "tablename"
                r_set_entity = await _call('fs_setFeatureStoreConfig', {"entity": entity_name})
                print("fs_setFeatureStoreConfig (entity) →", r_set_entity)

                # 7) fs_getFeatures
                print("\n[7/8] fs_getFeatures…")
                r5 = await _call('fs_getFeatures')
                print("fs_getFeatures →", r5)

                # Extract feature names from r5
                def _extract_feature_names(payload):
                    # Accept either {"results": [...]} or a raw list
                    items = payload.get("results") if isinstance(payload, dict) else payload
                    if not isinstance(items, list):
                        return []
                    names = []
                    for row in items:
                        if not isinstance(row, dict):
                            continue
                        for key in ("feature_name", "FEATURE_NAME", "name", "FEATURE", "feature"):
                            if key in row and row[key] is not None:
                                names.append(row[key])
                                break
                    return names

                feature_selection = _extract_feature_names(r5)
                print(f"Extracted {len(feature_selection)} feature names for dataset creation")

                # 8) fs_createDataset
                print("\n[8/8] fs_createDataset…")
                create_payload = {
                    "entity_name": entity_name,
                    "feature_selection": feature_selection,
                    "dataset_name": "test_efs_dataset",
                    "target_database": database_name,
                }
                print("fs_createDataset payload:", create_payload)
                r6 = await _call('fs_createDataset', create_payload)

                # If tool returned an error payload (not exception), also retry with CSV features
                if isinstance(r6, dict) and isinstance(r6.get("results"), dict):
                    err = r6["results"].get("error")
                    if isinstance(err, str) and ("NoneType" in err or "string" in err):
                        create_payload_retry = dict(create_payload)
                        create_payload_retry["feature_selection"] = ",".join(feature_selection)
                        print("Retrying fs_createDataset with CSV features (error payload):", create_payload_retry)
                        r6 = await _call('fs_createDataset', create_payload_retry)

                print("fs_createDataset →", r6)

        asyncio.run(runner())

    elif args.action=='cleanup':
        list_of_tables = db_list_tables()
        [execute_sql(f"DROP VIEW {database_name}.{t}") for t in list_of_tables.TableName if t.startswith('FS_V')]
        [execute_sql(f"DROP TABLE {database_name}.{t}") for t in list_of_tables.TableName if t.startswith('FS_T')]
        [execute_sql(f"DROP TABLE {database_name}.{t}") for t in list_of_tables.TableName if t.startswith('FS_T')]
        [execute_sql(f"DROP TABLE {database_name}.{t}") for t in list_of_tables.TableName if t.startswith('FS_T')]

if __name__ == '__main__':
    main()