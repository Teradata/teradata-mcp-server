import argparse
import os
from urllib.parse import urlparse

from teradataml import create_context, db_drop_table, load_example_data, remove_context


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
        # Set up the feature store
        load_example_data("dataframe", "sales")

    elif args.action in ('cleanup'):
        db_drop_table(table_name="sales", suppress_error=True)
        print("Or you can run the cleanup action of this script with: `plot_setup.py --action cleanup`")
    else:
        raise ValueError(f"Unknown action: {args.action}")

    # Drop the context if it was created
    if eng:
        remove_context()


if __name__ == '__main__':
    main()
