from typing import Optional
import teradatasql
import teradataml as tdml # import of the teradataml package
from urllib.parse import urlparse
import logging
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("teradata_mcp_server")


# ----------- support of the teradataml context -------------
def teradataml_connection():
    if os.getenv("DATABASE_URI") is not None:
        try:
            logmech = os.getenv("LOGMECH", "TD2")
            parsed_url = urlparse(os.getenv("DATABASE_URI"))
            Param = {
                    'username' : parsed_url.username,
                    'password' : parsed_url.password,
                    'host'     : parsed_url.hostname,
                    'database' : parsed_url.path.lstrip('/')
            }

            tdml.create_context(**Param, logmech = logmech)
            logger.info("Connection with teradataml is successful.")
        except Exception as e:
            logger.error(f"Error connecting to database with Teradataml: {e}")
    else:
        logger.warning("DATABASE_URI is not specified, teradataml context has not been established.")

# -----------------------------------------------------------     

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
            logger.warning("DATABASE_URI is not specified, database connection will not be established.")
            self.conn = None
        else:
            connection_url = connection_url or os.getenv("DATABASE_URI")
            parsed_url = urlparse(connection_url)
            user = parsed_url.username
            password = parsed_url.password
            host = parsed_url.hostname
            database = parsed_url.path.lstrip('/') 
            self.connection_url = connection_url
            logmech = os.getenv("LOGMECH", "TD2")
            try:
                self.conn = teradatasql.connect (
                    host=host,
                    user=user,
                    password=password,
                    database=database,
                    logmech=logmech
                )
                logger.info(f"Connected to database: {host}")

            except Exception as e:
                logger.error(f"Error connecting to database: {e}")
                self.conn = None

            #afm--defect teradataml does not auto-reconnect 
            # also, connect to teradataml.  
            teradataml_connection()
    
    # Method to return the cursor
    #     If the connection is not established, it will raise an exception
    #     If the connection is established, it will return the cursor
    #     The cursor can be used to execute SQL queries
    def cursor(self):
        if self.conn is None:
            logger.error("Error cursor is None")
            raise Exception("No connection to database")
        return self.conn.cursor()

    # Destructor
    #     It will close the connection to the database
    def close(self):
        if self.conn is not None:
            try:
                self.conn.close()
                logger.info("Connection to database closed")
            except Exception as e:
                logger.error(f"Error closing connection to database: {e}")
        else:
            logger.warning("Connection to database is already closed")
        

