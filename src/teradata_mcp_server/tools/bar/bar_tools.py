"""
BAR (Backup and Restore) Tools for Teradata DSA MCP Server

"""

import logging
import string
import json
from typing import Optional, List, Dict
import os

logger = logging.getLogger("teradata_mcp_server")

# Setup logging to file (always add file handler)
log_dir = os.path.join(os.path.dirname(__file__), '../../../logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'bar_tools.log')
file_handler = logging.FileHandler(log_file)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.setLevel(logging.DEBUG)
logger.info('Logging initialized to %s', log_file)
logger.info('TEST LOG ENTRY: bar_tools.py imported and logging is active.')

from teradata_mcp_server.tools.utils import create_response
from .dsa_client import dsa_client

logger = logging.getLogger("teradata_mcp_server")


#------------------ Disk File System Operations ------------------#

def list_disk_file_systems() -> str:
    """List all configured disk file systems in DSA
    
    Lists all disk file systems configured for backup operations, showing:
    - File system paths
    - Maximum files allowed per file system
    - Configuration status
    
    Returns:
        Formatted summary of all disk file systems with their configurations
    """
    try:
        logger.info("Listing disk file systems via DSA API")
        
        # Make request to DSA API
        response = dsa_client._make_request(
            method="GET",
            endpoint="dsa/components/backup-applications/disk-file-system"
        )
        
        logger.debug(f"DSA API response: {response}")
        
        results = []
        results.append("🗂️ DSA Disk File Systems")
        results.append("=" * 50)
        
        if response.get('status') == 'LIST_DISK_FILE_SYSTEMS_SUCCESSFUL':
            file_systems = response.get('fileSystems', [])
            
            if file_systems:
                results.append(f"📊 Total File Systems: {len(file_systems)}")
                results.append("")
                
                for i, fs in enumerate(file_systems, 1):
                    results.append(f"🗂️ File System #{i}")
                    results.append(f"   📁 Path: {fs.get('fileSystemPath', 'N/A')}")
                    results.append(f"   📄 Max Files: {fs.get('maxFiles', 'N/A')}")
                    results.append("")
            else:
                results.append("📋 No disk file systems configured")
                
            results.append("=" * 50)
            results.append(f"✅ Status: {response.get('status')}")
            results.append(f"🔍 Found Component: {response.get('foundComponent', False)}")
            results.append(f"✔️ Valid: {response.get('valid', False)}")
            
        else:
            results.append(f"❌ Failed to list disk file systems")
            results.append(f"📊 Status: {response.get('status', 'Unknown')}")
            if response.get('validationlist'):
                validation = response['validationlist']
                if validation.get('serverValidationList'):
                    for error in validation['serverValidationList']:
                        results.append(f"❌ Error: {error.get('message', 'Unknown error')}")
        
        return "\n".join(results)
        
    except Exception as e:
        logger.error(f"Failed to list disk file systems: {str(e)}")
        return f"❌ Error listing disk file systems: {str(e)}"


def config_disk_file_system(file_system_path: str, max_files: int) -> str:
    """Configure a disk file system for DSA backup operations
    
    Adds a new disk file system to the existing list or updates an existing one.
    This allows DSA to use the file system for backup storage operations.
    
    Args:
        file_system_path: Full path to the file system directory (e.g., "/var/opt/teradata/backup")
        max_files: Maximum number of files allowed in this file system (must be > 0)
        
    Returns:
        Formatted result of the configuration operation with status and any validation messages
    """
    try:
        logger.info(f"Configuring disk file system: {file_system_path} with max files: {max_files}")
        
        # First, get the existing file systems
        try:
            existing_response = dsa_client._make_request(
                method="GET",
                endpoint="dsa/components/backup-applications/disk-file-system"
            )
            
            existing_file_systems = []
            if existing_response.get('status') == 'LIST_DISK_FILE_SYSTEMS_SUCCESSFUL':
                existing_file_systems = existing_response.get('fileSystems', [])
                logger.info(f"Found {len(existing_file_systems)} existing file systems")
            else:
                logger.info("No existing file systems found or unable to retrieve them")
                
        except Exception as e:
            logger.warning(f"Could not retrieve existing file systems: {e}")
            existing_file_systems = []
        
        # Check if the new file system path already exists and update it, or add it
        file_systems_to_configure = []
        path_exists = False
        
        for fs in existing_file_systems:
            if fs.get('fileSystemPath') == file_system_path:
                # Update existing file system
                file_systems_to_configure.append({
                    "fileSystemPath": file_system_path,
                    "maxFiles": max_files
                })
                path_exists = True
                logger.info(f"Updating existing file system: {file_system_path}")
            else:
                # Keep existing file system unchanged
                file_systems_to_configure.append(fs)
        
        # If path doesn't exist, add the new file system
        if not path_exists:
            file_systems_to_configure.append({
                "fileSystemPath": file_system_path,
                "maxFiles": max_files
            })
            logger.info(f"Adding new file system: {file_system_path}")
        
        # Prepare request data with all file systems (existing + new/updated)
        request_data = {
            "fileSystems": file_systems_to_configure
        }
        
        logger.info(f"Configuring {len(file_systems_to_configure)} file systems total")
        
        # Make request to DSA API
        response = dsa_client._make_request(
            method="POST",
            endpoint="dsa/components/backup-applications/disk-file-system",
            data=request_data
        )
        
        logger.debug(f"DSA API response: {response}")
        
        results = []
        results.append("🗂️ DSA Disk File System Configuration")
        results.append("=" * 50)
        results.append(f"📁 File System Path: {file_system_path}")
        results.append(f"📄 Max Files: {max_files}")
        results.append(f"📊 Total File Systems: {len(file_systems_to_configure)}")
        results.append(f"🔄 Operation: {'Update' if path_exists else 'Add'}")
        results.append("")
        
        if response.get('status') == 'CONFIG_DISK_FILE_SYSTEM_SUCCESSFUL':
            results.append("✅ Disk file system configured successfully")
            results.append(f"📊 Status: {response.get('status')}")
            results.append(f"✔️ Valid: {response.get('valid', False)}")
            
        else:
            results.append("❌ Failed to configure disk file system")
            results.append(f"📊 Status: {response.get('status', 'Unknown')}")
            results.append(f"✔️ Valid: {response.get('valid', False)}")
            
            # Show validation errors if any
            if response.get('validationlist'):
                validation = response['validationlist']
                results.append("")
                results.append("🔍 Validation Details:")
                
                if validation.get('serverValidationList'):
                    for error in validation['serverValidationList']:
                        results.append(f"❌ Server Error: {error.get('message', 'Unknown error')}")
                        results.append(f"   Code: {error.get('code', 'N/A')}")
                        results.append(f"   Status: {error.get('valStatus', 'N/A')}")
                
                if validation.get('clientValidationList'):
                    for error in validation['clientValidationList']:
                        results.append(f"❌ Client Error: {error.get('message', 'Unknown error')}")
        
        results.append("")
        results.append("=" * 50)
        results.append("✅ Disk file system configuration operation completed")
        
        return "\n".join(results)
        
    except Exception as e:
        logger.error(f"Failed to configure disk file system: {str(e)}")
        return f"❌ Error configuring disk file system '{file_system_path}': {str(e)}"


def delete_disk_file_systems() -> str:
    """Delete all disk file system configurations from DSA
    
    Removes all disk file system configurations from DSA. This operation will fail
    if any file systems are currently in use by backup operations or file target groups.
    
    Returns:
        Formatted result of the deletion operation with status and any validation messages
        
    Warning:
        This operation removes ALL disk file system configurations. Make sure no
        backup operations or file target groups are using these file systems.
    """
    try:
        logger.info("Deleting all disk file system configurations via DSA API")
        
        # Make request to DSA API
        response = dsa_client._make_request(
            method="DELETE",
            endpoint="dsa/components/backup-applications/disk-file-system"
        )
        
        logger.debug(f"DSA API response: {response}")
        
        results = []
        results.append("🗂️ DSA Disk File System Deletion")
        results.append("=" * 50)
        
        if response.get('status') == 'DELETE_COMPONENT_SUCCESSFUL':
            results.append("✅ All disk file systems deleted successfully")
            results.append(f"📊 Status: {response.get('status')}")
            results.append(f"✔️ Valid: {response.get('valid', False)}")
            
        else:
            results.append("❌ Failed to delete disk file systems")
            results.append(f"📊 Status: {response.get('status', 'Unknown')}")
            results.append(f"✔️ Valid: {response.get('valid', False)}")
            
            # Show validation errors if any
            if response.get('validationlist'):
                validation = response['validationlist']
                results.append("")
                results.append("🔍 Validation Details:")
                
                if validation.get('serverValidationList'):
                    for error in validation['serverValidationList']:
                        results.append(f"❌ Server Error: {error.get('message', 'Unknown error')}")
                        results.append(f"   Code: {error.get('code', 'N/A')}")
                        results.append(f"   Status: {error.get('valStatus', 'N/A')}")
                
                if validation.get('clientValidationList'):
                    for error in validation['clientValidationList']:
                        results.append(f"❌ Client Error: {error.get('message', 'Unknown error')}")
                
                # If deletion failed due to dependencies, provide guidance
                if any('in use by' in error.get('message', '') for error in validation.get('serverValidationList', [])):
                    results.append("")
                    results.append("💡 Helpful Notes:")
                    results.append("   • Remove all backup jobs using these file systems first")
                    results.append("   • Delete any file target groups that reference these file systems")
                    results.append("   • Use list_disk_file_systems() to see current configurations")
        
        results.append("")
        results.append("=" * 50)
        results.append("✅ Disk file system deletion operation completed")
        
        return "\n".join(results)
        
    except Exception as e:
        logger.error(f"Failed to delete disk file systems: {str(e)}")
        return f"❌ Error deleting disk file systems: {str(e)}"


def remove_disk_file_system(file_system_path: str) -> str:
    """Remove a specific disk file system from DSA configuration
    
    Removes a specific disk file system from the existing list by reconfiguring
    the remaining file systems. This operation will fail if the file system is
    currently in use by backup operations or file target groups.
    
    Args:
        file_system_path: Full path to the file system directory to remove (e.g., "/var/opt/teradata/backup")
        
    Returns:
        Formatted result of the removal operation with status and any validation messages
        
    Warning:
        This operation will fail if the file system is in use by any backup operations
        or file target groups. Remove those dependencies first.
    """
    try:
        logger.info(f"Removing disk file system: {file_system_path}")
        
        # First, get the existing file systems
        try:
            existing_response = dsa_client._make_request(
                method="GET",
                endpoint="dsa/components/backup-applications/disk-file-system"
            )
            
            existing_file_systems = []
            if existing_response.get('status') == 'LIST_DISK_FILE_SYSTEMS_SUCCESSFUL':
                existing_file_systems = existing_response.get('fileSystems', [])
                logger.info(f"Found {len(existing_file_systems)} existing file systems")
            else:
                logger.warning("No existing file systems found or unable to retrieve them")
                return f"❌ Could not retrieve existing file systems to remove '{file_system_path}'"
                
        except Exception as e:
            logger.error(f"Could not retrieve existing file systems: {e}")
            return f"❌ Error retrieving existing file systems: {str(e)}"
        
        # Check if the file system to remove exists
        path_exists = False
        file_systems_to_keep = []
        
        for fs in existing_file_systems:
            if fs.get('fileSystemPath') == file_system_path:
                path_exists = True
                logger.info(f"Found file system to remove: {file_system_path}")
            else:
                # Keep this file system
                file_systems_to_keep.append(fs)
        
        # If path doesn't exist, return error
        if not path_exists:
            available_paths = [fs.get('fileSystemPath', 'N/A') for fs in existing_file_systems]
            results = []
            results.append("🗂️ DSA Disk File System Removal")
            results.append("=" * 50)
            results.append(f"❌ File system '{file_system_path}' not found")
            results.append("")
            results.append("📋 Available file systems:")
            if available_paths:
                for path in available_paths:
                    results.append(f"   • {path}")
            else:
                results.append("   (No file systems configured)")
            results.append("")
            results.append("=" * 50)
            return "\n".join(results)
        
        # Prepare request data with remaining file systems
        request_data = {
            "fileSystems": file_systems_to_keep
        }
        
        logger.info(f"Removing '{file_system_path}', keeping {len(file_systems_to_keep)} file systems")
        
        # Make request to DSA API to reconfigure with remaining file systems
        response = dsa_client._make_request(
            method="POST",
            endpoint="dsa/components/backup-applications/disk-file-system",
            data=request_data
        )
        
        logger.debug(f"DSA API response: {response}")
        
        results = []
        results.append("🗂️ DSA Disk File System Removal")
        results.append("=" * 50)
        results.append(f"📁 Removed File System: {file_system_path}")
        results.append(f"📊 Remaining File Systems: {len(file_systems_to_keep)}")
        results.append("")
        
        if response.get('status') == 'CONFIG_DISK_FILE_SYSTEM_SUCCESSFUL':
            results.append("✅ Disk file system removed successfully")
            results.append(f"📊 Status: {response.get('status')}")
            results.append(f"✔️ Valid: {response.get('valid', False)}")
            
            if file_systems_to_keep:
                results.append("")
                results.append("📋 Remaining file systems:")
                for fs in file_systems_to_keep:
                    path = fs.get('fileSystemPath', 'N/A')
                    max_files = fs.get('maxFiles', 'N/A')
                    results.append(f"   • {path} (Max Files: {max_files})")
            else:
                results.append("")
                results.append("📋 No file systems remaining (all removed)")
            
        else:
            results.append("❌ Failed to remove disk file system")
            results.append(f"📊 Status: {response.get('status', 'Unknown')}")
            results.append(f"✔️ Valid: {response.get('valid', False)}")
            
            # Show validation errors if any
            if response.get('validationlist'):
                validation = response['validationlist']
                results.append("")
                results.append("🔍 Validation Details:")
                
                if validation.get('serverValidationList'):
                    for error in validation['serverValidationList']:
                        results.append(f"❌ Server Error: {error.get('message', 'Unknown error')}")
                        results.append(f"   Code: {error.get('code', 'N/A')}")
                        results.append(f"   Status: {error.get('valStatus', 'N/A')}")
                
                if validation.get('clientValidationList'):
                    for error in validation['clientValidationList']:
                        results.append(f"❌ Client Error: {error.get('message', 'Unknown error')}")
        
        results.append("")
        results.append("=" * 50)
        results.append("✅ Disk file system removal operation completed")
        
        return "\n".join(results)
        
    except Exception as e:
        logger.error(f"Failed to remove disk file system: {str(e)}")
        return f"❌ Error removing disk file system '{file_system_path}': {str(e)}"


def manage_dsa_disk_file_systems(
    operation: str,
    file_system_path: Optional[str] = None,
    max_files: Optional[int] = None
) -> str:
    """Unified DSA Disk File System Management Tool
    
    This comprehensive tool handles all DSA disk file system operations including
    listing, configuring, and removing file system configurations.
    
    Args:
        operation: The operation to perform
        file_system_path: Path to the file system (for config and remove operations)
        max_files: Maximum number of files allowed (for config operation)
    
    Available Operations:
        - "list" - List all configured disk file systems
        - "config" - Configure a new disk file system
        - "delete_all" - Remove all file system configurations
        - "remove" - Remove a specific file system configuration
    
    Returns:
        Result of the requested operation
    """
    
    logger.info(f"DSA Disk File System Management - Operation: {operation}")
    
    try:
        # List operation
        if operation == "list":
            return list_disk_file_systems()
            
        # Config operation
        elif operation == "config":
            if not file_system_path:
                return "❌ Error: file_system_path is required for config operation"
            if max_files is None:
                return "❌ Error: max_files is required for config operation"
            return config_disk_file_system(file_system_path, max_files)
            
        # Delete all operation
        elif operation == "delete_all":
            return delete_disk_file_systems()
            
        # Remove specific operation
        elif operation == "remove":
            if not file_system_path:
                return "❌ Error: file_system_path is required for remove operation"
            return remove_disk_file_system(file_system_path)
            
        else:
            available_operations = [
                "list", "config", "delete_all", "remove"
            ]
            return f"❌ Error: Unknown operation '{operation}'. Available operations: {', '.join(available_operations)}"
            
    except Exception as e:
        logger.error(f"DSA Disk File System Management error - Operation: {operation}, Error: {str(e)}")
        return f"❌ Error during {operation}: {str(e)}"


""" 
#PA255044 ->  START -- AWS S3 Configuration Tool
""" 
#------------------ AWS S3 Backup Solution Configuration and Operations ------------------#


def list_aws_s3_backup_configurations () -> str:
    """List the configured AWS S3 object store systems in DSA
    
    Lists all configured AWS S3 storage target systems that are currently available configured for the backup operations, showing:
    - Bucket names
    - Prefix numbers, names and devices configured
    - Configuration status
    
    Returns:
        Formatted summary of all S3 file systems with their configurations
    """
    
    try:
        logger.info("Listing AWS S3 target systems via DSA API")

        # Make request to DSA API
        response = dsa_client._make_request(
            method="GET",
            endpoint="dsa/components/backup-applications/aws-s3"
        )
        
        # Add debug log for full API response
        logger.debug("[DEBUG] Full DSA API response from aws-s3 endpoint: %r", response)
        
        # Temporary debug output to console for investigation
        print(f"[DEBUG] AWS LIST API RESPONSE:")
        print(f"Status: {response.get('status')}")
        print(f"AWS list length: {len(response.get('aws', []))}")
        print(f"Full aws list: {response.get('aws', [])}")
        print("=" * 80)
        
        results = []
        results.append("🗂️ DSA AWS S3 Backup Solution Systems Available")
        results.append("=" * 50)
        
        if response.get('status') == 'LIST_AWS_APP_SUCCESSFUL':
            # Extract all AWS configurations from the aws list
            aws_list = response.get('aws', [])
            
            total_configurations = 0
            total_buckets = 0
            
            if aws_list and isinstance(aws_list, list):
                total_configurations = len(aws_list)
                results.append(f"📊 Total AWS S3 Configurations: {total_configurations}")
                results.append("")
                
                # Process each AWS configuration
                for config_idx, aws_config in enumerate(aws_list, 1):
                    configAwsRest = aws_config.get('configAwsRest', {})
                    account_name = configAwsRest.get('acctName', 'N/A')
                    access_id = configAwsRest.get('accessId', 'N/A')
                    
                    results.append(f"🔧 AWS Configuration #{config_idx}")
                    results.append(f"   📋 Account Name: {account_name}")
                    results.append(f"   🔑 Access ID: {access_id}")
                    
                    bucketsByRegion = configAwsRest.get('bucketsByRegion', [])
                    
                    # Handle if bucketsByRegion is a dict (single region) or list
                    if isinstance(bucketsByRegion, dict):
                        bucketsByRegion = [bucketsByRegion]

                    config_bucket_count = 0
                    if bucketsByRegion:
                        for i, region in enumerate(bucketsByRegion, 1):
                            region_name = region.get('region', 'N/A')
                            results.append(f"   🗂️ Region #{i}: {region_name}")
                            buckets = region.get('buckets', [])
                            if isinstance(buckets, dict):
                                buckets = [buckets]
                            if buckets:
                                for j, bucket in enumerate(buckets, 1):
                                    config_bucket_count += 1
                                    total_buckets += 1
                                    bucket_name = bucket.get('bucketName', 'N/A')
                                    results.append(f"      📁 Bucket #{j}: {bucket_name}")
                                    prefix_list = bucket.get('prefixList', [])
                                    if isinstance(prefix_list, dict):
                                        prefix_list = [prefix_list]
                                    if prefix_list:
                                        for k, prefix in enumerate(prefix_list, 1):
                                            prefix_name = prefix.get('prefixName', 'N/A')
                                            storage_devices = prefix.get('storageDevices', 'N/A')
                                            results.append(f"         🔖 Prefix #{k}: {prefix_name}")
                                            results.append(f"            Storage Devices: {storage_devices}")
                                    else:
                                        results.append(f"         🔖 No prefixes configured")
                            else:
                                results.append(f"      📁 No buckets configured in this region")
                    else:
                        results.append("      📋 No regions configured for this account")
                    
                    results.append("")
                
                # Update the total bucket count
                results[1] = f"📊 Total Buckets Configured: {total_buckets}"
            else:
                results.append("📋 No AWS backup Solutions Configured")

            results.append("=" * 50)
            results.append(f"✅ Status: {response.get('status')}")
            results.append(f"🔍 Found Component: {response.get('foundComponent', False)}")
            results.append(f"✔️ Valid: {response.get('valid', False)}")
            
        else:
            results.append(f"❌ Failed to list AWS S3 Backup Solutions Configured")
            results.append(f"📊 Status: {response.get('status', 'Unknown')}")
            if response.get('validationlist'):
                validation = response['validationlist']
                if validation.get('serverValidationList'):
                    for error in validation['serverValidationList']:
                        results.append(f"❌ Error: {error.get('message', 'Unknown error')}")
        
        return "\n".join(results)
        
    except Exception as e:
        logger.error(f"Failed to list AWS S3 Backup Solutions Configured: {str(e)}")
        return f"❌ Error listing AWS S3 Backup Solutions Configured: {str(e)}"


def delete_aws_s3_backup_configurations() -> str:
    """Delete all AWS S3 backup configurations from DSA
    
    Removes all AWS S3 backup solution configurations from DSA. This operation will fail
    if any S3 configurations are currently in use by backup operations or target groups.
    
    Returns:
        Formatted result of the deletion operation with status and any validation messages
        
    Warning:
        This operation removes ALL AWS S3 backup configurations. Make sure no
        backup operations or target groups are using these configurations.
    """
    try:
        logger.info("Deleting all AWS S3 backup configurations via DSA API")
        
        # Make request to DSA API
        response = dsa_client._make_request(
            method="DELETE",
            endpoint="dsa/components/backup-applications/aws-s3"
        )
        
        logger.debug(f"DSA API response: {response}")
        
        results = []
        results.append("🗂️ DSA AWS S3 Backup Configuration Deletion")
        results.append("=" * 50)
        
        if response.get('status') == 'DELETE_COMPONENT_SUCCESSFUL':
            results.append("✅ All AWS S3 backup configurations deleted successfully")
            results.append(f"📊 Status: {response.get('status')}")
            results.append(f"✔️ Valid: {response.get('valid', False)}")
            
        else:
            results.append("❌ Failed to delete AWS S3 backup configurations")
            results.append(f"📊 Status: {response.get('status', 'Unknown')}")
            results.append(f"✔️ Valid: {response.get('valid', False)}")
            
            # Show validation errors if any
            if response.get('validationlist'):
                validation = response['validationlist']
                results.append("")
                results.append("🔍 Validation Details:")
                
                if validation.get('serverValidationList'):
                    for error in validation['serverValidationList']:
                        results.append(f"❌ Server Error: {error.get('message', 'Unknown error')}")
                        results.append(f"   Code: {error.get('code', 'N/A')}")
                        results.append(f"   Status: {error.get('valStatus', 'N/A')}")
                
                if validation.get('clientValidationList'):
                    for error in validation['clientValidationList']:
                        results.append(f"❌ Client Error: {error.get('message', 'Unknown error')}")
                
                # If deletion failed due to dependencies, provide guidance
                if any('in use by' in error.get('message', '') for error in validation.get('serverValidationList', [])):
                    results.append("")
                    results.append("💡 Helpful Notes:")
                    results.append("   • Remove all backup jobs using these AWS S3 configurations first")
                    results.append("   • Delete any target groups that reference these S3 configurations")
                    results.append("   • Use list_aws_s3_backup_configurations() to see current configurations")
        
        results.append("")
        results.append("=" * 50)
        results.append("✅ AWS S3 backup configuration deletion operation completed")
        
        return "\n".join(results)
        
    except Exception as e:
        logger.error(f"Failed to delete AWS S3 backup configurations: {str(e)}")
        return f"❌ Error deleting AWS S3 backup configurations: {str(e)}"



def remove_AWS_S3_backup_configuration(aws_acct_name: str) -> str:
    """Remove a specific AWS S3 configuration from DSA

    Removes a specific AWS S3 configuration from the existing list by reconfiguring
    the remaining S3 configurations. This operation will fail if the S3 configuration is
    currently in use by backup operations or S3 target groups.
    
    Args:
        aws_acct_name : Name of the AWS S3 account for which the configuration needs to be removed from DSA (e.g., "/var/opt/teradata/backup")
        
    Returns:
        Formatted result of the removal operation with status and any validation messages
        
    Warning:
        This operation will fail if the AWS S3 config is in use by any backup operations
        or target groups. Remove those dependencies first.
    """
    try:
        logger.info(f"Removing AWS S3 configuration: {aws_acct_name}")

        # Prepare request data with aws_acct_name as that is the input for the 
        request_data = aws_acct_name
        
        # First, get the existing S3 configurations
        try:
            existing_response = dsa_client._make_request(
                method="GET",
                endpoint="dsa/components/backup-applications/aws-s3"
            )

            existing_s3_configurations = []
            if existing_response.get('status') == 'LIST_AWS_APP_SUCCESSFUL':
                # Use the exact same logic as the list function
                aws_list = existing_response.get('aws', [])
                logger.debug(f"AWS list from API: {aws_list}")
                logger.debug(f"AWS list type: {type(aws_list)}, length: {len(aws_list) if aws_list else 0}")
                if aws_list and isinstance(aws_list, list):
                    # For consistency with list function, treat each aws entry as a configuration
                    existing_s3_configurations = aws_list
                    logger.info(f"Successfully parsed {len(existing_s3_configurations)} S3 configurations")
                else:
                    logger.warning(f"No aws list found or wrong type. aws_list: {aws_list}")
            else:
                logger.warning("No existing S3 configurations found or unable to retrieve them")
                logger.debug(f"API response status: {existing_response.get('status')}")
                return f"❌ Could not retrieve existing S3 configurations to remove '{aws_acct_name}'"

        except Exception as e:
            logger.error(f"Could not retrieve existing S3 configurations: {e}")
            return f"❌ Error retrieving existing S3 configurations: {str(e)}"

        # Check if the S3 configuration to remove, actually exists or not
        s3config_exists = False
        s3_configurations_to_keep = []

        for s3 in existing_s3_configurations:
            # Extract account name from the nested structure
            config_aws_rest = s3.get('configAwsRest', {})
            current_acct_name = config_aws_rest.get('acctName', '')
            
            logger.debug(f"Checking S3 config - current_acct_name: '{current_acct_name}', target: '{aws_acct_name}'")
            if current_acct_name == aws_acct_name:
                s3config_exists = True
                logger.info(f"Found S3 configuration to remove: {aws_acct_name}")
            else:
                # Keep this S3 configuration
                s3_configurations_to_keep.append(s3)
        
        # If S3 config doesn't exist, return error
        if not s3config_exists:
            available_s3_configs = []
            debug_info = []
            for i, s3 in enumerate(existing_s3_configurations):
                config_aws_rest = s3.get('configAwsRest', {})
                acct_name = config_aws_rest.get('acctName', 'N/A')
                
                # Also collect bucket names as potential identifiers
                bucket_names = []
                buckets_by_region = config_aws_rest.get('bucketsByRegion', [])
                if isinstance(buckets_by_region, dict):
                    buckets_by_region = [buckets_by_region]
                for region in buckets_by_region:
                    buckets = region.get('buckets', [])
                    if isinstance(buckets, dict):
                        buckets = [buckets]
                    for bucket in buckets:
                        bucket_name = bucket.get('bucketName', '')
                        if bucket_name:
                            bucket_names.append(bucket_name)
                
                available_s3_configs.append(acct_name)
                # Add debug info about the structure - show all possible account fields
                debug_info.append(f"Config #{i+1}: Top level keys: {list(s3.keys())}")
                debug_info.append(f"   configAwsRest keys: {list(config_aws_rest.keys())}")
                debug_info.append(f"   Bucket names: {bucket_names}")
                # Look for any field that might contain account info
                for key, value in config_aws_rest.items():
                    if 'acc' in key.lower() or 'name' in key.lower() or 'id' in key.lower():
                        debug_info.append(f"   {key}: {value}")
            results = []
            results.append("🗂️ DSA S3 Configuration Removal")
            results.append("=" * 50)
            results.append(f"❌ S3 configuration '{aws_acct_name}' not found")
            results.append("")
            results.append("📋 Available S3 configurations:")
            if available_s3_configs:
                for path in available_s3_configs:
                    results.append(f"   • {path}")
            else:
                results.append("   (No S3 configurations configured)")
            results.append("")
            results.append("🔍 Debug Info:")
            for debug in debug_info:
                results.append(f"   {debug}")
            results.append("")
            results.append("=" * 50)
            return "\n".join(results)

        logger.info(f"Removing '{aws_acct_name}', keeping {len(s3_configurations_to_keep)} S3 configurations")

        # this code logic is not required. If the account is found, we can just delete it, do not complicate with reconfiguring the rest
        # reconfiguring the rest is not going to work in the single call to the API
        # Make request to DSA API to reconfigure with remaining S3 configurations
        # If no configurations remain, we need to delete all instead of posting empty config
        #if not s3_configurations_to_keep:
        #    logger.info("No S3 configurations remaining, deleting all S3 configurations")
        #    response = dsa_client._make_request(
        #        method="DELETE",
        #        endpoint="dsa/components/backup-applications/aws-s3"
        #    )
        #else:
        #    logger.info(f"Reconfiguring with {len(s3_configurations_to_keep)} remaining S3 configurations")
        #    response = dsa_client._make_request(
        #       method="POST",
        #        endpoint="dsa/components/backup-applications/aws-s3",
        #        data=request_data
        #    )

 
            
        # Build the request data and delete the specific configuration that is already found to be existing
        # Use the correct endpoint with account name and trailing slash (matching successful Swagger call)
        response = dsa_client._make_request(
                method="DELETE",
                endpoint=f"dsa/components/backup-applications/aws-s3/{aws_acct_name}/"
        )

        logger.debug(f"DSA API response: {response}")

        results = []
        results.append("🗂️ DSA S3 Configuration Removal")
        results.append("=" * 50)
        results.append(f"📁 Removed S3 Configuration: {aws_acct_name}")
        results.append(f"📊 Remaining S3 Configurations: {len(s3_configurations_to_keep)}")
        results.append("")

        success_statuses = ['CONFIG_AWS_APP_SUCCESSFUL', 'LIST_AWS_APP_SUCCESSFUL', 'DELETE_COMPONENT_SUCCESSFUL']
        if response.get('status') in success_statuses:
            results.append("✅ AWS S3 configuration removed successfully")
            results.append(f"📊 Status: {response.get('status')}")
            results.append(f"✔️ Valid: {response.get('valid', False)}")

            if s3_configurations_to_keep:
                results.append("")
                results.append("📋 Remaining S3 configurations:")
                for s3 in s3_configurations_to_keep:
                    config_aws_rest = s3.get('configAwsRest', {})
                    acct_name = config_aws_rest.get('acctName', 'N/A')
                    results.append(f"   • {acct_name}")
            else:
                results.append("")
                results.append("📋 No S3 configurations remaining (all removed)")

        else:
            results.append("❌ Failed to remove AWS S3 configuration")
            results.append(f"📊 Status: {response.get('status', 'Unknown')}")
            results.append(f"✔️ Valid: {response.get('valid', False)}")

            # Show validation errors if any
            if response.get('validationlist'):
                validation = response['validationlist']
                results.append("")
                results.append("🔍 Validation Details:")

                if validation.get('serverValidationList'):
                    for error in validation['serverValidationList']:
                        results.append(f"❌ Server Error: {error.get('message', 'Unknown error')}")
                        results.append(f"   Code: {error.get('code', 'N/A')}")
                        results.append(f"   Status: {error.get('valStatus', 'N/A')}")

                if validation.get('clientValidationList'):
                    for error in validation['clientValidationList']:
                        results.append(f"❌ Client Error: {error.get('message', 'Unknown error')}")

        results.append("")
        results.append("=" * 50)
        results.append("✅ AWS S3 backup configuration removal operation completed")
        
        return "\n".join(results)
        
    except Exception as e:
        logger.error(f"Failed to remove AWS S3 configuration: {str(e)}")
        return f"❌ Error removing AWS S3 configuration '{aws_acct_name}': {str(e)}"
    

def manage_AWS_S3_backup_configurations(
    operation: str,
    accessId: Optional[str] = None,
    accessKey: Optional[str] = None,
    bucketsByRegion: Optional[object] = None,
    bucketName: Optional[str] = None,
    prefixName: Optional[str] = "dsa-backup",
    storageDevices: Optional[int] = 4,
    acctName: Optional[str] = None
) -> str:
    """Unified DSA AWS S3 Backup Configuration Management Tool

    This comprehensive tool handles all DSA AWS S3 backup configuration operations including
    listing, configuring, and removing backup configurations.
    
    Args:
        operation: The operation to perform
        accessId: AWS Access ID
        accessKey: AWS Access Key
        bucketsByRegion: Buckets by region configuration (object: dict or list)
        bucketName: AWS Bucket Name
        prefixName: AWS S3 Prefix Name
        storageDevices: Storage devices to use (default 4)
        acctName: AWS Account Name
    
    Available Operations:
        - "list" - List all configured AWS S3 backup solutions
        - "config" - Configure a new AWS S3 backup solution
        - "delete_all" - Remove all AWS S3 backup solution configurations
        - "remove" - Remove a specific AWS S3 backup solution configuration

    Returns:
        Result of the requested operation
    """

    logger.info(f"DSA AWS S3 Backup Solution Management - Operation: {operation}")
    
    try:
        # List operation
        if operation == "list":
            return list_aws_s3_backup_configurations()
        # Config operation
       # Config operation
        elif operation == "config":
            if not accessId:
                return "❌ Error: accessId is required for config operation"
            if not accessKey:
                return "❌ Error: accessKey is required for config operation"
            if not bucketsByRegion:
                return "❌ Error: bucketsByRegion is required for config operation"
            if not bucketName:
                return "❌ Error: bucketName is required for config operation"
            if not prefixName:
                return "❌ Error: prefixName is required for config operation"
            # Validate storageDevices as integer
            if not storageDevices or not isinstance(storageDevices, int) or storageDevices <= 0:
                return "❌ Error: storageDevices must be a positive integer for config operation"
            if not acctName:
                return "❌ Error: acctName is required for config operation"
            
            # Transform bucketsByRegion to match API expectations
            formatted_buckets_by_region = []


            # Debug information
            debug_msg = f"Original bucketsByRegion: type={type(bucketsByRegion)}, value={bucketsByRegion}"
            
            if isinstance(bucketsByRegion, list):
                # Handle if it's a simple list of regions like ["us-west-2"]
                if bucketsByRegion and isinstance(bucketsByRegion[0], str):
                    # Convert simple region string to proper structure
                    region_name = bucketsByRegion[0]
                    formatted_buckets_by_region = [{
                        "region": region_name,
                        "buckets": [{
                            "bucketName": bucketName,
                            "prefixList": [{
                                "prefixName": prefixName,
                                "storageDevices": storageDevices,
                                "prefixId": 0
                            }]
                        }]
                    }]
                    debug_msg += f" | Converted to: {formatted_buckets_by_region}"
                else:
                    # Assume it's already properly formatted
                    formatted_buckets_by_region = bucketsByRegion
                    debug_msg += " | Used as-is (already formatted)"
            elif isinstance(bucketsByRegion, dict):
                # Handle if it's a single region object
                formatted_buckets_by_region = [bucketsByRegion]
                debug_msg += f" | Wrapped dict in list: {formatted_buckets_by_region}"
            else:
                return f"❌ Error: bucketsByRegion must be a list or dict, got {type(bucketsByRegion)} | {debug_msg}"

            # bucketsByRegion is now expected as an object (dict or list)
            request_data = {
                "configAwsRest": {
                    "accessId": accessId,
                    "accessKey": accessKey,
                    "bucketsByRegion": formatted_buckets_by_region,
                    "acctName": acctName,
                    "viewpoint": True,
                    "viewpointBucketRegion": True
                }
            }

            # Debug: return debug info for testing
            debug_info = f"DEBUG INFO:\n{debug_msg}\nFormatted structure: {formatted_buckets_by_region}\nFull request data: {request_data}"

            try:
                response = dsa_client._make_request(
                    method="POST",
                    endpoint="dsa/components/backup-applications/aws-s3",
                    data=request_data
                )
                return f"✅ AWS backup solution configuration operation completed\nResponse: {response}\n\n{debug_info}"
            except Exception as e:
                return f"❌ Error configuring AWS backup solution: {str(e)}\n\n{debug_info}"

        # Delete all operation
        elif operation == "delete_all":
            return delete_aws_s3_backup_configurations()
        # Remove specific operation
        elif operation == "remove":
            if not acctName:
                return "❌ Error: acctName is required for remove operation"
            return remove_AWS_S3_backup_configuration(acctName)
        else:
            available_operations = [
                "list", "config", "delete_all", "remove"
            ]
            return f"❌ Error: Unknown operation '{operation}'. Available operations: {', '.join(available_operations)}"
    except Exception as e:
        logger.error(f"DSA AWS S3 Configuration Management error - Operation: {operation}, Error: {str(e)}")
        return f"❌ Error during {operation}: {str(e)}"


#------------------ Media Server Operations ------------------#

def manage_dsa_media_servers(
    operation: str,
    server_name: Optional[str] = None,
    port: Optional[int] = None,
    ip_addresses: Optional[str] = None,
    pool_shared_pipes: Optional[int] = 50,
    virtual: Optional[bool] = False
) -> str:
    """Unified media server management for all media server operations
    
    This comprehensive function handles all media server operations in the DSA system,
    including listing, getting details, adding, deleting, and managing consumers.
    """
    # Validate operation
    valid_operations = [
        "list", "get", "add", "delete", 
        "list_consumers", "list_consumers_by_server"
    ]
    
    if operation not in valid_operations:
        return f"❌ Invalid operation '{operation}'. Valid operations: {', '.join(valid_operations)}"
    
    try:
        # Route to the appropriate operation
        if operation == "list":
            return _list_media_servers()
        
        elif operation == "get":
            if not server_name:
                return "❌ server_name is required for 'get' operation"
            return _get_media_server(server_name)
        
        elif operation == "add":
            if not server_name:
                return "❌ server_name is required for 'add' operation"
            if not port:
                return "❌ port is required for 'add' operation"
            if not ip_addresses:
                return "❌ ip_addresses is required for 'add' operation"
            
            try:
                import json
                ip_list = json.loads(ip_addresses)
                return _add_media_server(server_name, port, ip_list, pool_shared_pipes or 50)
            except json.JSONDecodeError as e:
                return f"❌ Invalid IP addresses format: {str(e)}\nExpected JSON format: '[{{\"ipAddress\": \"IP\", \"netmask\": \"MASK\"}}]'"
        
        elif operation == "delete":
            if not server_name:
                return "❌ server_name is required for 'delete' operation"
            return _delete_media_server(server_name, virtual or False)
        
        elif operation == "list_consumers":
            return _list_media_server_consumers()
        
        elif operation == "list_consumers_by_server":
            if not server_name:
                return "❌ server_name is required for 'list_consumers_by_server' operation"
            return _list_media_server_consumers_by_name(server_name)
    
    except Exception as e:
        logger.error(f"Failed to execute media server operation '{operation}': {str(e)}")
        return f"❌ Error executing media server operation '{operation}': {str(e)}"


def _list_media_servers() -> str:
    """List all media servers from the DSA system"""
    try:
        # Make request to list media servers
        response = dsa_client._make_request("GET", "dsa/components/mediaservers")
        
        if not response.get("valid", False):
            error_messages = []
            validation_list = response.get("validationlist", {})
            if validation_list:
                client_errors = validation_list.get("clientValidationList", [])
                server_errors = validation_list.get("serverValidationList", [])
                
                for error in client_errors + server_errors:
                    error_messages.append(f"Code {error.get('code', 'N/A')}: {error.get('message', 'Unknown error')}")
            
            if error_messages:
                return f"❌ Failed to list media servers:\n" + "\n".join(error_messages)
            else:
                return f"❌ Failed to list media servers: {response.get('status', 'Unknown error')}"
        
        # Return the full response for complete transparency
        return json.dumps(response, indent=2)
        
    except Exception as e:
        logger.error(f"Failed to list media servers: {str(e)}")
        return f"❌ Error listing media servers: {str(e)}"


def _get_media_server(server_name: str) -> str:
    """Get details of a specific media server by name"""
    try:
        # Make request to get specific media server
        endpoint = f"dsa/components/mediaservers/{server_name}"
        response = dsa_client._make_request("GET", endpoint)
        
        if not response.get("valid", False):
            error_messages = []
            validation_list = response.get("validationlist", {})
            if validation_list:
                client_errors = validation_list.get("clientValidationList", [])
                server_errors = validation_list.get("serverValidationList", [])
                
                for error in client_errors + server_errors:
                    error_messages.append(f"Code {error.get('code', 'N/A')}: {error.get('message', 'Unknown error')}")
            
            if error_messages:
                return f"❌ Failed to get media server '{server_name}':\n" + "\n".join(error_messages)
            else:
                return f"❌ Failed to get media server '{server_name}': {response.get('status', 'Unknown error')}"
        
        # Return the full response for complete transparency
        return json.dumps(response, indent=2)
        
    except Exception as e:
        logger.error(f"Failed to get media server '{server_name}': {str(e)}")
        return f"❌ Error getting media server '{server_name}': {str(e)}"


def _add_media_server(
    server_name: str,
    port: int,
    ip_list: List[Dict[str, str]],
    pool_shared_pipes: int = 50
) -> str:
    """Add a new media server to the DSA system"""
    try:
        # Validate inputs
        if not server_name or not server_name.strip():
            return "❌ Server name is required and cannot be empty"
        
        if not (1 <= port <= 65535):
            return f"❌ Port must be between 1 and 65535"
        
        if not ip_list or not isinstance(ip_list, list):
            return "❌ At least one IP address is required"
        
        # Validate IP addresses format
        for ip_info in ip_list:
            if not isinstance(ip_info, dict) or 'ipAddress' not in ip_info or 'netmask' not in ip_info:
                return "❌ Each IP address must be a dictionary with 'ipAddress' and 'netmask' keys"
        
        # Prepare request payload
        payload = {
            "serverName": server_name.strip(),
            "port": port,
            "ipInfo": ip_list
        }
        
        # Make request to add media server
        response = dsa_client._make_request(
            "POST", 
            "dsa/components/mediaservers", 
            data=payload,
            headers={"Content-Type": "application/json", "Accept": "*/*"}
        )
        
        if not response.get("valid", False):
            error_messages = []
            validation_list = response.get("validationlist", {})
            if validation_list:
                client_errors = validation_list.get("clientValidationList", [])
                server_errors = validation_list.get("serverValidationList", [])
                
                for error in client_errors + server_errors:
                    error_messages.append(f"Code {error.get('code', 'N/A')}: {error.get('message', 'Unknown error')}")
            
            if error_messages:
                return f"❌ Failed to add media server '{server_name}':\n" + "\n".join(error_messages)
            else:
                return f"❌ Failed to add media server '{server_name}': {response.get('status', 'Unknown error')}"
        
        # Return the full response for complete transparency
        return json.dumps(response, indent=2)
        
    except Exception as e:
        logger.error(f"Failed to add media server '{server_name}': {str(e)}")
        return f"❌ Error adding media server '{server_name}': {str(e)}"


def _delete_media_server(server_name: str, virtual: bool = False) -> str:
    """Delete a media server from the DSA system"""
    try:
        # Prepare request parameters
        params = {}
        if virtual:
            params["virtual"] = "true"
        
        # Make request to delete media server
        endpoint = f"dsa/components/mediaservers/{server_name}"
        response = dsa_client._make_request("DELETE", endpoint, params=params)
        
        if not response.get("valid", False):
            error_messages = []
            validation_list = response.get("validationlist", {})
            if validation_list:
                client_errors = validation_list.get("clientValidationList", [])
                server_errors = validation_list.get("serverValidationList", [])
                
                for error in client_errors + server_errors:
                    error_messages.append(f"Code {error.get('code', 'N/A')}: {error.get('message', 'Unknown error')}")
            
            if error_messages:
                return f"❌ Failed to delete media server '{server_name}':\n" + "\n".join(error_messages)
            else:
                return f"❌ Failed to delete media server '{server_name}': {response.get('status', 'Unknown error')}"
        
        # Return the full response for complete transparency
        return json.dumps(response, indent=2)
        
    except Exception as e:
        logger.error(f"Failed to delete media server '{server_name}': {str(e)}")
        return f"❌ Error deleting media server '{server_name}': {str(e)}"


def _list_media_server_consumers() -> str:
    """List all media server consumers from the DSA system"""
    try:
        # Make request to list media server consumers
        response = dsa_client._make_request("GET", "dsa/components/mediaservers/listconsumers")
        
        if not response.get("valid", False):
            error_messages = []
            validation_list = response.get("validationlist", {})
            if validation_list:
                client_errors = validation_list.get("clientValidationList", [])
                server_errors = validation_list.get("serverValidationList", [])
                
                for error in client_errors + server_errors:
                    error_messages.append(f"Code {error.get('code', 'N/A')}: {error.get('message', 'Unknown error')}")
            
            if error_messages:
                return f"❌ Failed to list media server consumers:\n" + "\n".join(error_messages)
            else:
                return f"❌ Failed to list media server consumers: {response.get('status', 'Unknown error')}"
        
        # Return the full response for complete transparency
        return json.dumps(response, indent=2)
        
    except Exception as e:
        logger.error(f"Failed to list media server consumers: {str(e)}")
        return f"❌ Error listing media server consumers: {str(e)}"


def _list_media_server_consumers_by_name(server_name: str) -> str:
    """List consumers for a specific media server by name"""
    try:
        # Make request to list consumers for specific media server
        endpoint = f"dsa/components/mediaservers/listconsumers/{server_name.strip()}"
        response = dsa_client._make_request("GET", endpoint)
        
        if not response.get("valid", False):
            error_messages = []
            validation_list = response.get("validationlist", {})
            if validation_list:
                client_errors = validation_list.get("clientValidationList", [])
                server_errors = validation_list.get("serverValidationList", [])
                
                for error in client_errors + server_errors:
                    error_messages.append(f"Code {error.get('code', 'N/A')}: {error.get('message', 'Unknown error')}")
            
            if error_messages:
                return f"❌ Failed to list consumers for media server '{server_name}':\n" + "\n".join(error_messages)
            else:
                return f"❌ Failed to list consumers for media server '{server_name}': {response.get('status', 'Unknown error')}"
        
        # Return the full response for complete transparency
        return json.dumps(response, indent=2)
        
    except Exception as e:
        logger.error(f"Failed to list consumers for media server '{server_name}': {str(e)}")
        return f"❌ Error listing consumers for media server '{server_name}': {str(e)}"

#------------------ Teradata System Management Operations ------------------#

def manage_dsa_systems(
    operation: str,
    system_name: Optional[str] = None,
    tdp_id: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    ir_support: Optional[bool] = True,
    component_name: Optional[str] = None
) -> str:
    """Unified Teradata system management for all system operations
    
    This comprehensive function handles all Teradata system operations in the DSA system,
    including listing, getting details, configuring, enabling, deleting, and managing consumers.
    """
    # Validate operation
    valid_operations = [
        "list_systems", "get_system", "config_system", 
        "enable_system", "delete_system", "list_consumers", "get_consumer"
    ]
    
    if operation not in valid_operations:
        return f"❌ Invalid operation '{operation}'. Valid operations: {', '.join(valid_operations)}"
    
    try:
        # Route to the appropriate operation
        if operation == "list_systems":
            return _list_teradata_systems()
        
        elif operation == "get_system":
            if not system_name:
                return "❌ system_name is required for 'get_system' operation"
            return _get_teradata_system(system_name)
        
        elif operation == "config_system":
            if not all([system_name, tdp_id, username, password]):
                return "❌ system_name, tdp_id, username, and password are required for 'config_system' operation"
            return _config_teradata_system(system_name, tdp_id, username, password, ir_support)
        
        elif operation == "enable_system":
            if not system_name:
                return "❌ system_name is required for 'enable_system' operation"
            return _enable_teradata_system(system_name)
        
        elif operation == "delete_system":
            if not system_name:
                return "❌ system_name is required for 'delete_system' operation"
            return _delete_teradata_system(system_name)
        
        elif operation == "list_consumers":
            return _list_system_consumers()
        
        elif operation == "get_consumer":
            if not component_name:
                return "❌ component_name is required for 'get_consumer' operation"
            return _get_system_consumer(component_name)
    
    except Exception as e:
        logger.error(f"Failed to execute Teradata system operation '{operation}': {str(e)}")
        return f"❌ Error executing Teradata system operation '{operation}': {str(e)}"


def _list_teradata_systems() -> str:
    """List all configured Teradata database systems in DSA"""
    try:
        # Make API call to list Teradata systems
        response = dsa_client._make_request(
            method='GET',
            endpoint='dsa/components/systems/teradata'
        )
        
        # Return the full response for complete transparency
        return json.dumps(response, indent=2)
        
    except Exception as e:
        logger.error(f"Failed to list Teradata systems: {str(e)}")
        return f"❌ Error listing Teradata systems: {str(e)}"


def _get_teradata_system(system_name: str) -> str:
    """Get detailed information about a specific Teradata database system"""
    try:
        if not system_name or not system_name.strip():
            return "❌ System name is required and cannot be empty"
        
        system_name = system_name.strip()
        
        # Make API call to get specific Teradata system
        response = dsa_client._make_request(
            method='GET',
            endpoint=f'dsa/components/systems/teradata/{system_name}'
        )
        
        # Return the full response for complete transparency
        return json.dumps(response, indent=2)
        
    except Exception as e:
        logger.error(f"Failed to get Teradata system '{system_name}': {str(e)}")
        return f"❌ Error getting Teradata system '{system_name}': {str(e)}"


def _config_teradata_system(
    system_name: str,
    tdp_id: str,
    username: str,
    password: str,
    ir_support: Optional[str] = None
) -> str:
    """Configure a new Teradata database system in DSA"""
    try:
        if not all([system_name, tdp_id, username, password]):
            return "❌ system_name, tdp_id, username, and password are required"
        
        # Prepare the configuration payload - matching the working model exactly
        config_data = {
            "systemName": system_name.strip(),
            "tdpId": tdp_id.strip(),
            "user": username.strip(),
            "password": password,
            "databaseQueryMethodType": "BASE_VIEW",
            "skipForceFull": True,
            "irSupport": ir_support or "true",
            "irSupportTarget": "true",
            "dslJsonLogging": True,
            "ajseSupport": "true",
            "softLimit": 10,
            "hardLimit": 10
        }
        
        # Make API call to configure Teradata system
        response = dsa_client._make_request(
            method='POST',
            endpoint='dsa/components/systems/teradata',
            data=config_data
        )
        
        # Return the full response for complete transparency
        return json.dumps(response, indent=2)
        
    except Exception as e:
        logger.error(f"Failed to configure Teradata system '{system_name}': {str(e)}")
        return f"❌ Error configuring Teradata system '{system_name}': {str(e)}"


def _enable_teradata_system(system_name: str) -> str:
    """Enable a configured Teradata database system in DSA"""
    try:
        if not system_name or not system_name.strip():
            return "❌ System name is required"
        
        system_name = system_name.strip()
        
        # Make API call to enable Teradata system
        response = dsa_client._make_request(
            method='PATCH',
            endpoint=f'dsa/components/systems/enabling/{system_name}/',
            data={"enabled": True}
        )
        
        # Return the full response for complete transparency
        return json.dumps(response, indent=2)
        
    except Exception as e:
        logger.error(f"Failed to enable Teradata system '{system_name}': {str(e)}")
        return f"❌ Error enabling Teradata system '{system_name}': {str(e)}"


def _delete_teradata_system(system_name: str) -> str:
    """Delete a Teradata database system from DSA"""
    try:
        if not system_name or not system_name.strip():
            return "❌ System name is required"
        
        system_name = system_name.strip()
        
        # Make API call to delete Teradata system
        response = dsa_client._make_request(
            method='DELETE',
            endpoint=f'dsa/components/systems/teradata/{system_name}'
        )
        
        # Return the full response for complete transparency
        return json.dumps(response, indent=2)
        
    except Exception as e:
        logger.error(f"Failed to delete Teradata system '{system_name}': {str(e)}")
        return f"❌ Error deleting Teradata system '{system_name}': {str(e)}"


def _list_system_consumers() -> str:
    """List all system consumers in DSA"""
    try:
        # Make API call to list system consumers
        response = dsa_client._make_request(
            method='GET',
            endpoint='dsa/components/systems/listconsumers'
        )
        
        # Return the full response for complete transparency
        return json.dumps(response, indent=2)
        
    except Exception as e:
        logger.error(f"Failed to list system consumers: {str(e)}")
        return f"❌ Error listing system consumers: {str(e)}"


def _get_system_consumer(component_name: str) -> str:
    """Get detailed information about a specific system consumer"""
    try:
        if not component_name or not component_name.strip():
            return "❌ Component name is required and cannot be empty"
        
        component_name = component_name.strip()
        
        # Make API call to get specific system consumer
        response = dsa_client._make_request(
            method='GET',
            endpoint=f'dsa/components/systems/listconsumers/{component_name}'
        )
        
        # Return complete DSA response for transparency
        return json.dumps(response, indent=2)
        
    except Exception as e:
        logger.error(f"Failed to get system consumer '{component_name}': {str(e)}")
        return f"❌ Error getting system consumer '{component_name}': {str(e)}"

#------------------ Disk File Target Group Operations ------------------#

def _list_disk_file_target_groups(replication: bool = False) -> str:
    """List all disk file target groups"""
    try:
        response = dsa_client._make_request(
            method="GET",
            endpoint=f"dsa/components/target-groups/disk-file-system?replication={str(replication).lower()}"
        )
        return json.dumps(response, indent=2)
    except Exception as e:
        logger.error(f"Failed to list disk file target groups: {str(e)}")
        return f"❌ Error listing disk file target groups: {str(e)}"


def _get_disk_file_target_group(target_group_name: str, replication: bool = False) -> str:
    """Get details of a specific disk file target group"""
    try:
        response = dsa_client._make_request(
            method="GET",
            endpoint=f"dsa/components/target-groups/disk-file-system/{target_group_name}/?replication={str(replication).lower()}"
        )
        return json.dumps(response, indent=2)
    except Exception as e:
        logger.error(f"Failed to get disk file target group '{target_group_name}': {str(e)}")
        return f"❌ Error getting disk file target group '{target_group_name}': {str(e)}"


def _create_disk_file_target_group(target_group_config: str, replication: bool = False) -> str:
    """Create a new disk file target group using JSON configuration"""
    try:
        import json
        try:
            config_data = json.loads(target_group_config)
            target_group_name = config_data.get('targetGroupName', 'Unknown')
        except json.JSONDecodeError as e:
            return f"❌ Error: Invalid JSON in target_group_config: {str(e)}"
        
        logger.info(f"Creating target disk file system '{target_group_name}' via DSA API")
        
        response = dsa_client._make_request(
            method="POST",
            endpoint=f"dsa/components/target-groups/disk-file-system?replication={str(replication).lower()}",
            data=config_data
        )
        return json.dumps(response, indent=2)
    except Exception as e:
        logger.error(f"Failed to create disk file target group: {str(e)}")
        return f"❌ Error creating disk file target group: {str(e)}"


def _enable_disk_file_target_group(target_group_name: str) -> str:
    """Enable a disk file target group"""
    try:
        response = dsa_client._make_request(
            method="PATCH",
            endpoint=f"dsa/components/target-groups/disk-file-system/enabling/{target_group_name}/"
        )
        return json.dumps(response, indent=2)
    except Exception as e:
        logger.error(f"Failed to enable disk file target group '{target_group_name}': {str(e)}")
        return f"❌ Error enabling disk file target group '{target_group_name}': {str(e)}"


def _disable_disk_file_target_group(target_group_name: str) -> str:
    """Disable a disk file target group"""
    try:
        response = dsa_client._make_request(
            method="PATCH",
            endpoint=f"dsa/components/target-groups/disk-file-system/disabling/{target_group_name}/"
        )
        return json.dumps(response, indent=2)
    except Exception as e:
        logger.error(f"Failed to disable disk file target group '{target_group_name}': {str(e)}")
        return f"❌ Error disabling disk file target group '{target_group_name}': {str(e)}"


def _delete_disk_file_target_group(
    target_group_name: str,
    replication: bool = False,
    delete_all_data: bool = False
) -> str:
    """Delete a disk file target group"""
    try:
        response = dsa_client._make_request(
            method="DELETE",
            endpoint=f"dsa/components/target-groups/disk-file-system/{target_group_name}/?replication={str(replication).lower()}&deleteAllData={str(delete_all_data).lower()}"
        )
        return json.dumps(response, indent=2)
    except Exception as e:
        logger.error(f"Failed to delete disk file target group '{target_group_name}': {str(e)}")
        return f"❌ Error deleting disk file target group '{target_group_name}': {str(e)}"


def manage_dsa_disk_file_target_groups(
    operation: str,
    target_group_name: Optional[str] = None,
    target_group_config: Optional[str] = None,
    replication: bool = False,
    delete_all_data: bool = False
) -> str:
    """Manage DSA disk file target groups
    
    Provides comprehensive management of disk file target groups including:
    - List all target groups
    - Get specific target group details
    - Create new target groups
    - Enable/disable target groups
    - Delete target groups
    
    Args:
        operation: Operation to perform ('list', 'get', 'create', 'enable', 'disable', 'delete')
        target_group_name: Name of the target group (required for get, enable, disable, delete)
        target_group_config: JSON configuration string for create operation
        replication: Enable replication (for delete operation)
        delete_all_data: Whether to delete all backup data (for delete operation)
    
    Returns:
        JSON string with operation results
    """
    try:
        logger.info(f"Managing DSA disk file target groups - operation: {operation}")
        
        if operation == "list":
            return _list_disk_file_target_groups(replication)
            
        elif operation == "get":
            if not target_group_name:
                return json.dumps({"status": "error", "data": "❌ target_group_name is required for get operation"}, indent=2)
            return _get_disk_file_target_group(target_group_name, replication)
            
        elif operation == "create":
            if not target_group_config:
                return json.dumps({"status": "error", "data": "❌ target_group_config is required for create operation"}, indent=2)
            return _create_disk_file_target_group(target_group_config, replication)
            
        elif operation == "enable":
            if not target_group_name:
                return json.dumps({"status": "error", "data": "❌ target_group_name is required for enable operation"}, indent=2)
            return _enable_disk_file_target_group(target_group_name)
            
        elif operation == "disable":
            if not target_group_name:
                return json.dumps({"status": "error", "data": "❌ target_group_name is required for disable operation"}, indent=2)
            return _disable_disk_file_target_group(target_group_name)
            
        elif operation == "delete":
            if not target_group_name:
                return json.dumps({"status": "error", "data": "❌ target_group_name is required for delete operation"}, indent=2)
            return _delete_disk_file_target_group(target_group_name, replication, delete_all_data)
            
        else:
            return json.dumps({
                "status": "error", 
                "data": f"❌ Unknown operation: {operation}. Supported operations: list, get, create, enable, disable, delete"
            }, indent=2)
            
    except Exception as e:
        logger.error(f"Error in manage_dsa_disk_file_target_groups: {e}")
        return json.dumps({
            "status": "error",
            "data": f"❌ Error in disk file target group operation: {str(e)}"
        }, indent=2)


#------------------ Tool Handler for MCP ------------------#

def handle_bar_manageDsaDiskFileSystem(
    conn: any,  # Not used for DSA operations, but required by MCP framework
    operation: str,
    file_system_path: str = None,
    max_files: int = None,
    *args,
    **kwargs
):
    """
    Handle DSA disk file system operations for the MCP server
    
    This tool provides unified management of DSA disk file system configurations
    for backup and restore operations.
    
    Args:
        conn: Database connection (not used for DSA operations)
        operation: The operation to perform (list, config, delete_all, remove)
        file_system_path: Path to the file system (for config and remove operations)
        max_files: Maximum number of files allowed (for config operation)
    
    **Note: To UPDATE an existing disk file system configuration, simply use the 'config' 
    operation with the same file_system_path. The DSA API will automatically override the 
    existing configuration - no need to remove and reconfigure the file system.**
    
    Returns:
        ResponseType: formatted response with operation results + metadata
    """
    logger.debug(f"Tool: handle_bar_manageDsaDiskFileSystem: Args: operation: {operation}, file_system_path: {file_system_path}, max_files: {max_files}")
    
    try:
        # Run the synchronous operation
        result = manage_dsa_disk_file_systems(
            operation=operation,
            file_system_path=file_system_path,
            max_files=max_files
        )
        
        metadata = {
            "tool_name": "bar_manageDsaDiskFileSystem",
            "operation": operation,
            "file_system_path": file_system_path,
            "max_files": max_files,
            "success": True
        }
        
        logger.debug(f"Tool: handle_bar_manageDsaDiskFileSystem: metadata: {metadata}")
        return create_response(result, metadata)
        
    except Exception as e:
        logger.error(f"Error in handle_bar_manageDsaDiskFileSystem: {e}")
        error_result = f"❌ Error in DSA disk file system operation: {str(e)}"
        metadata = {
            "tool_name": "bar_manageDsaDiskFileSystem",
            "operation": operation,
            "error": str(e),
            "success": False
        }
        return create_response(error_result, metadata)

def handle_bar_manageAWSS3Operations(
    conn: any,  # Not used for DSA operations, but required by MCP framework
    operation: str,
    accessId: str = None,
    accessKey: str = None,
    bucketsByRegion: object = None,
    bucketName: str = None,
    prefixName: str = None,
    storageDevices: int = None,
    acctName: str = None,
    *args,
    **kwargs
):
    """
    Handle DSA AWS S3 backup solution configuration operations for the MCP server

    This tool provides unified management of DSA AWS S3 backup solution configuration
    that is  required for backup and restore operations.
    
    Args:
        conn: Database connection (not used for DSA operations)
        operation: The operation to perform (list, config). The  delete_all, remove and will be implemented later
        accessId: AWS access ID (for config operation)
        accessKey: AWS access key (for config operation)
        bucketsByRegion: List of S3 buckets by region (for config operation)
        bucketName: S3 bucket name (for config operation)
        prefixName: S3 prefix name (for config operation)
        storageDevices: Number of Storage devices (for config operation)
        acctName: AWS account name (for config operation)

    **Note: To UPDATE an existing AWS S3 configuration, simply use the 'config' operation 
    with new parameters. The DSA API will automatically override the existing 
    configuration - no need to remove and reconfigure the S3 settings.**

    Returns:
        ResponseType: formatted response with operation results + metadata
    """
    logger.info("handle_bar_manageAWSS3Operations called with operation=%s, accessId=%s, acctName=%s", operation, accessId, acctName)
    logger.debug(f"Tool: handle_bar_manageAWSS3Operations: Args: operation: {operation}, accessId: {accessId}, accessKey: {accessKey}, bucketsByRegion: {bucketsByRegion}, acctName: {acctName}")
    logger.debug(f"[DEBUG] bucketsByRegion type: {type(bucketsByRegion)} value: {bucketsByRegion}")
    try:
        # Run the synchronous operation
        result = manage_AWS_S3_backup_configurations(
            operation=operation,
            accessId=accessId,
            accessKey=accessKey,
            bucketsByRegion=bucketsByRegion,
            bucketName=bucketName,
            prefixName=prefixName,
            storageDevices=storageDevices,
            acctName=acctName
        )
        metadata = {
            "tool_name": "bar_manageAWSS3Operations",
            "operation": operation,
            "accessId": accessId,
            "accessKey": accessKey,
            "bucketsByRegion": bucketsByRegion,
            "bucketName": bucketName,
            "prefixName": prefixName,
            "storageDevices": storageDevices,
            "acctName": acctName,
            "success": True
        }
        logger.debug(f"Tool: handle_bar_manageAWSS3Operations: metadata: {metadata}")
        return create_response(result, metadata)
    except Exception as e:
        logger.error(f"Error in handle_bar_manageAWSS3Operations: {e}")
        error_result = f"❌ Error in DSA AWS S3 operation: {str(e)}"
        metadata = {
            "tool_name": "bar_manageAWSS3Operations",
            "operation": operation,
            "error": str(e),
            "success": False
        }
        return create_response(error_result, metadata)

def handle_bar_manageMediaServer(
    conn: any,  # Not used for DSA operations, but required by MCP framework
    operation: str,
    server_name: str = None,
    port: int = None,
    ip_addresses: str = None,
    pool_shared_pipes: int = 50,
    virtual: bool = False,
    *args,
    **kwargs
):
    """
    Unified media server management tool for all DSA media server operations.
    
    This comprehensive tool handles all media server operations in the DSA system,
    including listing, getting details, adding, deleting, and managing consumers.
    
    Arguments:
        operation - The operation to perform. Valid values:
                   "list" - List all media servers
                   "get" - Get details of a specific media server  
                   "add" - Add a new media server
                   "delete" - Delete a media server
                   "list_consumers" - List all media server consumers
                   "list_consumers_by_server" - List consumers for a specific server
        server_name - Name of the media server (required for get, add, delete, list_consumers_by_server)
        port - Port number for the media server (required for add operation, 1-65535)
        ip_addresses - JSON string containing IP address configuration for add operation, e.g.:
                      '[{"ipAddress": "192.168.1.100", "netmask": "255.255.255.0"}]'
        pool_shared_pipes - Number of shared pipes in the pool (for add operation, 1-99, default: 50)
        virtual - Whether to perform a virtual deletion (for delete operation, default: False)
    
    **Note: To UPDATE an existing media server configuration, simply use the 'add' operation 
    with the same server_name. The DSA API will automatically override the existing 
    configuration - no need to delete and recreate the media server.**
    
    Returns:
        ResponseType: formatted response with media server operation results + metadata
    """
    logger.debug(f"Tool: handle_bar_manageMediaServer: Args: operation: {operation}, server_name: {server_name}, port: {port}")
    
    try:
        # Validate operation
        valid_operations = [
            "list", "get", "add", "delete", 
            "list_consumers", "list_consumers_by_server"
        ]
        
        if operation not in valid_operations:
            error_result = f"❌ Invalid operation '{operation}'. Valid operations: {', '.join(valid_operations)}"
            metadata = {
                "tool_name": "bar_manageMediaServer",
                "operation": operation,
                "error": "Invalid operation",
                "success": False
            }
            return create_response(error_result, metadata)
        
        # Execute the media server operation
        result = manage_dsa_media_servers(
            operation=operation,
            server_name=server_name,
            port=port,
            ip_addresses=ip_addresses,
            pool_shared_pipes=pool_shared_pipes,
            virtual=virtual
        )
        
        metadata = {
            "tool_name": "bar_manageMediaServer",
            "operation": operation,
            "server_name": server_name,
            "success": True
        }
        logger.debug(f"Tool: handle_bar_manageMediaServer: metadata: {metadata}")
        return create_response(result, metadata)
    except Exception as e:
        logger.error(f"Error in handle_bar_manageMediaServer: {e}")
        error_result = f"❌ Error in DSA media server operation: {str(e)}"
        metadata = {
            "tool_name": "bar_manageMediaServer",
            "operation": operation,
            "error": str(e),
            "success": False
        }
        return create_response(error_result, metadata)
    
def handle_bar_manageTeradataSystem(
    conn: any,  # Not used for DSA operations, but required by MCP framework
    operation: str,
    system_name: Optional[str] = None,
    tdp_id: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    ir_support: Optional[str] = None,
    component_name: Optional[str] = None,
    *args,
    **kwargs
):
    """Unified DSA System Management Tool
    
    This comprehensive tool handles all DSA system operations including Teradata systems
    and system consumers management in a single interface.
    
    Args:
        operation: The operation to perform. Valid operations:
                  - "list_systems" - List all configured Teradata systems
                  - "get_system" - Get details for a specific Teradata system
                  - "config_system" - Configure a new Teradata system
                  - "enable_system" - Enable a Teradata system
                  - "delete_system" - Delete a Teradata system
                  - "list_consumers" - List all system consumers
                  - "get_consumer" - Get details for a specific system consumer
        system_name: Name of the Teradata system (required for system operations)
        tdp_id: TDP ID for Teradata system (required for config operation)
        username: Username for Teradata system (required for config operation)
        password: Password for Teradata system (required for config operation)
        ir_support: IR support level (for config operation) - "SOURCE", "TARGET", or "BOTH"
        component_name: Name of the system component (required for consumer operations)
    
    **Note: To UPDATE an existing Teradata system configuration, simply use the 'config_system' 
    operation with the same system_name. The DSA API will automatically override the existing 
    configuration - no need to delete and recreate the system.**
    
    Returns:
        Dict containing the result and metadata
    """
    try:
        logger.debug(f"Tool: handle_bar_manageTeradataSystem: Args: operation: {operation}, system_name: {system_name}")
        
        # Validate operation
        valid_operations = [
            "list_systems", "get_system", "config_system", 
            "enable_system", "delete_system", "list_consumers", "get_consumer"
        ]
        
        if operation not in valid_operations:
            error_result = f"❌ Invalid operation '{operation}'. Valid operations: {', '.join(valid_operations)}"
            metadata = {
                "tool_name": "bar_manageTeradataSystem",
                "operation": operation,
                "error": "Invalid operation",
                "success": False
            }
            return create_response(error_result, metadata)
        
        # Execute the Teradata system operation
        result = manage_dsa_systems(
            operation=operation,
            system_name=system_name,
            tdp_id=tdp_id,
            username=username,
            password=password,
            ir_support=ir_support,
            component_name=component_name
        )
        
        metadata = {
            "tool_name": "bar_manageTeradataSystem",
            "operation": operation,
            "system_name": system_name,
            "success": True
        }
        
        if component_name:
            metadata["component_name"] = component_name
            
        logger.debug(f"Tool: handle_bar_manageTeradataSystem: metadata: {metadata}")
        return create_response(result, metadata)
        
    except Exception as e:
        logger.error(f"Error in handle_bar_manageTeradataSystem: {e}")
        error_result = f"❌ Error in DSA Teradata system operation: {str(e)}"
        metadata = {
            "tool_name": "bar_manageTeradataSystem",
            "operation": operation,
            "error": str(e),
            "success": False
        }
        return create_response(error_result, metadata)

def handle_bar_manageDiskFileTargetGroup(
    conn: any,  # Not used for DSA operations, but required by MCP framework
    operation: str,
    target_group_name: Optional[str] = None,
    target_group_config: Optional[str] = None,
    replication: bool = False,
    delete_all_data: bool = False
):
    """Handle DSA disk file target group management operations
    
    Manage disk file target groups for backup and restore operations including:
    
    **Available Operations:**
    - `list`: List all disk file target groups
    - `get`: Get detailed information about a specific target group
    - `create`: Create a new target group with specified configuration or update existing one
    - `enable`: Enable a target group for backup operations
    - `disable`: Disable a target group
    - `delete`: Delete a target group (optionally with all backup data)
    
    **Parameters:**
    - operation: The operation to perform
    - target_group_name: Name of the target group (required for get, enable, disable, delete operations)
    - target_group_config: JSON configuration string for create operation (required for create)
    - replication: Enable replication settings for list, get, create, and delete operations (default: False)
    - delete_all_data: Delete all associated backup data when deleting target group (default: False)
    
    **Examples:**
    ```
    # List all target groups without replication
    bar_manageDiskFileTargetGroup(operation="list")
    # List all target groups with replication
    bar_manageDiskFileTargetGroup(operation="list", replication=True)

    # Get specific target group details without replication
    bar_manageDiskFileTargetGroup(operation="get", target_group_name="my_target_group")
    # Get specific target group details with replication
    bar_manageDiskFileTargetGroup(operation="get", target_group_name="my_target_group", replication=True)
    
    # Create new target group
    - Create basic target group:
        config = '{"targetGroupName":"test_tg","isEnabled":true,"remoteFileSystems":[{"mediaServerName":"test-ms","fileSystems":[{"path":"/backup/test","files":100,"filesystemId":1}]}]}'
        bar_manageDiskFileTargetGroup(operation="create", target_group_config=config)

    - Create multi-server group:
        config = '{"targetGroupName":"backup_tg","isEnabled":true,"remoteFileSystems":[{"mediaServerName":"ms1","fileSystems":[{"path":"/backup1","files":500}]},{"mediaServerName":"ms2","fileSystems":[{"path":"/backup2","files":500}]}]}'
        bar_manageDiskFileTargetGroup(operation="create", target_group_config=config)

    **Note: To UPDATE an existing target group configuration, simply use the 'create' operation 
    with the same targetGroupName. The DSA API will automatically override the existing 
    configuration - no need to delete and recreate the target group.**

    # Enable a target group
    bar_manageDiskFileTargetGroup(operation="enable", target_group_name="my_target_group")
    # Disable a target group
    bar_manageDiskFileTargetGroup(operation="disable", target_group_name="my_target_group")
    
    # Delete a target group and all its data with replication
    - Delete configuration only:
        bar_manageDiskFileTargetGroup("delete", target_group_name="test_tg")
    - Delete with all data (PERMANENT):
        bar_manageDiskFileTargetGroup("delete", 
                                       target_group_name="old_tg", 
                                       delete_all_data=True)
    - Delete replicated group:
        bar_manageDiskFileTargetGroup("delete", 
                                       target_group_name="repl_tg", 
                                       replication=True, 
                                       delete_all_data=True)

    ```
    
    Returns:
        JSON string containing the operation results and status
    """
    try:
        logger.info(f"BAR Disk File Target Group Management - Operation: {operation}")
        
        result = manage_dsa_disk_file_target_groups(
            operation=operation,
            target_group_name=target_group_name,
            target_group_config=target_group_config,
            replication=replication,
            delete_all_data=delete_all_data
        )
        
        metadata = {
            "tool_name": "bar_manageDiskFileTargetGroup",
            "operation": operation,
            "target_group_name": target_group_name,
            "success": True
        }
        
        if target_group_config:
            metadata["target_group_config"] = target_group_config
        if replication:
            metadata["replication"] = replication
        if delete_all_data:
            metadata["delete_all_data"] = delete_all_data
            
        logger.debug(f"Tool: handle_bar_manageDiskFileTargetGroup: metadata: {metadata}")
        return create_response(result, metadata)
        
    except Exception as e:
        logger.error(f"Error in handle_bar_manageDiskFileTargetGroup: {e}")
        error_result = f"❌ Error in DSA disk file target group operation: {str(e)}"
        metadata = {
            "tool_name": "bar_manageDiskFileTargetGroup",
            "operation": operation,
            "error": str(e),
            "success": False
        }
        return create_response(error_result, metadata)

