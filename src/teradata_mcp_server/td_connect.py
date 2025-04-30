from typing import Optional
import teradatasql
from urllib.parse import urlparse
import logging
import os
from dotenv import load_dotenv
from tabulate import tabulate

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger("teradata_mcp_server")

# This class is used to connect to Teradata database using teradatasql library
#     It uses the connection URL from the environment variable DATABASE_URI from a .env file
#     The connection URL should be in the format: teradata://username:password@host:port/database
class TDConn:
    conn = None
    connection_url = None

    # Constructor
    #     It will read the connection URL from the environment variable DATABASE_URI
    #     It will parse the connection URL and create a connection to the database
    def __init__(self, connection_url: Optional[str] = None):

        if os.getenv("DATABASE_URI") is None:
            logger.error(f"DATABASE_URI is None: {e}")
            self.conn = None
        else:
            parsed_url = urlparse(os.getenv("DATABASE_URI"))
            user = parsed_url.username
            password = parsed_url.password
            host = parsed_url.hostname
            database = parsed_url.path.lstrip('/') 
            self.connection_url = connection_url
            try:
                self.conn = teradatasql.connect (
                    host=host,
                    user=user,
                    password=password,
                    database=database,
                )
            
            except Exception as e:
                logger.error(f"Error connecting to database: {e}")
                self.conn = None
    
    # Method to return the cursor
    #     If the connection is not established, it will raise an exception
    #     If the connection is established, it will return the cursor
    #     The cursor can be used to execute SQL queries
    def cursor(self):
        if self.conn is None:
            logger.error(f"Error cursor is None: {e}")
            raise Exception("No connection to database")
        return self.conn.cursor()

    # Destructor
    #     It will close the connection to the database
    def close(self):
        self.conn.close()

    # Tools
    # Standard methods to implement tool functionalities
    def peek_table(self, tablename, databasename=None):
        """
        This function returns data sample and inferred structure from a database table or view.
        """
        if databasename is not None:
            tablename = f"{databasename}.{tablename}"
        with self.conn.cursor() as cur:
            cur.execute(f'select top 5 * from {tablename}')
            columns=cur.description
            sample=cur.fetchall()

            # Format the column name and descriptions
            columns_desc=""
            for c in columns:
                columns_desc += f"- **{c[0]}**: {c[1].__name__} {f'({c[3]})' if c[3] else ''}\n"

            # Format the data sample as a table
            sample_tab=tabulate(sample, headers=[c[0] for c in columns], tablefmt='pipe')

            # Put the result together as a nicely formatted doc
            return \
f'''
# Database dataset description
Object name: **{tablename}**

## Object structure
Column names, data types and internal representation length if available.
{columns_desc}

## Data sample
This is a data sample:

{sample_tab}
'''