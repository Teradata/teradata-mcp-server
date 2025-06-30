import logging
from teradatasql import TeradataConnection 
from typing import Optional, Any, Dict, List
import json
from datetime import date, datetime
from decimal import Decimal
import tdfs4ds



logger = logging.getLogger("teradata_mcp_server")

def serialize_teradata_types(obj: Any) -> Any:
    """Convert Teradata-specific types to JSON serializable formats"""
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    return str(obj)

def rows_to_json(cursor_description: Any, rows: List[Any]) -> List[Dict[str, Any]]:
    """Convert database rows to JSON objects using column names as keys"""
    if not cursor_description or not rows:
        return []
    
    columns = [col[0] for col in cursor_description]
    return [
        {
            col: serialize_teradata_types(value)
            for col, value in zip(columns, row)
        }
        for row in rows
    ]

def create_response(data: Any, metadata: Optional[Dict[str, Any]] = None) -> str:
    """Create a standardized JSON response structure"""
    if metadata:
        response = {
            "status": "success",
            "metadata": metadata,
            "results": data
        }
    else:
        response = {
            "status": "success",
            "results": data
        }

    return json.dumps(response, default=serialize_teradata_types)

#------------------ Do not make changes above  ------------------#


#------------------ Tool  ------------------#
# Feature Store existence tool
#     Arguments: 
#       conn (TeradataConnection) - Teradata connection object for executing SQL queries
#       db_name - the database name to check for existenceAdd commentMore actions
# #     Returns: True or False    
def handle_get_fs_is_feature_store_present(conn: TeradataConnection, db_name: str, *args, **kwargs):
    
    logger.info(f"Tool: handle_get_fs_is_feature_store_present: Args: db_name: {db_name}")
    
    data = False
    
    try:
        data = tdfs4ds.connect(database=db_name)
    except Exception as e:
        logger.error(f"Error connecting to Teradata Feature Store: {e}")
        return create_response({"error": str(e)}, {"tool_name": "get_fs_is_feature_store_present", "db_name": db_name})

    metadata = {
        "tool_name": "get_fs_is_feature_store_present",
        "db_name": db_name,
    }
    return create_response(data, metadata)

#------------------ Tool  ------------------#
# Feature Store available data domainAdd commentMore actions
#     Arguments: 
#       conn (TeradataConnection) - Teradata connection object for executing SQL queries
# #     Returns: True or False    
def handle_get_fs_get_data_domains(conn: TeradataConnection, fs_config, *args, **kwargs):
    db_name = fs_config.db_name
    logger.info(f"Tool: handle_get_fs_get_data_domains: Args: db_name: {db_name}")
    
    metadata = {
        "tool_name": "handle_get_fs_get_data_domains",
        "db_name": fs_config.db_name,
    }
    
    if not db_name:
        logger.error("Database name is not provided.")
        return create_response({"error": "The database name for the feature store is not specified."}, metadata)
        
    data = False
    
    try:
        is_a_feature_store = tdfs4ds.connect(database=db_name)
        if not is_a_feature_store:
            return create_response(False, {"tool_name": "handle_get_fs_get_data_domains", "db_name": db_name})
    except Exception as e:
        logger.error(f"Error connecting to Teradata Feature Store: {e}")
        return create_response({"error": str(e)}, {"tool_name": "handle_get_fs_get_data_domains", "db_name": db_name})
    
    sql_query = f"""
    SELECT DISTINCT DATA_DOMAIN FROM {fs_config.feature_catalog}
    """
    logger.info(sql_query)
    with conn.cursor() as cur:
        rows = cur.execute(sql_query)
        data = rows_to_json(cur.description, rows.fetchall())
        metadata = {
            "tool_name": "handle_get_fs_get_data_domains",
            "db_name": fs_config.db_name,
        }

        return create_response(data, metadata)

#------------------ Tool  ------------------#
# Feature high level report of the feature store content
#     Arguments: 
#       conn (TeradataConnection) - Teradata connection object for executing SQL queries
# #     Returns: True or False    
def handle_get_fs_feature_store_content(conn: TeradataConnection, fs_config, *args, **kwargs):
    db_name = fs_config.db_name
    logger.info(f"Tool: handle_get_fs_feature_store_content: Args: db_name: {db_name}")
    metadata = {
        "tool_name": "handle_get_fs_feature_store_content",
        "db_name": fs_config.db_name,
    }
    
    if not db_name:
        logger.error("Database name is not provided.")
        return create_response({"error": "The database name for the feature store is not specified."}, metadata)
    data = False
    
    try:
        is_a_feature_store = tdfs4ds.connect(database=db_name)
        if not is_a_feature_store:
            return create_response(False, {"tool_name": "handle_get_fs_feature_store_content", "db_name": db_name})
    except Exception as e:
        logger.error(f"Error connecting to Teradata Feature Store with tdfs4ds {tdfs4ds.__version__}: {e}")
        return create_response({"error": str(e)}, {"tool_name": "handle_get_fs_feature_store_content", "db_name": db_name})
    
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
def handle_get_fs_get_the_feature_data_model(conn: TeradataConnection, fs_config, *args, **kwargs):
    db_name = fs_config.db_name
    logger.info(f"Tool: handle_get_fs_get_the_feature_data_model: Args: db_name: {db_name}")
    
    is_a_feature_store = False
    
    try:
        is_a_feature_store = tdfs4ds.connect(database=db_name)
    except Exception as e:
        logger.error(f"Error connecting to Teradata Feature Store: {e}")
        return create_response({"error": str(e)}, {"tool_name": "handle_get_fs_get_the_feature_data_model", "db_name": db_name})

    if not is_a_feature_store:
        return create_response({"error": f"There is no feature store in {db_name}"}, {"tool_name": "handle_get_fs_get_the_feature_catalog", "db_name": db_name})

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
        "tool_name": "handle_get_fs_get_the_feature_catalog",
        "db_name": db_name,
    }
    return create_response(data, metadata)

#------------------ Tool  ------------------#
# Feature Store: get abailable entities
#     Arguments: 
#       conn (TeradataConnection) - Teradata connection object for executing SQL queries
#       db_name - the database name to check for existence
# #     Returns: True or False    
def handle_get_fs_get_available_entities(conn: TeradataConnection, fs_config, *args, **kwargs):
    db_name = fs_config.db_name
    logger.info(f"Tool: handle_get_fs_get_available_entities: Args: db_name: {db_name}")
    
    is_a_feature_store = False
    
    try:
        is_a_feature_store = tdfs4ds.connect(database=db_name)
    except Exception as e:
        logger.error(f"Error connecting to Teradata Feature Store: {e}")
        return create_response({"error": str(e)}, {"tool_name": "handle_get_fs_get_available_entities", "db_name": db_name})

    if not is_a_feature_store:
        return create_response({"error": f"There is no feature store in {db_name}"}, {"tool_name": "handle_get_fs_get_available_entities", "db_name": db_name})
    
    # set the data domain:
    data_domain = fs_config.data_domain
    if data_domain is None or data_domain == '':
        return create_response({"error": "The data domain is not specified"}, {"tool_name": "handle_get_fs_get_available_entities", "db_name": db_name})
    
    tdfs4ds.DATA_DOMAIN = data_domain

    

    # get the entities
    from tdfs4ds.feature_store.feature_query_retrieval import get_list_entity

    try:
        data = get_list_entity()
    except Exception as e:
        logger.error(f"Error retrieving entities: {e}")
        return create_response({"error": str(e)}, {"tool_name": "handle_get_fs_get_available_entities", "db_name": db_name})
        
    metadata = {
        "tool_name": "handle_get_fs_get_available_entities",
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
def handle_get_fs_get_available_datasets(conn: TeradataConnection, fs_config, *args, **kwargs):
    db_name = fs_config.db_name
    logger.info(f"Tool: handle_get_fs_get_available_datasets: Args: db_name: {db_name}")
    
    is_a_feature_store = False
    
    try:
        is_a_feature_store = tdfs4ds.connect(database=db_name)
    except Exception as e:
        logger.error(f"Error connecting to Teradata Feature Store: {e}")
        return create_response({"error": str(e)}, {"tool_name": "handle_get_fs_get_available_datasets", "db_name": db_name})

    if not is_a_feature_store:
        return create_response({"error": f"There is no feature store in {db_name}"}, {"tool_name": "handle_get_fs_get_available_datasets", "db_name": db_name})
    
    try:
        data = tdfs4ds.dataset_catalog().to_pandas()
    except Exception as e:
        logger.error(f"Error retrieving available datasets: {e}")
        return create_response({"error": str(e)}, {"tool_name": "handle_get_fs_get_available_datasets", "db_name": db_name})
        
    metadata = {
        "tool_name": "handle_get_fs_get_available_datasets",
        "db_name": db_name,
    }
    return create_response(data, metadata)

#------------------ Tool  ------------------#
# Feature Store: get abailable entities
#     Arguments: 
#       conn (TeradataConnection) - Teradata connection object for executing SQL queries
#       db_name - the database name to check for existence
# #     Returns: True or False    
def handle_get_fs_get_features(conn: TeradataConnection, fs_config, *args, **kwargs):
    db_name = fs_config.db_name
    logger.info(f"Tool: handle_get_fs_get_features: Args: db_name: {db_name}")
    
    if not db_name:
        return create_response({"error": "Database name is not specified"}, {"tool_name": "handle_get_fs_get_features"})
    
    try:
        is_a_feature_store = tdfs4ds.connect(database=db_name)
    except Exception as e:
        logger.error(f"Error connecting to Teradata Feature Store: {e}")
        return create_response({"error": str(e)}, {"tool_name": "handle_get_fs_get_features", "db_name": db_name})

    if not is_a_feature_store:
        return create_response({"error": f"There is no feature store in {db_name}"}, {"tool_name": "handle_get_fs_get_features", "db_name": db_name})

    # Validate required fields
    data_domain     = fs_config.data_domain
    entity          = fs_config.entity
    feature_catalog = fs_config.feature_catalog

    if not data_domain:
        return create_response({"error": "The data domain is not specified"}, {"tool_name": "handle_get_fs_get_features", "db_name": db_name})
    
    if not entity:
        return create_response({"error": "The entity name is not specified"}, {"tool_name": "handle_get_fs_get_features", "db_name": db_name})

    if not feature_catalog:
        return create_response({"error": "The feature catalog table is not specified"}, {"tool_name": "handle_get_fs_get_features", "db_name": db_name})

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
        return create_response({"error": str(e)}, {"tool_name": "handle_get_fs_get_features", "db_name": db_name})

    metadata = {
        "tool_name": "handle_get_fs_get_features",
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
def handle_write_fs_get_create_dataset(conn: TeradataConnection, fs_config, entity_name: str, feature_selection: str, dataset_name: str, target_database: str, *args, **kwargs):
    db_name = fs_config.db_name
    logger.info(f"Tool: handle_get_fs_get_create_dataset: Args: db_name: {db_name}")
    
    is_a_feature_store = False
    
    try:
        is_a_feature_store = tdfs4ds.connect(database=db_name)
    except Exception as e:
        logger.error(f"Error connecting to Teradata Feature Store: {e}")
        return create_response({"error": str(e)}, {"tool_name": "handle_get_fs_get_create_dataset", "db_name": db_name})

    if not is_a_feature_store:
        return create_response({"error": f"There is no feature store in {db_name}"}, {"tool_name": "handle_get_fs_get_create_dataset", "db_name": db_name})
    
    # set the data domain:
    data_domain = fs_config.data_domain
    if data_domain is None or data_domain == '':
        return create_response({"error": "The data domain is not specified"}, {"tool_name": "handle_get_fs_get_create_dataset", "db_name": db_name})

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
        return create_response({"error": str(e)}, {"tool_name": "handle_get_fs_get_create_dataset", "db_name": db_name})
    
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
        return create_response({"error": str(e)}, {"tool_name": "handle_get_fs_get_create_dataset", "db_name": db_name})
    

    data = {
        'VIEW NAME' : target_database + '.' + dataset_name
        }

    metadata = {
        "tool_name": "handle_get_fs_get_create_dataset",
        "db_name": db_name,
        "entity_name": entity_name,
        "data_domain": data_domain, 
        "feature_selection": feature_selection,
        "dataset_name": dataset_name,
        "target_database": target_database
    }
    return create_response(data, metadata)