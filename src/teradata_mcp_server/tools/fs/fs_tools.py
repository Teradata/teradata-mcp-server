import logging

import tdfs4ds
from teradatasql import TeradataConnection

from teradata_mcp_server.tools.utils import create_response, rows_to_json

logger = logging.getLogger("teradata_mcp_server")

from teradata_mcp_server.tools.utils import serialize_teradata_types, rows_to_json, create_response

#------------------ Do not make changes above  ------------------#


#------------------ Tool  ------------------#
# Feature Store existence tool
#     Arguments:
#       conn (TeradataConnection) - Teradata connection object for executing SQL queries
#       db_name - the database name to check for existenceAdd commentMore actions
# #     Returns: True or False
def handle_fs_isFeatureStorePresent(conn: TeradataConnection, db_name: str, *args, **kwargs):
    """ Check if a feature store is present in the specified database.
    
    Args:
        db_name (str): The name of the database to check for the feature store.
    """
    
    logger.info(f"Tool: handle_fs_isFeatureStorePresent: Args: db_name: {db_name}")

    data = False

    try:
        data = tdfs4ds.connect(database=db_name)
    except Exception as e:
        logger.error(f"Error connecting to Teradata Feature Store: {e}")
        return create_response({"error": str(e)}, {"tool_name": "fs_isFeatureStorePresent", "db_name": db_name})

    metadata = {
        "tool_name": "fs_isFeatureStorePresent",
        "db_name": db_name,
    }
    return create_response(data, metadata)

#------------------ Tool  ------------------#
# Feature Store available data domainAdd commentMore actions
#     Arguments:
#       conn (TeradataConnection) - Teradata connection object for executing SQL queries
# #     Returns: True or False
def handle_fs_getDataDomains(conn: TeradataConnection, fs_config, *args, **kwargs):
    """ 
    List the available data domains. Requires a configured `db_name`  in the feature store config. Use this to explore which entities can be used when building a dataset.
    """

    db_name = fs_config.db_name
    logger.info(f"Tool: handle_fs_getDataDomains: Args: db_name: {db_name}")

    metadata = {
        "tool_name": "fs_getDataDomains",
        "db_name": fs_config.db_name,
    }

    if not db_name:
        logger.error("Database name is not provided.")
        return create_response({"error": "The database name for the feature store is not specified."}, metadata)

    data = False

    try:
        is_a_feature_store = tdfs4ds.connect(database=db_name)
        if not is_a_feature_store:
            return create_response(False, {"tool_name": "handle_fs_getDataDomains", "db_name": db_name})
    except Exception as e:
        logger.error(f"Error connecting to Teradata Feature Store: {e}")
        return create_response({"error": str(e)}, {"tool_name": "handle_fs_getDataDomains", "db_name": db_name})

    sql_query = f"""
    SELECT DISTINCT DATA_DOMAIN FROM {fs_config.feature_catalog}
    """
    logger.info(sql_query)
    with conn.cursor() as cur:
        rows = cur.execute(sql_query)
        data = rows_to_json(cur.description, rows.fetchall())
        metadata = {
            "tool_name": "fs_getDataDomains",
            "db_name": fs_config.db_name,
        }

        return create_response(data, metadata)

#------------------ Tool  ------------------#
# Feature high level report of the feature store content
#     Arguments:
#       conn (TeradataConnection) - Teradata connection object for executing SQL queries
# #     Returns: True or False
def handle_fs_featureStoreContent(conn: TeradataConnection, fs_config, *args, **kwargs):
    """ 
    Returns a summary of the feature store content. Use this to understand what data is available in the feature store.
    """

    db_name = fs_config.db_name
    logger.info(f"Tool: handle_fs_featureStoreContent: Args: db_name: {db_name}")
    metadata = {
        "tool_name": "fs_featureStoreContent",
        "db_name": fs_config.db_name,
    }

    if not db_name:
        logger.error("Database name is not provided.")
        return create_response({"error": "The database name for the feature store is not specified."}, metadata)
    data = False

    try:
        is_a_feature_store = tdfs4ds.connect(database=db_name)
        if not is_a_feature_store:
            return create_response(False, {"tool_name": "handle_fs_featureStoreContent", "db_name": db_name})
    except Exception as e:
        logger.error(f"Error connecting to Teradata Feature Store with tdfs4ds {tdfs4ds.__version__}: {e}")
        return create_response({"error": str(e)}, {"tool_name": "handle_fs_featureStoreContent", "db_name": db_name})

    sql_query = f"""
    SELECT DATA_DOMAIN, ENTITY_NAME, count(FEATURE_ID) AS FEATURE_COUNT
    FROM {fs_config.feature_catalog}
    GROUP BY DATA_DOMAIN, ENTITY_NAME
    """

    with conn.cursor() as cur:
        rows = cur.execute(sql_query)
        data = rows_to_json(cur.description, rows.fetchall())

        return create_response(data, metadata)

#------------------ Tool  ------------------#
# Feature Store: feature store schema
#     Arguments:
#       conn (TeradataConnection) - Teradata connection object for executing SQL queries
#       db_name - the database name to check for existence
# #     Returns: the feature store schema, mainly the catalogs
def handle_fs_getFeatureDataModel(conn: TeradataConnection, fs_config, *args, **kwargs):
    """ 
    Returns the feature store data model, including the feature catalog, process catalog, and dataset catalog.
    """

    db_name = fs_config.db_name
    logger.info(f"Tool: handle_fs_getFeatureDataModel: Args: db_name: {db_name}")

    is_a_feature_store = False

    try:
        is_a_feature_store = tdfs4ds.connect(database=db_name)
    except Exception as e:
        logger.error(f"Error connecting to Teradata Feature Store: {e}")
        return create_response({"error": str(e)}, {"tool_name": "handle_fs_getFeatureDataModel", "db_name": db_name})

    if not is_a_feature_store:
        return create_response({"error": f"There is no feature store in {db_name}"}, {"tool_name": "handle_fs_getFeatureDataModel", "db_name": db_name})

    data = {}
    data['FEATURE CATALOG'] = {
        'TABLE' : db_name + '.' + tdfs4ds.FEATURE_CATALOG_NAME_VIEW,
        'DESCRIPTION' : 'lists the available features, data domains and entities'
        }
    data['PROCESS CATALOG'] = {
        'TABLE' : db_name + '.' + tdfs4ds.PROCESS_CATALOG_NAME_VIEW,
        'DESCRIPTION' : 'lists the processes that implements the computation logic.'
    }
    data['DATASET CATALOG'] = {
        'TABLE' : db_name + '.' + 'FS_V_FS_DATASET_CATALOG',
        'DESCRIPTION' : 'lists the available datasets'
    }

    metadata = {
        "tool_name": "fs_getFeatureDataModel",
        "db_name": db_name,
    }
    return create_response(data, metadata)

#------------------ Tool  ------------------#
# Feature Store: get abailable entities
#     Arguments:
#       conn (TeradataConnection) - Teradata connection object for executing SQL queries
#       db_name - the database name to check for existence
# #     Returns: True or False
def handle_fs_getAvailableEntities(conn: TeradataConnection, fs_config, *args, **kwargs):
    """ 
    List the available entities for a given data domain. Requires a configured `db_name` and `data_domain` and  `entity` in the feature store config. Use this to explore which entities can be used when building a dataset.
    """
    db_name = fs_config.db_name
    logger.info(f"Tool: handle_fs_getAvailableEntities: Args: db_name: {db_name}")

    is_a_feature_store = False

    try:
        is_a_feature_store = tdfs4ds.connect(database=db_name)
    except Exception as e:
        logger.error(f"Error connecting to Teradata Feature Store: {e}")
        return create_response({"error": str(e)}, {"tool_name": "handle_fs_getAvailableEntities", "db_name": db_name})

    if not is_a_feature_store:
        return create_response({"error": f"There is no feature store in {db_name}"}, {"tool_name": "handle_fs_getAvailableEntities", "db_name": db_name})

    # set the data domain:
    data_domain = fs_config.data_domain
    if data_domain is None or data_domain == '':
        return create_response({"error": "The data domain is not specified"}, {"tool_name": "handle_fs_getAvailableEntities", "db_name": db_name})

    tdfs4ds.DATA_DOMAIN = data_domain



    # get the entities
    from tdfs4ds.feature_store.feature_query_retrieval import get_list_entity

    try:
        data = get_list_entity()
    except Exception as e:
        logger.error(f"Error retrieving entities: {e}")
        return create_response({"error": str(e)}, {"tool_name": "handle_fs_getAvailableEntities", "db_name": db_name})

    metadata = {
        "tool_name": "fs_getAvailableEntities",
        "db_name": db_name,
        "data_domain": data_domain
    }
    return create_response(data, metadata)

#------------------ Tool  ------------------#
# Feature Store: get abailable entities
#     Arguments:
#       conn (TeradataConnection) - Teradata connection object for executing SQL queries
#       db_name - the database name to check for existence
# #     Returns: True or False
def handle_fs_getAvailableDatasets(conn: TeradataConnection, fs_config, *args, **kwargs):
    """ 
    List the list of available datasets.Requires a configured `db_name` in the feature store config.Use this to explore the datasets that are available .
    """

    db_name = fs_config.db_name
    logger.info(f"Tool: handle_fs_getAvailableDatasets: Args: db_name: {db_name}")

    is_a_feature_store = False

    try:
        is_a_feature_store = tdfs4ds.connect(database=db_name)
    except Exception as e:
        logger.error(f"Error connecting to Teradata Feature Store: {e}")
        return create_response({"error": str(e)}, {"tool_name": "handle_fs_getAvailableDatasets", "db_name": db_name})

    if not is_a_feature_store:
        return create_response({"error": f"There is no feature store in {db_name}"}, {"tool_name": "handle_fs_getAvailableDatasets", "db_name": db_name})

    try:
        data = tdfs4ds.dataset_catalog().to_pandas()
    except Exception as e:
        logger.error(f"Error retrieving available datasets: {e}")
        return create_response({"error": str(e)}, {"tool_name": "handle_fs_getAvailableDatasets", "db_name": db_name})

    metadata = {
        "tool_name": "fs_getAvailableDatasets",
        "db_name": db_name,
    }
    return create_response(data, metadata)

#------------------ Tool  ------------------#
# Feature Store: get abailable entities
#     Arguments:
#       conn (TeradataConnection) - Teradata connection object for executing SQL queries
#       db_name - the database name to check for existence
# #     Returns: True or False
def handle_fs_getFeatures(conn: TeradataConnection, fs_config, *args, **kwargs):
    """ 
    List the list of features. Requires a configured `db_name` and  `data_domain` in the feature store config. Use this to explore the features available .
    """

    db_name = fs_config.db_name
    logger.info(f"Tool: handle_fs_getFeatures: Args: db_name: {db_name}")

    if not db_name:
        return create_response({"error": "Database name is not specified"}, {"tool_name": "handle_fs_getFeatures"})

    try:
        is_a_feature_store = tdfs4ds.connect(database=db_name)
    except Exception as e:
        logger.error(f"Error connecting to Teradata Feature Store: {e}")
        return create_response({"error": str(e)}, {"tool_name": "handle_fs_getFeatures", "db_name": db_name})

    if not is_a_feature_store:
        return create_response({"error": f"There is no feature store in {db_name}"}, {"tool_name": "handle_fs_getFeatures", "db_name": db_name})

    # Validate required fields
    data_domain     = fs_config.data_domain
    entity          = fs_config.entity
    feature_catalog = fs_config.feature_catalog

    if not data_domain:
        return create_response({"error": "The data domain is not specified"}, {"tool_name": "handle_fs_getFeatures", "db_name": db_name})

    if not entity:
        return create_response({"error": "The entity name is not specified"}, {"tool_name": "handle_fs_getFeatures", "db_name": db_name})

    if not feature_catalog:
        return create_response({"error": "The feature catalog table is not specified"}, {"tool_name": "handle_fs_getFeatures", "db_name": db_name})

    tdfs4ds.DATA_DOMAIN = data_domain

    try:
        sql_query = f"""
            SEL * FROM {feature_catalog}
            WHERE DATA_DOMAIN = '{data_domain}' AND ENTITY_NAME = '{entity}'
        """
        with conn.cursor() as cur:
            rows = cur.execute(sql_query)
            data = rows_to_json(cur.description, rows.fetchall())

    except Exception as e:
        logger.error(f"Error retrieving features: {e}")
        return create_response({"error": str(e)}, {"tool_name": "handle_fs_getFeatures", "db_name": db_name})

    metadata = {
        "tool_name": "fs_getFeatures",
        "db_name": db_name,
        "data_domain": data_domain,
        "entity": entity,
        "num_features": len(data)
    }
    return create_response(data, metadata)

#------------------ Tool  ------------------#
# Feature Store: dataset creation tool
#     Arguments:
#       conn (TeradataConnection) - Teradata connection object for executing SQL queries
#       db_name - the database name to check for existence
# #     Returns: True or False
def handle_fs_createDataset(conn: TeradataConnection, fs_config, entity_name: str, feature_selection: list[str], dataset_name: str, target_database: str, *args, **kwargs):
    """ 
    Create a dataset using selected features and an entity from the feature store. The dataset is created in the specified target database under the given name. Requires a configured feature store and data domain. Registers the dataset in the catalog automatically. Use this when you want to build and register a new dataset for analysis or modeling.
    Args:
        entity_name (str): Entity for which the dataset will be created. Available entities are reported in the feature catalog.
        feature_selection (list[str]): List of features to include in the dataset. Available features are reported in the feature catalog.
        dataset_name (str): The name of the dataset to create.
        target_database (str): The database where the dataset will be created.
    """

    db_name = fs_config.db_name
    logger.info(f"Tool: handle_fs_createDataset: Args: db_name: {db_name}")

    is_a_feature_store = False

    try:
        is_a_feature_store = tdfs4ds.connect(database=db_name)
    except Exception as e:
        logger.error(f"Error connecting to Teradata Feature Store: {e}")
        return create_response({"error": str(e)}, {"tool_name": "handle_fs_createDataset", "db_name": db_name})

    if not is_a_feature_store:
        return create_response({"error": f"There is no feature store in {db_name}"}, {"tool_name": "handle_fs_createDataset", "db_name": db_name})

    # set the data domain:
    data_domain = fs_config.data_domain
    if data_domain is None or data_domain == '':
        return create_response({"error": "The data domain is not specified"}, {"tool_name": "handle_fs_createDataset", "db_name": db_name})

    tdfs4ds.DATA_DOMAIN = data_domain


    # get the feature version:
    from tdfs4ds.feature_store.feature_query_retrieval import get_feature_versions

    try:
        feature_selection = get_feature_versions(
            entity_name = entity_name,
            features    = feature_selection
        )
    except Exception as e:
        logger.error(f"Error retrieving feature versions: {e}")
        return create_response({"error": str(e)}, {"tool_name": "handle_fs_createDataset", "db_name": db_name})

    # build the dataset
    from tdfs4ds import build_dataset
    try:
        dataset = build_dataset(
            entity_id         = entity_name,
            selected_features = feature_selection,
            view_name         = dataset_name,
            schema_name      = target_database,
            comment           = 'my dataset for curve clustering'
        )
    except Exception as e:
        logger.error(f"Error creating dataset: {e}")
        return create_response({"error": str(e)}, {"tool_name": "handle_fs_createDataset", "db_name": db_name})


    data = {
        'VIEW NAME' : target_database + '.' + dataset_name
        }

    metadata = {
        "tool_name": "fs_createDataset",
        "db_name": db_name,
        "entity_name": entity_name,
        "data_domain": data_domain,
        "feature_selection": feature_selection,
        "dataset_name": dataset_name,
        "target_database": target_database
    }
    return create_response(data, metadata)
