import logging
from typing import TYPE_CHECKING, Optional
from urllib.parse import quote_plus, urlparse

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.pool import NullPool, QueuePool

from .auth_validation import (
    AuthValidator,
    InvalidTokenFormatError,
    InvalidUsernameError,
    RateLimiter,
    RateLimitExceededError,
)
from .utils import (
    parse_auth_header,
    parse_basic_credentials,
)

if TYPE_CHECKING:
    from teradata_mcp_server.config import Settings

logger = logging.getLogger("teradata_mcp_server")



# This class is used to connect to Teradata database using SQLAlchemy (teradatasqlalchemy driver)
#     It uses the connection URL from the environment variable DATABASE_URI from a .env file
#     The connection URL should be in the format: teradata://username:password@host:port/database
class TDConn:
    engine: Engine | None = None

    def __init__(self, settings: Optional['Settings'] = None):
        """
        Initialize TDConn with configuration from Settings object.

        Args:
            settings: Settings object containing database configuration
        """
        if settings is None:
            # Backward compatibility: create minimal settings from environment
            import os

            # Fallback to environment variables if no settings provided
            self._rate_limiter = RateLimiter(
                max_attempts=int(os.getenv("AUTH_RATE_LIMIT_ATTEMPTS", "5")),
                window_seconds=int(os.getenv("AUTH_RATE_LIMIT_WINDOW", "60"))
            )
            connection_url = os.getenv("DATABASE_URI")
            if connection_url is None:
                logger.warning("No database configuration provided, database connection will not be established.")
                self.engine = None
                return

            logmech = os.getenv("LOGMECH", "TD2")
            pool_size = int(os.getenv("TD_POOL_SIZE", "5"))
            max_overflow = int(os.getenv("TD_MAX_OVERFLOW", "10"))
            pool_timeout = int(os.getenv("TD_POOL_TIMEOUT", "30"))
        else:
            # Use settings object
            self._rate_limiter = RateLimiter(
                max_attempts=settings.auth_rate_limit_attempts,
                window_seconds=settings.auth_rate_limit_window
            )
            connection_url = settings.database_uri
            if connection_url is None:
                logger.warning("No database URI specified in settings, database connection will not be established.")
                self.engine = None
                return

            logmech = settings.logmech
            pool_size = settings.pool_size
            max_overflow = settings.max_overflow
            pool_timeout = settings.pool_timeout

        # Parse connection URL
        parsed_url = urlparse(connection_url)
        user = parsed_url.username
        password = parsed_url.password
        self._base_host = parsed_url.hostname
        self._base_port = parsed_url.port or 1025
        self._base_db = parsed_url.path.lstrip('/')
        self._default_basic_logmech = logmech

        # Build SQLAlchemy connection string for teradatasqlalchemy
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
    def validate_auth_header(self, auth_header: str) -> str | None:
        """
        Validate an HTTP Authorization header against Teradata and return the
        database username (principal) to impersonate if valid, else None.

        Rules:
          - If scheme == Basic: treat credential as base64(user:secret) and
            validate using the TDConn's default basic LOGMECH (LDAP/TD2/KRB5).
            The returned principal is the Basic username.
          - If scheme == Bearer: treat value as a JWT and validate using
            LOGMECH=JWT with LOGDATA=token=<jwt>. The returned principal is
            the authenticated database user from the connection.

        Raises:
          - RateLimitExceededError: If too many auth attempts from this client
          - InvalidUsernameError: If username format is invalid
          - InvalidTokenFormatError: If token format is invalid
        """
        # Apply rate limiting
        from .auth_validation import generate_client_id
        client_id = generate_client_id(auth_header)
        if not self._rate_limiter.is_allowed(client_id):
            raise RateLimitExceededError(self._rate_limiter.window_seconds)

        scheme, value = parse_auth_header(auth_header)
        if not scheme or not value:
            return None

        if scheme == "basic":
            # Validate Basic token format first
            if not AuthValidator.validate_basic_token(value):
                raise InvalidTokenFormatError("Invalid Basic authentication token format")

            user, secret = parse_basic_credentials(value)
            if not user or not secret:
                return None

            # Validate username format
            if not AuthValidator.validate_username(user):
                raise InvalidUsernameError(f"Invalid username format: {user}")

            result = self._validate_basic_credentials(user, secret, self._default_basic_logmech)
            if result:
                # Clear rate limit on successful authentication
                self._rate_limiter.clear_client(client_id)
            return result

        if scheme == "bearer":
            token = value
            if not token:
                return None

            # Validate JWT format first
            if not AuthValidator.validate_jwt_format(token):
                raise InvalidTokenFormatError("Invalid JWT token format")

            result = self._validate_jwt_token(token)
            if result:
                # Clear rate limit on successful authentication
                self._rate_limiter.clear_client(client_id)
            return result

        # Unsupported scheme
        return None

    # ----------------- credential validation against TD ---------------------
    def _validate_basic_credentials(self, user: str, secret: str, logmech: str) -> str | None:
        """Validate user/password credentials against Teradata database.
        Uses the same host/port as the service account, but connects to the user's default database.
        Returns the validated username on success, None otherwise.
        """
        try:
            # For basic credential validation, just validate the credentials without specifying a database
            # Let Teradata use the user's default database
            sqlalchemy_url = (
                f"teradatasql://{user}:{secret}@{self._base_host}:{self._base_port}?LOGMECH={logmech}"
            )
            engine = create_engine(
                sqlalchemy_url,
                poolclass=NullPool,
                # Note: QUERY_TIMEOUT is not supported in connect_args for teradatasql driver
            )
            with engine.connect() as conn:
                conn.exec_driver_sql("SELECT 1")
            engine.dispose()
            return user  # Return the validated username
        except Exception as e:
            logger.debug(f"Basic credential validation failed for user '{user}' with LOGMECH={logmech}: {e}")
            return None

    def _validate_jwt_token(self, jwt_token: str) -> str | None:
        """Validate JWT token against Teradata database and return authenticated username.
        Uses LOGMECH=JWT with the token passed via LOGDATA.
        Returns the database username of the authenticated user, None on failure.
        """
        try:
            # No username needed for JWT LOGMECH
            sqlalchemy_url = (
                f"teradatasql://@{self._base_host}:{self._base_port}/{self._base_db}?LOGMECH=JWT&LOGDATA=token={quote_plus(jwt_token)}"
            )
            engine = create_engine(
                sqlalchemy_url,
                poolclass=NullPool,
                # Note: QUERY_TIMEOUT is not supported in connect_args for teradatasql driver
            )
            with engine.connect() as conn:
                # Get the authenticated database username
                result = conn.exec_driver_sql("SELECT USER")
                username = result.fetchone()[0]
            engine.dispose()
            return username
        except Exception as e:
            logger.debug(f"JWT token validation failed via LOGMECH=JWT: {e}")
            return None
