from typing import Any, List, Optional
from pydantic import Field, BaseModel

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

    db_name: Optional[str] = Field(
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
