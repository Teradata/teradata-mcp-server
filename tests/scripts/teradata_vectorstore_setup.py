import argparse
import os
from urllib.parse import urlparse

from teradataml import *


def main():
    parser = argparse.ArgumentParser(description="Teradata MCP Server")
    parser.add_argument('--database_uri', type=str, required=False, help='Database URI to connect to: teradata://username:password@host:1025/schemaname')
    parser.add_argument('--action', type=str, choices=['setup', 'cleanup'], required=True, help='Action to perform: setup, test or cleanup')
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

        eng = create_context(host=host, username=user, password=password)

    if args.action=='setup':
        # Set up the analytic functions test data.

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
        
    elif args.action in ('cleanup'):

        # Cleanup for ClassificationEvaluator
        db_drop_table(table_name='sentiment_extract_input', suppress_error=True)
    else:
        raise ValueError(f"Unknown action: {args.action}")

    # Drop the context if it was created
    if eng:
        remove_context()
        
    print("Done.")


if __name__ == '__main__':
    main()