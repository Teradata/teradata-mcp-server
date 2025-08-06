import tdfs4ds
from tdfs4ds.utils.lineage import crystallize_view
from teradataml import create_context, DataFrame, execute_sql, db_list_tables
from urllib.parse import urlparse
import argparse
import os

parser = argparse.ArgumentParser(description="Teradata MCP Server")
parser.add_argument('--database_uri', type=str, required=False, help='Database URI to connect to: teradata://username:password@host:1025/schemaname')
parser.add_argument('--action', type=str, choices=['setup', 'cleanup'], required=True, help='Action to perform: setup or cleanup')
# Extract known arguments and load them into the environment if provided
args, unknown = parser.parse_known_args()

database_name = 'demo_user'
connection_url = args.database_uri or os.getenv("DATABASE_URI")

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
    tdfs4ds.DATA_DOMAIN='demo_dba'
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

elif args.action=='cleanup':
    list_of_tables = db_list_tables()
    [execute_sql(f"DROP VIEW {database_name}.{t}") for t in list_of_tables.TableName if t.startswith('FS_V')]
    [execute_sql(f"DROP TABLE {database_name}.{t}") for t in list_of_tables.TableName if t.startswith('FS_T')]
    [execute_sql(f"DROP TABLE {database_name}.{t}") for t in list_of_tables.TableName if t.startswith('FS_T')]
    [execute_sql(f"DROP TABLE {database_name}.{t}") for t in list_of_tables.TableName if t.startswith('FS_T')]