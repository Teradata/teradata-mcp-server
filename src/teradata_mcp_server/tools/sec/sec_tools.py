import logging
from teradatasql import TeradataConnection 
from typing import Optional, Any, Dict, List
import json
from datetime import date, datetime
from decimal import Decimal

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
# get user permissions tool
#     Arguments: 
#       conn (TeradataConnection) - Teradata connection object for executing SQL queries
#       user_name (str) - The username for which to retrieve permissions
#       
#     Returns: permissions assigned to user_name or error message
def handle_sec_userDbPermissions(conn: TeradataConnection, user_name: str, *args, **kwargs):
    logger.debug(f"Tool: handle_sec_userDbPermissions: Args: user_name: {user_name}")

    with conn.cursor() as cur:
        if user_name == "":
            logger.debug("No user_name argument provided")
            rows = []
        else:
            logger.debug(f"Argument provided: {user_name}")
            rows = cur.execute(f"""
                SELECT 
                    DatabaseName, 
                    TableName, 
                    ColumnName, 
                    AccessRight, 
                    GrantAuthority, 
                    GrantorName 
                FROM DBC.AllRightsV 
                WHERE UserName = '{user_name}' 
                ORDER BY DatabaseName, TableName, AccessRight;""")

        data = rows_to_json(cur.description, rows.fetchall())
        metadata = {
            "tool_name": "sec_userDbPermissions",
            "argument": user_name,
        }
        return create_response(data, metadata) 


#------------------ Tool  ------------------#
# get role permissions tool
#     Arguments: 
#       conn (TeradataConnection) - Teradata connection object for executing SQL queries
#       role_name (str) - The role name for which to retrieve permissions
#
#     Returns: permissions assigned to role_name or error message
def handle_sec_rolePermissions(conn: TeradataConnection, role_name: str, *args, **kwargs):
    logger.debug(f"Tool: handle_sec_rolePermissions: Args: role_name: {role_name}")

    with conn.cursor() as cur:
        if role_name == "":
            logger.debug("No role_name argument provided")
            rows = []
        else:
            logger.debug(f"Argument provided: {role_name}")
            rows = cur.execute(f"""
                SELECT RN.Grantee
                    ,ARR.DatabaseName
                    ,ARR.AccessRight
                    ,CASE 
                            WHEN ARR.AccessRight = 'AE' THEN 'ALTER EXTERNAL PROCEDURE'    
                            WHEN ARR.AccessRight = 'AF' THEN 'ALTER FUNCTION'    
                            WHEN ARR.AccessRight = 'AP' THEN 'ALTER PROCEDURE'    
                            WHEN ARR.AccessRight = 'AS' THEN 'ABORT SESSION'    
                            WHEN ARR.AccessRight = 'CA' THEN 'CREATE AUTHORIZATION'    
                            WHEN ARR.AccessRight = 'CD' THEN 'CREATE DATABASE'    
                            WHEN ARR.AccessRight = 'CE' THEN 'CREATE EXTERNAL PROCEDURE'    
                            WHEN ARR.AccessRight = 'CF' THEN 'CREATE FUNCTION'    
                            WHEN ARR.AccessRight = 'CG' THEN 'CREATE TRIGGER'    
                            WHEN ARR.AccessRight = 'CM' THEN 'CREATE MACRO'    
                            WHEN ARR.AccessRight = 'CO' THEN 'CREATE PROFILE'    
                            WHEN ARR.AccessRight = 'CP' THEN 'CHECKPOINT'    
                            WHEN ARR.AccessRight = 'CR' THEN 'CREATE ROLE'    
                            WHEN ARR.AccessRight = 'CT' THEN 'CREATE TABLE'    
                            WHEN ARR.AccessRight = 'CU' THEN 'CREATE USER'    
                            WHEN ARR.AccessRight = 'CV' THEN 'CREATE VIEW'    
                            WHEN ARR.AccessRight = 'D'  THEN 'DELETE'    
                            WHEN ARR.AccessRight = 'DA' THEN 'DROP AUTHORIZATION'    
                            WHEN ARR.AccessRight = 'DD' THEN 'DROP DATABASE'    
                            WHEN ARR.AccessRight = 'DF' THEN 'DROP FUNCTION'    
                            WHEN ARR.AccessRight = 'DG' THEN 'DROP TRIGGER'    
                            WHEN ARR.AccessRight = 'DM' THEN 'DROP MACRO'    
                            WHEN ARR.AccessRight = 'DO' THEN 'DROP PROFILE'    
                            WHEN ARR.AccessRight = 'DP' THEN 'DUMP'    
                            WHEN ARR.AccessRight = 'DR' THEN 'DROP ROLE'    
                            WHEN ARR.AccessRight = 'DT' THEN 'DROP TABLE'    
                            WHEN ARR.AccessRight = 'DU' THEN 'DROP USER'    
                            WHEN ARR.AccessRight = 'DV' THEN 'DROP VIEW'    
                            WHEN ARR.AccessRight = 'E'  THEN 'EXECUTE'    
                            WHEN ARR.AccessRight = 'EF' THEN 'EXECUTE FUNCTION'    
                            WHEN ARR.AccessRight = 'GC' THEN 'CREATE GLOP'    
                            WHEN ARR.AccessRight = 'GD' THEN 'DROP GLOP'    
                            WHEN ARR.AccessRight = 'GM' THEN 'GLOP MEMBER'    
                            WHEN ARR.AccessRight = 'I'  THEN 'INSERT'    
                            WHEN ARR.AccessRight = 'IX' THEN 'INDEX'    
                            WHEN ARR.AccessRight = 'MR' THEN 'MONITOR RESOURCE'    
                            WHEN ARR.AccessRight = 'MS' THEN 'MONITOR SESSION'    
                            WHEN ARR.AccessRight = 'NT' THEN 'NONTEMPORAL'    
                            WHEN ARR.AccessRight = 'OD' THEN 'OVERRIDE DELETE POLICY'    
                            WHEN ARR.AccessRight = 'OI' THEN 'OVERRIDE INSERT POLICY'    
                            WHEN ARR.AccessRight = 'OP' THEN 'CREATE OWNER PROCEDURE'    
                            WHEN ARR.AccessRight = 'OS' THEN 'OVERRIDE SELECT POLICY'    
                            WHEN ARR.AccessRight = 'OU' THEN 'OVERRIDE UPDATE POLICY'    
                            WHEN ARR.AccessRight = 'PC' THEN 'CREATE PROCEDURE'    
                            WHEN ARR.AccessRight = 'PD' THEN 'DROP PROCEDURE'    
                            WHEN ARR.AccessRight = 'PE' THEN 'EXECUTE PROCEDURE'    
                            WHEN ARR.AccessRight = 'R'  THEN 'SELECT'    
                            WHEN ARR.AccessRight = 'RF' THEN 'REFERENCE'    
                            WHEN ARR.AccessRight = 'RO' THEN 'REPLCONTROL'    
                            WHEN ARR.AccessRight = 'RS' THEN 'RESTORE'    
                            WHEN ARR.AccessRight = 'SA' THEN 'SECURITY CONSTRAINT ASSIGNMENT'    
                            WHEN ARR.AccessRight = 'SD' THEN 'SECURITY CONSTRAINT DEFINITION'    
                            WHEN ARR.AccessRight = 'SH' THEN 'SHOW'    
                            WHEN ARR.AccessRight = 'SR' THEN 'SET RESOURCE RATE'    
                            WHEN ARR.AccessRight = 'SS' THEN 'SET SESSION RATE'    
                            WHEN ARR.AccessRight = 'ST' THEN 'STATISTICS'    
                            WHEN ARR.AccessRight = 'TH' THEN 'CTCONTROL'    
                            WHEN ARR.AccessRight = 'U'  THEN 'UPDATE'
                            ELSE 'Unknown'
                        END AS AccesRightText
                FROM DBC.RoleMembers AS RN
                INNER JOIN DBC.AllRoleRights AS ARR 
                    ON RN.RoleName = ARR.RoleName 
                WHERE RN.Grantee = '{role_name}'
                GROUP BY 1, 2, 3, 4
                ORDER BY 1, 2, 3, 4;""")

        data = rows_to_json(cur.description, rows.fetchall())
        metadata = {
            "tool_name": "sec_rolePermissions",
            "argument": role_name,
        }
        return create_response(data, metadata)


#------------------ Tool  ------------------#
# get roles that a user belongs to tool
#     Arguments: 
#       conn (TeradataConnection) - Teradata connection object for executing SQL queries
#       user_name (str) - The username for which to retrieve roles
#
#     Returns: roles assigned to user_name or error message
def handle_sec_userRoles(conn: TeradataConnection, user_name: str, *args, **kwargs):
    logger.debug(f"Tool: handle_sec_userRoles: Args: user_name: {user_name}")

    with conn.cursor() as cur:
        if user_name == "":
            logger.debug("No user_name argument provided")
            rows = []
        else:
            logger.debug(f"Argument provided: {user_name}")
            rows = cur.execute(f"""
                Select 
                    r.RoleName,
                    r.CreatorName,
                    r.CreateTimeStamp,
                    Rm.Grantor,
                    Rm.WhenGranted,
                    Rm.DefaultRole,
                    Rm.WithAdmin
                FROM DBC.RoleInfoV r
                JOIN DBC.RoleMembersV Rm
                ON r.RoleName = Rm.RoleName
                WHERE r.RoleName LIKE  '%{user_name}%' (NOT CASESPECIFIC);""")

        data = rows_to_json(cur.description, rows.fetchall())
        metadata = {
            "tool_name": "sec_userRoles",
            "argument": user_name,
        }
        return create_response(data, metadata)

