# Teradata QueryGrid (QG) tools

## Prerequisites

**Teradata QueryGrid (QG) Infrastructure** must be properly configured and running before using QueryGrid tools

### Environment Variables

The QG tools require the following environment variables for making connection:

- `QG_MANAGER_HOST` - Hostname for QG Manager (QGM) APIs (default: localhost)
- `QG_MANAGER_PORT` - Port for QG Manager (QGM) APIs (default: 9443)
- `QG_MANAGER_USERNAME` - Username for QGM authentication (default: support)
- `QG_MANAGER_PASSWORD` - Password for QGM authentication (default: teradata)
- `QG_MANAGER_VERIFY_SSL` - Whether to verify SSL certificates (default: true)

### QG Profile Configuration
The QG profile is defined in `config/profiles.yml` and controls access to QG-related tools and resources.

**Profile Configuration:**
```yaml
qg:
  tool:
    - ^qg_*
  prompt:
    - ^qg_*
  resource:
    - ^qg_*
```
**What the QG profile enables:**
- Access to all `qg_*` tools for managing QueryGrid

**Usage:** Specify `--profile qg` when running MCP server to enable QG-specific functionality

## Available QueryGrid Tools

The QueryGrid MCP server provides **56 GET methods** for retrieving QueryGrid configuration and status information. All tools follow the naming convention `qg_get_*` and provide read-only access to QueryGrid Manager data.

### Core Resource Methods (42 total)

#### Managers (2 tools)
- `qg_get_managers` - Get all QueryGrid managers with optional filtering
- `qg_get_manager_by_id` - Get a specific manager by ID

#### Nodes (3 tools)
- `qg_get_nodes` - Get all nodes with advanced filtering options
- `qg_get_node_by_id` - Get a specific node by ID
- `qg_get_node_heartbeat_by_id` - Get the latest heartbeat sent by a specific node

#### Systems (2 tools)
- `qg_get_systems` - Get all systems with optional filtering
- `qg_get_system_by_id` - Get a specific system by ID

#### Connectors (6 tools)
- `qg_get_connectors` - Get all connectors with filtering
- `qg_get_connector_by_id` - Get a specific connector by ID
- `qg_get_connector_active` - Get active connector configuration
- `qg_get_connector_pending` - Get pending connector configuration
- `qg_get_connector_previous` - Get previous connector configuration
- `qg_get_connector_drivers` - Get connector drivers by version

#### Fabrics (5 tools)
- `qg_get_fabrics` - Get all fabrics with filtering
- `qg_get_fabric_by_id` - Get a specific fabric by ID
- `qg_get_fabric_active` - Get active fabric configuration
- `qg_get_fabric_pending` - Get pending fabric configuration
- `qg_get_fabric_previous` - Get previous fabric configuration

#### Networks (5 tools)
- `qg_get_networks` - Get all networks with filtering
- `qg_get_network_by_id` - Get a specific network by ID
- `qg_get_network_active` - Get active network configuration
- `qg_get_network_pending` - Get pending network configuration
- `qg_get_network_previous` - Get previous network configuration

#### Links (5 tools)
- `qg_get_links` - Get all links with filtering
- `qg_get_link_by_id` - Get a specific link by ID
- `qg_get_link_active` - Get active link configuration
- `qg_get_link_pending` - Get pending link configuration
- `qg_get_link_previous` - Get previous link configuration

#### Communication Policies (5 tools)
- `qg_get_comm_policies` - Get all communication policies
- `qg_get_comm_policy_by_id` - Get a specific communication policy by ID
- `qg_get_comm_policy_active` - Get active communication policy configuration
- `qg_get_comm_policy_pending` - Get pending communication policy configuration
- `qg_get_comm_policy_previous` - Get previous communication policy configuration

#### Bridges (2 tools)
- `qg_get_bridges` - Get all bridges with filtering
- `qg_get_bridge_by_id` - Get a specific bridge by ID

#### Data Centers (2 tools)
- `qg_get_datacenters` - Get all datacenters with filtering
- `qg_get_datacenter_by_id` - Get a specific datacenter by ID

#### Node Virtual IPs (2 tools)
- `qg_get_node_virtual_ips` - Get all node virtual IPs
- `qg_get_node_virtual_ip_by_id` - Get a specific node virtual IP by ID

### Query & Software Methods (6 total)

#### Queries (3 tools)
- `qg_get_query_summary` - Get query summary with filtering options
- `qg_get_query_by_id` - Get a specific query by ID
- `qg_get_query_details` - Get detailed information for a specific query

#### Software (3 tools)
- `qg_get_software` - Get QueryGrid software information
- `qg_get_software_by_id` - Get a specific software package by ID
- `qg_get_software_jdbc_driver` - Get QueryGrid JDBC driver software information
- `qg_get_software_jdbc_driver_by_name` - Get software information for a specific JDBC driver

### User Management Methods (4 total)

#### Users (2 tools)
- `qg_get_users` - Get all QueryGrid users
- `qg_get_user_by_username` - Get a specific user by username

#### User Mappings (2 tools)
- `qg_get_user_mappings` - Get all user mappings with filtering
- `qg_get_user_mapping_by_id` - Get a specific user mapping by ID

### Monitoring & Diagnostics (5 total)

#### Issues (2 tools)
- `qg_get_issues` - Get all active QueryGrid issues
- `qg_get_issue_by_id` - Get a specific issue by ID

#### Diagnostics (3 tools)
- `qg_get_diagnostic_check_status` - Get diagnostic check status
- `qg_get_nodes_auto_install_status` - Get automatic node installation status
- `qg_get_create_foreign_server_status` - Get CONNECTOR_CFS diagnostic check status

### API Information (1 tool)
- `qg_get_api_info` - Get QueryGrid API information

## Tool Parameters

Most tools support optional parameters for filtering and configuration:

- `extra_info` (bool) - Include additional information in responses
- `filter_by_name` (str) - Filter results by name (supports wildcards with '*')
- `filter_by_tag` (str) - Filter by tag (comma-separated key:value pairs)
- `flatten` (bool) - Flatten nested response structures

Query-specific tools support additional parameters:
- `last_modified_after` (str) - Filter queries modified after ISO8601 timestamp
- `completed` (bool) - Include only completed queries
- `query_text_phrase` (str) - Filter by text phrase in query
- `query_ref_ids` (str) - Filter by comma-separated query reference IDs
- `initiator_query_id` (str) - Filter by initiator query ID

Node-specific filtering parameters:
- `filter_by_system_id` (str) - Filter nodes by system ID
- `filter_by_bridge_id` (str) - Filter nodes by bridge ID
- `filter_by_fabric_id` (str) - Filter nodes by fabric ID
- `filter_by_connector_id` (str) - Filter nodes by connector ID
- `fabric_version` (str) - Filter by fabric version
- `connector_version` (str) - Filter by connector version
- `drivers` (str) - Filter with drivers parameter
- `details` (bool) - Include detailed information

## Usage Examples

```bash
# Get all managers
qg_get_managers

# Get managers with extra info
qg_get_managers extra_info=true

# Get specific manager
qg_get_manager_by_id id=my_manager_id

# Get nodes with filtering
qg_get_nodes filter_by_system_id=my_system_id filter_by_fabric_id=my_fabric_id

# Get systems filtered by name
qg_get_systems filter_by_name=my_system

# Get connectors with extra info
qg_get_connectors extra_info=true

# Get query summary with filters
qg_get_query_summary completed=true last_modified_after=2024-01-01T00:00:00Z

# Get fabrics flattened
qg_get_fabrics flatten=true

# Get networks filtered by tag
qg_get_networks filter_by_tag=env:production,team:backend
```

## Test Coverage

The QueryGrid tools include comprehensive test coverage with **96 test cases** across all 56 tools. Each tool has at least one test case, with complex tools having multiple test scenarios covering different parameter combinations.

Test cases are located in `tests/cases/qg_test_cases.json` and cover:
- Default parameter usage
- Optional parameter combinations
- Edge cases and filtering scenarios
- All supported parameter types (boolean, string, UUID, etc.)

---

[← Return to Main README](../../../../README.md)