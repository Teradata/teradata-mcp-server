from typing import Optional
import teradataml as tdml # import of the teradataml package
from urllib.parse import urlparse
import logging
import os
from dotenv import load_dotenv

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool

load_dotenv()

logger = logging.getLogger("teradata_mcp_server")



# This class is used to connect to Teradata database using SQLAlchemy (teradatasqlalchemy driver)
#     It uses the connection URL from the environment variable DATABASE_URI from a .env file
#     The connection URL should be in the format: teradata://username:password@host:port/database
class TDConn:
    engine: Optional[Engine] = None
    connection_url: Optional[str] = None

    # Constructor
    #     It will read the connection URL from the environment variable DATABASE_URI
    #     It will parse the connection URL and create a SQLAlchemy engine connected to the database
    def __init__(self, connection_url: Optional[str] = None):
        if connection_url is None and os.getenv("DATABASE_URI") is None:
            logger.warning("DATABASE_URI is not specified, database connection will not be established.")
            self.engine = None
        else:
            connection_url = connection_url or os.getenv("DATABASE_URI")
            parsed_url = urlparse(connection_url)
            user = parsed_url.username
            password = parsed_url.password
            host = parsed_url.hostname
            port = parsed_url.port or 1025
            database = parsed_url.path.lstrip('/')
            logmech = os.getenv("LOGMECH", "TD2")

            # Pool parameters from env
            pool_size = int(os.getenv("TD_POOL_SIZE", 5))
            max_overflow = int(os.getenv("TD_MAX_OVERFLOW", 10))
            pool_timeout = int(os.getenv("TD_POOL_TIMEOUT", 30))

            # Build SQLAlchemy connection string for teradatasqlalchemy
            # Format: teradatasql://user:pass@host:port/database?LOGMECH=TD2
            sqlalchemy_url = (
                f"teradatasql://{user}:{password}@{host}:{port}/{database}?LOGMECH={logmech}"
            )

            try:
                self.engine = create_engine(
                    sqlalchemy_url,
                    poolclass=QueuePool,
                    pool_size=pool_size,
                    max_overflow=max_overflow,
                    pool_timeout=pool_timeout,
                )
                self.connection_url = sqlalchemy_url
                logger.info(f"SQLAlchemy engine created for Teradata: {host}:{port}/{database}")
            except Exception as e:
                logger.error(f"Error creating database engine: {e}")
                self.engine = None

            # Create the teradataml context 
            if "<EVS or EFS enabled>":
                import teradataml as tdml # import of the teradataml package
                tdml.create_context(tdsqlengine=self.engine)

    # Destructor
    #     It will close the SQLAlchemy connection and engine
    def close(self):
        if self.engine is not None:
            try:
                self.engine.dispose()
                logger.info("SQLAlchemy engine disposed")
            except Exception as e:
                logger.error(f"Error disposing SQLAlchemy engine: {e}")
        else:
            logger.warning("SQLAlchemy engine is already disposed or was never created")


