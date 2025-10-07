import argparse
import os
from urllib.parse import urlparse

from teradataml import *


def main():
    parser = argparse.ArgumentParser(description="Teradata MCP Server")
    parser.add_argument('--database_uri', type=str, required=False, help='Database URI to connect to: teradata://username:password@host:1025/schemaname')
    parser.add_argument('--action', type=str, choices=['setup', 'cleanup'], required=True, help='Action to perform: setup, test or cleanup')
    parser.add_argument('--sysdba_user', type=str, required=True, help='system database administrator user name')
    parser.add_argument('--sysdba_password', type=str, required=True, help='system database administrator password')
    # Extract known arguments and load them into the environment if provided
    args, unknown = parser.parse_known_args()

    connection_url = args.database_uri or os.getenv("DATABASE_URI")

    eng = None
    if args.action in ['setup', 'cleanup']:
        if not connection_url:
            raise ValueError("DATABASE_URI must be provided either as an argument or as an environment variable.")

        parsed_url = urlparse(connection_url)
        user = parsed_url.username
        password = parsed_url.password
        host = parsed_url.hostname
        database = user
        
        
    if args.action=='setup':
        # Set up the analytic functions test data.
        
        ct1 = create_context(host=host, username=args.sysdba_user, password=args.sysdba_password)
        create_user_sql = "CREATE USER test1 AS PERM = 1e9 *(HASHAMP()+1) PASSWORD = test1;"
        execute_sql(create_user_sql)
        remove_context()
        eng = create_context(host=host, username=user, password=password)

        # Setup for SentimentExtractor.
        load_example_data("sentimentextractor", ["sentiment_extract_input"])
        
        create_table_statement = """
        CREATE MULTISET TABLE sentiment_extract_new_data (
            id INTEGER,
            review VARCHAR(500)
        );"""
        execute_sql(create_table_statement)
        insert_statement = """INSERT INTO sentiment_extract_new_data (id, review) VALUES (11, 'Great product!');"""
        execute_sql(insert_statement)
        remove_context()
        
    elif args.action in ('cleanup'):
    
        ct1 = create_context(host=host, username=args.sysdba_user, password=args.sysdba_password)
        drop_user_sql = "drop user test1;"
        execute_sql(drop_user_sql)
        remove_context()

        # Cleanup for ClassificationEvaluator
        eng = create_context(host=host, username=user, password=password)
        db_drop_table(table_name='sentiment_extract_input', suppress_error=True)
        db_drop_table(table_name='sentiment_extract_new_data', suppress_error=True)
        remove_context()
    else:
        raise ValueError(f"Unknown action: {args.action}")
    
    print("Done.")


if __name__ == '__main__':
    main()
