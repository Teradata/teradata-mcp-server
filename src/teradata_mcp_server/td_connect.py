from typing import Optional
import teradatasql
from urllib.parse import urlparse
import logging
import os
from tabulate import tabulate

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

        if connection_url is None and os.getenv("DATABASE_URI") is None:
            logger.warning(f"DATABASE_URI is not specified, database connection will not be established.")
            self.conn = None
        else:
            connection_url = connection_url or os.getenv("DATABASE_URI")
            parsed_url = urlparse(connection_url)
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
                logger.info(f"Connected to database: {host}")

            except Exception as e:
                logger.error(f"Error connecting to database: {e}")
                self.conn = None
    
    # Method to return the cursor
    #     If the connection is not established, it will raise an exception
    #     If the connection is established, it will return the cursor
    #     The cursor can be used to execute SQL queries
    def cursor(self):
        if self.conn is None:
            logger.error(f"Error cursor is None")
            raise Exception("No connection to database")
        return self.conn.cursor()

    # Destructor
    #     It will close the connection to the database
    def close(self):
        self.conn.cursor().close()
        if self.conn is not None:
            try:
                self.conn.close()
                logger.info(f"Connection to database closed")
            except Exception as e:
                logger.error(f"Error closing connection to database: {e}")
        else:
            logger.warning(f"Connection to database is already closed")
        

