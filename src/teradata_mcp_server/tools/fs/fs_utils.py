from typing import Any, List, Optional
from typing import Optional
from pydantic import Field, BaseModel
import logging
from sqlalchemy.engine import Connection
from sqlalchemy import text
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO

# Suppress stdout/stderr during tdfs4ds import to prevent contamination of MCP JSON protocol
stdout_buffer = StringIO()
stderr_buffer = StringIO()
with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
    import tdfs4ds

logger = logging.getLogger("teradata_mcp_server")

class FeatureStoreConfig(BaseModel):
    """
    Configuration class for the feature store. This model defines the metadata and catalog sources 
    used to organize and access features, processes, and datasets across data domains.
    """

    data_domain: Optional[str] = Field(
        default=None,
        description="The data domain associated with the feature store, grouping features within the same namespace."
    )

    entity: Optional[str] = Field(
        default=None,
        description="The list of entities, comma separated and in alphabetical order, upper case."
    )

    database_name: Optional[str] = Field(
        default=None,
        description="Name of the database where the feature store is hosted."
    )

    feature_catalog: Optional[str] = Field(
        default=None,
        description=(
            "Name of the feature catalog table. "
            "This table contains detailed metadata about features and entities."
        )
    )

    process_catalog: Optional[str] = Field(
        default=None,
        description=(
            "Name of the process catalog table. "
            "Used to retrieve information about feature generation processes, features, and associated entities."
        )
    )

    dataset_catalog: Optional[str] = Field(
        default=None,
        description=(
            "Name of the dataset catalog table. "
            "Used to list and manage available datasets within the feature store."
        )
    )

    def fs_setFeatureStoreConfig(
        self,
        conn: Connection,
        database_name: Optional[str] = None,
        data_domain: Optional[str] = None,
        entity: Optional[str] = None,
    ) -> "FeatureStoreConfig":

        if database_name:
            if tdfs4ds.connect(database=database_name):
                logger.info(f"connected to the feature store of the {database_name} database")
                # Reset data_domain if DB name changes
                if not (self.database_name and self.database_name.upper() == database_name.upper()):
                    self.data_domain = None
                
                self.database_name = database_name
                logger.info(f"connected to the feature store of the {database_name} database")
                self.feature_catalog = f"{database_name}.{tdfs4ds.FEATURE_CATALOG_NAME_VIEW}"
                logger.info(f"feature catalog {self.feature_catalog}")
                self.process_catalog = f"{database_name}.{tdfs4ds.PROCESS_CATALOG_NAME_VIEW}"
                logger.info(f"process catalog {self.process_catalog}")
                self.dataset_catalog = f"{database_name}.FS_V_FS_DATASET_CATALOG"  # <- fixed line
                logger.info(f"dataset catalog {self.dataset_catalog}")

        if self.database_name is not None and data_domain is not None:
            stmt = text(
                f"SELECT COUNT(*) AS N FROM {self.feature_catalog} "
                "WHERE UPPER(data_domain)=:domain"
            )
            result = conn.execute(stmt, {"domain": data_domain.upper()})
            count = result.scalar_one_or_none() or 0
            logger.info("Found %d matching data_domain rows", count)
            if count > 0:
                self.data_domain = data_domain
            else:
                self.data_domain = None

        if self.database_name is not None and self.data_domain is not None and entity is not None:
            stmt = text(
                f"SELECT COUNT(*) AS N FROM {self.feature_catalog} "
                "WHERE UPPER(data_domain)=:domain "
                "AND ENTITY_NAME=:entity"
            )
            result = conn.execute(stmt, {"domain": self.data_domain.upper(), "entity": entity.upper()})
            count = result.scalar_one_or_none() or 0
            logger.info("Found %d matching entity rows", count)
            if count > 0:
                self.entity = entity
        return self