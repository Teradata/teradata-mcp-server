# BAR (Backup and Recovery) Tools

**Dependencies**

- DSA REST API access
- httpx for async HTTP requests
- Environment variables for DSA connection configuration

**BAR** tools:

- bar_manageDsaDiskFileSystemOperations - Unified tool for managing DSA disk file system configurations

## Configuration

The BAR tools require the following environment variables for DSA connection:

- `DSA_BASE_URL` - Base URL for DSA API (default: https://localhost:9090/)
- `DSA_USERNAME` - Username for DSA authentication (default: admin)
- `DSA_PASSWORD` - Password for DSA authentication (default: admin)
- `DSA_VERIFY_SSL` - Whether to verify SSL certificates (default: true)
- `DSA_CONNECTION_TIMEOUT` - Request timeout in seconds (default: 30)

## Available Operations

### bar_manageDsaDiskFileSystemOperations

This unified tool handles all DSA disk file system operations:

**Operations:**
- `list` - List all configured disk file systems
- `config` - Configure a new disk file system with specified path and max files
- `delete_all` - Remove all file system configurations (use with caution)
- `remove` - Remove a specific file system configuration by path

**Examples:**
- List file systems: `{"operation": "list"}`
- Add new file system: `{"operation": "config", "file_system_path": "/backup/primary", "max_files": 1000}`
- Remove file system: `{"operation": "remove", "file_system_path": "/old/backup/path"}`
- Delete all: `{"operation": "delete_all"}`

## Notes

- File systems must exist and be accessible before configuration
- Removal operations will fail if file systems are in use by backup operations
- Always verify file system availability before configuration
- Check dependencies before removing file systems

[Return to Main README](../../../../README.md)
