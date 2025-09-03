"""
BAR (Backup and Recovery) Tools for Teradata DSA MCP Server
Provides disk file system ma        # First, get the existing file systems
        try:
            existing_response = dsa_client._make_request(
                method="GET",
                endpoint="dsa/components/backup-applications/disk-file-system"
            )nt operations
"""

import logging
from typing import Optional

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


#------------------ Tool Handler for MCP ------------------#

def handle_bar_manageDsaDiskFileSystemOperations(
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
    for backup and recovery operations.
    
    Args:
        conn: Database connection (not used for DSA operations)
        operation: The operation to perform (list, config, delete_all, remove)
        file_system_path: Path to the file system (for config and remove operations)
        max_files: Maximum number of files allowed (for config operation)
    
    Returns:
        ResponseType: formatted response with operation results + metadata
    """
    logger.debug(f"Tool: handle_bar_manageDsaDiskFileSystemOperations: Args: operation: {operation}, file_system_path: {file_system_path}, max_files: {max_files}")
    
    try:
        # Run the synchronous operation
        result = manage_dsa_disk_file_systems(
            operation=operation,
            file_system_path=file_system_path,
            max_files=max_files
        )
        
        metadata = {
            "tool_name": "bar_manageDsaDiskFileSystemOperations",
            "operation": operation,
            "file_system_path": file_system_path,
            "max_files": max_files,
            "success": True
        }
        
        logger.debug(f"Tool: handle_bar_manageDsaDiskFileSystemOperations: metadata: {metadata}")
        return create_response(result, metadata)
        
    except Exception as e:
        logger.error(f"Error in handle_bar_manageDsaDiskFileSystemOperations: {e}")
        error_result = f"❌ Error in DSA disk file system operation: {str(e)}"
        metadata = {
            "tool_name": "bar_manageDsaDiskFileSystemOperations",
            "operation": operation,
            "error": str(e),
            "success": False
        }
        return create_response(error_result, metadata)
