import logging
import os
from typing import Optional, Any
from urllib.parse import urlparse, quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool, NullPool

from .utils import (
    parse_auth_header,
    parse_basic_credentials,
    extract_unverified_jwt_claims,
    map_principal_from_claims,
)

load_dotenv()

logger = logging.getLogger("teradata_mcp_server")



# This class is used to connect to Teradata database using SQLAlchemy (teradatasqlalchemy driver)
#     It uses the connection URL from the environment variable DATABASE_URI from a .env file
#     The connection URL should be in the format: teradata://username:password@host:port/database
class TDConn:
    engine: Engine | None = None
    connection_url: str | None = None

    # Constructor
    #     It will read the connection URL from the environment variable DATABASE_URI
    #     It will parse the connection URL and create a SQLAlchemy engine connected to the database
    def __init__(self, connection_url: str | None = None):
        if connection_url is None and os.getenv("DATABASE_URI") is None:
            logger.warning("DATABASE_URI is not specified, database connection will not be established.")
            self.engine = None
        else:
            connection_url = connection_url or os.getenv("DATABASE_URI")
            parsed_url = urlparse(connection_url)
            user = parsed_url.username
            password = parsed_url.password
            self._base_host = parsed_url.hostname
            self._base_port = parsed_url.port or 1025
            self._base_db = parsed_url.path.lstrip('/')
            self._default_basic_logmech = os.getenv("LOGMECH", "TD2")

            # Pool parameters from env
            pool_size = int(os.getenv("TD_POOL_SIZE", 5))
            max_overflow = int(os.getenv("TD_MAX_OVERFLOW", 10))
            pool_timeout = int(os.getenv("TD_POOL_TIMEOUT", 30))

            # Build SQLAlchemy connection string for teradatasqlalchemy
            # Format: teradatasql://user:pass@host:port/database?LOGMECH=TD2
            sqlalchemy_url = (
                f"teradatasql://{user}:{password}@{self._base_host}:{self._base_port}/{self._base_db}?LOGMECH={self._default_basic_logmech}"
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
                logger.info(f"SQLAlchemy engine created for Teradata: {self._base_host}:{self._base_port}/{self._base_db}")
            except Exception as e:
                logger.error(f"Error creating database engine: {e}")
                self.engine = None

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

    # ------------------------------------------------------------------
    # Auth header parsing & validation (for AUTH_MODE=basic)
    # ------------------------------------------------------------------
    def validate_auth_header(self, auth_header: str) -> Optional[str]:
        """
        Validate an HTTP Authorization header against Teradata and return the
        database username (principal) to impersonate if valid, else None.

        Rules:
          - If scheme == Basic: treat credential as base64(user:secret) and
            validate using the TDConn's default basic LOGMECH (LDAP/TD2/KRB5).
            The returned principal is the Basic username.
          - If scheme == Bearer: treat value as a JWT and validate using
            LOGMECH=JWT with LOGDATA=token=<jwt>. The returned principal is
            inferred from JWT claims (db_user → preferred_username → sub).
        """
        scheme, value = parse_auth_header(auth_header)
        if not scheme or not value:
            return None

        if scheme == "basic":
            user, secret = parse_basic_credentials(value)
            if not user or not secret:
                return None
            ok = self._quick_password_validation(user, secret, self._default_basic_logmech)
            return user if ok else None

        if scheme == "bearer":
            token = value
            if not token:
                return None
            ok = self._quick_jwt_validation(token)
            if not ok:
                return None
            claims = extract_unverified_jwt_claims(token)
            principal = map_principal_from_claims(
                claims,
                strategy=os.getenv("USERMAP_STRATEGY", "claim:preferred_username"),
                fallback=None,
            )
            return principal

        # Unsupported scheme
        return None

    # ----------------- quick validation against TD ---------------------
    def _quick_password_validation(self, user: str, secret: str, logmech: str) -> bool:
        """Attempt a short-lived Teradata connection with user/password.
        Uses the same host/port/db as the service account, but swaps creds and LOGMECH.
        Returns True on success, False otherwise.
        """
        try:
            sqlalchemy_url = (
                f"teradatasql://{user}:{secret}@{self._base_host}:{self._base_port}/{self._base_db}?LOGMECH={logmech}"
            )
            engine = create_engine(
                sqlalchemy_url,
                poolclass=NullPool,
                connect_args={"QUERY_TIMEOUT": 5},
            )
            with engine.connect() as conn:
                conn.exec_driver_sql("SELECT 1")
            engine.dispose()
            return True
        except Exception as e:
            logger.debug(f"Password validation failed for user '{user}' with LOGMECH={logmech}: {e}")
            return False

    def _quick_jwt_validation(self, jwt_token: str) -> bool:
        """Attempt a short-lived Teradata connection using LOGMECH=JWT.
        Passes the token via LOGDATA=token=<jwt>.
        Returns True on success, False otherwise.
        """
        try:
            # No username needed for JWT LOGMECH
            sqlalchemy_url = (
                f"teradatasql://@{self._base_host}:{self._base_port}/{self._base_db}?LOGMECH=JWT&LOGDATA=token={quote_plus(jwt_token)}"
            )
            engine = create_engine(
                sqlalchemy_url,
                poolclass=NullPool,
                connect_args={"QUERY_TIMEOUT": 5},
            )
            with engine.connect() as conn:
                conn.exec_driver_sql("SELECT 1")
            engine.dispose()
            return True
        except Exception as e:
            logger.debug(f"JWT validation failed via LOGMECH=JWT: {e}")
            return False
