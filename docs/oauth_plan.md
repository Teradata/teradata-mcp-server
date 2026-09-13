# OAuth Integration Plan for Teradata MCP Server

## Overview

This document outlines the research findings on Teradata's OAuth and identity provider support, and proposes a phased implementation plan to add OAuth as an authentication option to the MCP server while maintaining backwards compatibility with existing auth methods.

## Research Findings

### Teradata OAuth & Identity Provider Support

#### VantageCloud Lake (Cloud-Native)
- **Native OIDC & OAuth 2.0 support** — Understands JWT bearer tokens directly
- **Token format** — JWT obtained via OAuth 2.0 client credentials flow
- **Token usage** — Passed as `Authorization: Bearer <JWT>` in API requests
- **Supported Identity Providers**:
  - Microsoft Entra ID (Azure AD) via OpenID Protocol
  - Okta via SAML 2.0
  - Generic OIDC and SAML 2.0 providers
- **Feature** — Bring Your Own Identity Provider (BYOIDP) enables enterprise IdP integration

#### Traditional Teradata Vantage (On-Premises)
- **Primary auth methods** — LDAP, Kerberos, TD2 (username/password), NTLM
- **Token-based** — No native OAuth/OIDC (uses directory services)
- **MFA support** — Certificate-based MFA available
- **SSO** — Through enterprise identity providers via directory integration

### Key Capabilities
- **JWT Bearer Tokens** — OAuth 2.0 client credentials produce JWTs
- **Multi-tenant support** — Secure Zones for tenant isolation, RBAC for authorization
- **Token validation** — Standard JWT signature, expiry, and claims validation
- **Federation** — VantageCloud Lake users log in with corporate credentials

### Documentation References
- [Teradata Authentication Methods](https://docs.teradata.com/r/Enterprise_IntelliFlex_VMware/Database-Introduction/Vantage-Security/User-Authentication/Authentication-Method)
- [Adding Identity Provider to VantageCloud Lake](https://docs.teradata.com/r/Lake-Configure-and-Manage-Your-Environment-and-Organization/Managing-Access/Adding-an-Identity-Provider)
- [Create JWT Token for API Calls](https://developers.teradata.com/quickstarts/vantagecloud-lake/create-jwt-token-for-api-calls/)

---

## Recommended Architecture

### Phase 1: OAuth Token Validation & JWT Bearer Support (VantageCloud Lake)

**Goal** — Enable JWT bearer token authentication for VantageCloud Lake deployments.

#### Approach
1. Accept OAuth tokens in request headers (`Authorization: Bearer <token>`)
2. Validate JWT signature, expiry, and claims (issuer, audience)
3. Extract user identity from JWT claims
4. Pass validated token to Teradata as bearer authentication
5. Create per-request connections using the bearer token (no shared pool)

#### Why This First
- **Lowest complexity** — No credential exchange or mapping needed
- **Native support** — Teradata natively understands JWT tokens
- **Customer demand** — Okta is a primary request
- **No breaking changes** — Existing auth methods unchanged

#### Implementation Details
- **Token endpoint** — Support `Authorization: Bearer <JWT>` in MCP protocol requests
- **JWT validation library** — `PyJWT` or similar for signature/claims verification
- **Per-request pooling** — Create connections on-demand with bearer token, close after request
- **Configuration** — New auth mode `oauth` in config with:
  - `oidc_issuer_url` (e.g., `https://your-okta-domain.okta.com/oauth2/v1`)
  - `client_id` and `client_secret` for token validation
  - Optional claims to validate (e.g., `audience`, `scope`)

---

### Phase 2: Credential Exchange Service (On-Premises)

**Goal** — Support OAuth with traditional Teradata Vantage (LDAP/Kerberos-based).

#### Approach
1. Accept OAuth tokens from Okta/Azure AD/other IdPs
2. Validate JWT (like Phase 1)
3. **Map IdP claims to Teradata credentials** — Extract username or group claims, resolve to Teradata user
4. Use mapped credentials to create traditional connections
5. Optional: Lookup Teradata roles/permissions from LDAP based on IdP groups

#### Why Second
- **More complex** — Requires identity mapping and potentially LDAP lookup
- **Lower immediate demand** — On-prem deployments may have alternative integrations
- **Can build on Phase 1** — Reuse JWT validation, add mapping layer

#### Implementation Details
- **Mapping rules** — Configuration-driven claim-to-user mapping:
  - Direct mapping: `sub` claim → Teradata username
  - Group-based: IdP group → Teradata role
  - Custom resolver: Lambda/plugin for complex logic
- **LDAP integration** — Optional LDAP lookup to enrich claims with Teradata roles
- **Backwards compatibility** — Existing `DATABASE_URI` auth unchanged
- **Configuration example**:
  ```yaml
  auth:
    oauth:
      mode: credential_exchange
      oidc_issuer_url: https://your-okta-domain.okta.com/oauth2/v1
      claim_mapping:
        username_claim: preferred_username
        groups_claim: groups
      ldap_lookup: true  # optional
  ```

---

### Phase 3: Multi-Pool Architecture (Optional)

**Goal** — Support both OAuth and traditional auth simultaneously.

#### Approach
1. **Default pool** — Created from `DATABASE_URI` at startup (current behavior)
2. **OAuth request path** — Detect OAuth token in headers, create per-request connection
3. **Routing** — Tool handlers check for bearer token, use appropriate pool

#### Why Third (Optional)
- **Enterprise requirement** — Some customers need both auth types in same deployment
- **Gradual migration** — Allows phased rollout without forcing all users to OAuth

---

## Implementation Plan

### Phase 1: OAuth/JWT Bearer Support (VantageCloud Lake)

#### Step 1.1: Add JWT Validation Middleware
- **File** — `src/teradata_mcp_server/middleware.py`
- **Changes**:
  - Add `OAuthValidator` class using `PyJWT`
  - Parse `Authorization: Bearer <token>` from request headers
  - Validate signature, expiry, issuer, audience claims
  - Extract user identity and store in request context

#### Step 1.2: Add OAuth Configuration
- **File** — `src/teradata_mcp_server/config/profiles.yml`
- **Add new auth section**:
  ```yaml
  oauth:
    enabled: false
    oidc_issuer_url: ""
    client_id: ""
    client_secret: ""
    audience: ""
    validate_claims:
      iss: true
      exp: true
      aud: true
  ```

#### Step 1.3: Add Per-Request Connection Pool
- **File** — `src/teradata_mcp_server/tools/td_connect.py`
- **Add method** — `get_oauth_connection(bearer_token: str) -> Connection`
  - Create SQLAlchemy engine with bearer token auth
  - Return single connection for request lifetime
  - Ensure cleanup after request completes

#### Step 1.4: Update Tool Handlers
- **File** — `src/teradata_mcp_server/app.py`
- **Modify lifespan/injection**:
  - Check for OAuth token in request context
  - If present, use per-request connection
  - If not, use default pool (existing behavior)
  - No changes to existing handler signatures

#### Step 1.5: Testing
- **Unit tests** — JWT validation, claim extraction, error handling
- **Integration tests** — End-to-end with mock Okta/OIDC provider
- **Test cases** — Valid token, expired token, invalid signature, missing claims

#### Step 1.6: Documentation
- **Setup guides** — Step-by-step instructions for Okta and Google OAuth setup
- **Configuration reference** — All OAuth config options and environment variables
- **Troubleshooting** — Common issues and debug steps
- **Examples** — Working configuration snippets

#### Deliverables
- JWT validation middleware
- OAuth configuration options
- Per-request connection support
- Test coverage (unit + integration)
- Setup guides (Okta, Google)
- Configuration documentation
- Troubleshooting guide

---

### Phase 2: Credential Exchange Service (On-Premises)

#### Step 2.1: Add Identity Mapping
- **File** — `src/teradata_mcp_server/middleware.py` (extend)
- **Add** — `IdentityMapper` class
  - Claim-to-username mapping rules
  - Group-to-role mapping (if configured)
  - Plugin/lambda support for custom logic

#### Step 2.2: Optional LDAP Integration
- **File** — `src/teradata_mcp_server/tools/td_connect.py` (extend)
- **Add** — `ldap_lookup_roles(username: str) -> List[str]`
  - Query LDAP directory for user's groups
  - Map groups to Teradata roles

#### Step 2.3: Credential Exchange Flow
- **File** — `src/teradata_mcp_server/middleware.py`
- **Add** — `exchange_oauth_for_credentials(token: str) -> (username, password)`
  - Validate JWT
  - Extract and map identity
  - Optional LDAP lookup
  - Return Teradata credentials

#### Step 2.4: Testing
- **Unit tests** — Claim mapping, LDAP lookup, error handling
- **Integration tests** — OAuth flow with credential exchange

#### Deliverables
- Identity mapping system
- Optional LDAP integration
- Credential exchange flow
- Test coverage

---

### Phase 3: Multi-Pool Architecture (If Needed)

#### Step 3.1: Pool Manager
- **File** — `src/teradata_mcp_server/tools/td_connect.py` (extend)
- **Add** — `PoolManager` class
  - Manage default pool + per-request pools
  - Lifecycle tracking and cleanup

#### Step 3.2: Request Routing
- **File** — `src/teradata_mcp_server/app.py` (extend)
- **Modify** — Dependency injection to select pool based on auth type

#### Step 3.3: Testing
- Concurrent requests with mixed auth types
- Pool lifecycle and cleanup verification

#### Deliverables
- Multi-pool architecture
- Transparent request routing
- Test coverage

---

## Testing Strategy

### Unit Tests

#### JWT Validation Tests (`tests/unit/test_oauth_validation.py`)
```python
# Test cases to cover:
- valid_jwt_with_all_claims()
- valid_jwt_minimal_claims()
- expired_jwt()
- invalid_signature()
- missing_required_claim_issuer()
- missing_required_claim_audience()
- malformed_jwt()
- jwt_with_extra_claims()
- claim_validation_with_custom_rules()
```

#### Identity Mapping Tests (`tests/unit/test_identity_mapper.py`)
```python
# Test cases to cover:
- direct_claim_to_username_mapping()
- group_claim_to_role_mapping()
- missing_username_claim()
- missing_group_claim()
- custom_mapping_resolver()
- mapping_with_defaults()
```

#### Token Extraction Tests (`tests/unit/test_token_extraction.py`)
```python
# Test cases to cover:
- extract_bearer_token_from_header()
- bearer_token_case_insensitive()
- malformed_authorization_header()
- missing_authorization_header()
- authorization_header_with_other_schemes()
```

### Integration Tests

#### Mock OIDC Server (`tests/integration/mock_oidc_server.py`)
- Mock OIDC provider serving keys, token endpoint, and userinfo
- Support both Okta-style and Google-style token responses
- Configurable claims and signing keys
- Token expiration simulation

#### End-to-End Tests (`tests/integration/test_oauth_e2e.py`)
```python
# Test cases to cover:
- oauth_token_accepted_for_teradata_connection()
- request_without_oauth_uses_default_pool()
- mixed_oauth_and_default_auth_requests()
- token_refresh_handling()
- concurrent_requests_with_different_tokens()
- connection_cleanup_after_request()
- database_error_with_oauth_token()
- invalid_token_rejected()
```

#### Real IdP Integration Tests (Optional, Sandbox)
- Test against Okta sandbox tenant
- Test against Google OAuth sandbox
- Verify token validation with real keys
- Test with real Teradata VantageCloud Lake instance (if available)

### Test Infrastructure

#### Dependencies
```toml
[dev]
pytest = "^7.0"
pytest-asyncio = "^0.21"
pytest-mock = "^3.11"
freezegun = "^1.2"  # For JWT expiry testing
pyjwt = "^2.8"
python-jose = "^3.3"  # For generating test JWTs
cryptography = "^41.0"  # For key generation
```

#### Mock Data
- Sample JWTs for Okta format
- Sample JWTs for Google format
- Sample JWTs with missing/extra claims
- Expired JWTs
- Tampered JWTs (invalid signature)
- JWKS response fixtures

#### Test Configuration
```yaml
# tests/integration/config/oauth_test.yml
oauth:
  enabled: true
  oidc_issuer_url: "http://localhost:9999"  # Mock OIDC server
  client_id: "test-client-id"
  client_secret: "test-client-secret"
  audience: "test-audience"
  validate_claims:
    iss: true
    exp: true
    aud: true
```

---

## Documentation Changes

### New Files to Create

#### 1. `docs/oauth/SETUP_OKTA.md` — Okta Configuration Guide

**Contents:**
- Prerequisites (Okta organization, VantageCloud Lake account)
- Step-by-step Okta app registration:
  - Create OIDC application
  - Configure authorization server
  - Add custom claims (username, groups)
  - Generate client credentials
  - Copy issuer URL, client ID, client secret
- Step-by-step MCP server configuration:
  - Environment variables
  - Configuration file format
  - Testing the connection
- Troubleshooting:
  - Common errors and solutions
  - How to validate JWTs manually
  - Debug logging

**Example sections:**
```markdown
## Create OIDC Application in Okta

1. Sign in to your Okta organization
2. Navigate to **Applications > Applications > Create App Integration**
3. Select **OIDC - OpenID Connect**
4. Select **Native Application** or **Web Application** (based on your use case)
5. Fill in the form:
   - App name: "Teradata MCP Server"
   - Grant type: **Client Credentials**
   - ...

## Copy Configuration Values

After creating the app, collect:
- **Issuer URL**: Found in **Security > API > Authorization Servers**
- **Client ID**: From app settings
- **Client Secret**: From app settings (save securely)
- **Audience**: Set to your Teradata instance URL or custom value

## Configure MCP Server

Set environment variables:

\`\`\`bash
export DATABASE_URI="teradataml://oauth@vantagecloud.teradata.com"
export OAUTH_OIDC_ISSUER_URL="https://your-org.okta.com/oauth2/v1"
export OAUTH_CLIENT_ID="0oa1234567890abc"
export OAUTH_CLIENT_SECRET="your_secret_here"
export OAUTH_AUDIENCE="https://vantagecloud.teradata.com"
export OAUTH_ENABLED=true

uv run teradata-mcp-server --database_uri "$DATABASE_URI"
\`\`\`

## Test the Connection

Use `curl` to validate your setup:

\`\`\`bash
# 1. Get a token from Okta
TOKEN=$(curl -X POST \\
  "https://your-org.okta.com/oauth2/v1/token" \\
  -H "Accept: application/json" \\
  -d "client_id=$OAUTH_CLIENT_ID" \\
  -d "client_secret=$OAUTH_CLIENT_SECRET" \\
  -d "audience=$OAUTH_AUDIENCE" \\
  -d "grant_type=client_credentials" | jq -r '.access_token')

echo "Token: $TOKEN"

# 2. Use token with MCP server (pseudo-code, actual format depends on MCP client)
curl -X POST http://localhost:8001/mcp/tools \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"tool": "base_readQuery", "query": "SELECT 1"}'
\`\`\`
```

#### 2. `docs/oauth/SETUP_GOOGLE.md` — Google OAuth Configuration Guide

**Contents:**
- Prerequisites (Google Cloud project, VantageCloud Lake account)
- Step-by-step Google Cloud setup:
  - Create OAuth 2.0 application
  - Configure consent screen
  - Create service account credentials
  - Add custom claims
  - Download JSON key file
- Step-by-step MCP server configuration:
  - Using service account key
  - Environment variables
  - Configuration file format
  - Testing the connection
- Troubleshooting

**Example sections:**
```markdown
## Create Google Cloud OAuth Application

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select existing one
3. Navigate to **APIs & Services > Credentials**
4. Click **Create Credentials > Service Account**
5. Fill in the form:
   - Service account name: "Teradata MCP Server"
   - Description: "OAuth authentication for Teradata MCP"
6. Click **Create and Continue**
7. Grant roles (optional, based on your setup):
   - Skip for OAuth-only use case
8. Click **Continue**

## Create and Download Service Account Key

1. In the Service Account details page, go to **Keys** tab
2. Click **Add Key > Create new key**
3. Choose **JSON** format
4. The JSON key file will download automatically
5. Store securely (do not commit to version control)

## Extract Configuration Values

From the downloaded JSON key file:

\`\`\`json
{
  "type": "service_account",
  "project_id": "your-project-id",
  "private_key_id": "key-id",
  "private_key": "-----BEGIN PRIVATE KEY-----...",
  "client_email": "teradata-mcp@your-project.iam.gserviceaccount.com",
  "client_id": "123456789",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs"
}
\`\`\`

## Configure MCP Server

Option A: Using environment variables (from JSON file):

\`\`\`bash
export OAUTH_PROVIDER=google
export DATABASE_URI="teradataml://oauth@vantagecloud.teradata.com"
export GOOGLE_SERVICE_ACCOUNT_KEY_FILE="/path/to/service-account-key.json"
export GOOGLE_TOKEN_URI="https://oauth2.googleapis.com/token"
export OAUTH_AUDIENCE="https://vantagecloud.teradata.com"
export OAUTH_ENABLED=true

uv run teradata-mcp-server --database_uri "$DATABASE_URI"
\`\`\`

Option B: Using configuration file:

\`\`\`yaml
# config/oauth.yml
oauth:
  enabled: true
  provider: google
  service_account_key_file: "/path/to/service-account-key.json"
  token_uri: "https://oauth2.googleapis.com/token"
  audience: "https://vantagecloud.teradata.com"
  validate_claims:
    iss: true
    exp: true
    aud: true
\`\`\`

## Test the Connection

Use `curl` to validate your setup:

\`\`\`bash
# 1. Create JWT assertion (or use a library)
# See: https://developers.google.com/identity/protocols/oauth2/service-account

# 2. Exchange JWT for access token
TOKEN=$(curl -X POST \\
  "https://oauth2.googleapis.com/token" \\
  -H "Content-Type: application/x-www-form-urlencoded" \\
  -d "grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer" \\
  -d "assertion=$JWT_ASSERTION" | jq -r '.access_token')

echo "Token: $TOKEN"

# 3. Use token with MCP server
curl -X POST http://localhost:8001/mcp/tools \\
  -H "Authorization: Bearer $TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{"tool": "base_readQuery", "query": "SELECT 1"}'
\`\`\`
```

#### 3. `docs/oauth/CONFIGURATION_REFERENCE.md` — Complete Configuration Reference

**Contents:**
- All environment variables and config file options
- Explanation of each setting
- Default values
- Required vs. optional
- Valid values and constraints
- Examples for different scenarios

**Structure:**
```markdown
# OAuth Configuration Reference

## Environment Variables

### OAUTH_ENABLED
- **Type:** boolean
- **Default:** false
- **Required:** No
- **Description:** Enable OAuth authentication
- **Example:** `export OAUTH_ENABLED=true`

### OAUTH_PROVIDER
- **Type:** string
- **Default:** "oidc"
- **Required:** No
- **Valid values:** "okta", "google", "azure", "oidc"
- **Description:** Identity provider type
- **Example:** `export OAUTH_PROVIDER=okta`

### OAUTH_OIDC_ISSUER_URL
- **Type:** string
- **Default:** ""
- **Required:** Yes (if OAUTH_ENABLED=true and OAUTH_PROVIDER=oidc)
- **Description:** OIDC issuer URL (e.g., https://your-org.okta.com/oauth2/v1)
- **Example:** `export OAUTH_OIDC_ISSUER_URL="https://dev-123456.okta.com/oauth2/v1"`

### OAUTH_CLIENT_ID
- **Type:** string
- **Default:** ""
- **Required:** Yes (if OAUTH_ENABLED=true)
- **Description:** OAuth client ID from your IdP
- **Example:** `export OAUTH_CLIENT_ID="0oa1234567890abc"`

### OAUTH_CLIENT_SECRET
- **Type:** string
- **Default:** ""
- **Required:** Yes (if OAUTH_ENABLED=true)
- **Description:** OAuth client secret (store securely, use secrets management)
- **Example:** `export OAUTH_CLIENT_SECRET="your_secret_key_here"`
- **Note:** Never commit to version control; use environment variables or secrets manager

### OAUTH_AUDIENCE
- **Type:** string
- **Default:** ""
- **Required:** No (recommended)
- **Description:** Expected audience claim in JWT (for validation)
- **Example:** `export OAUTH_AUDIENCE="https://vantagecloud.teradata.com"`

### OAUTH_VALIDATE_ISS (Issuer)
- **Type:** boolean
- **Default:** true
- **Required:** No
- **Description:** Validate JWT issuer claim matches OAUTH_OIDC_ISSUER_URL
- **Example:** `export OAUTH_VALIDATE_ISS=true`

### OAUTH_VALIDATE_AUD (Audience)
- **Type:** boolean
- **Default:** true
- **Required:** No
- **Description:** Validate JWT audience claim matches OAUTH_AUDIENCE
- **Example:** `export OAUTH_VALIDATE_AUD=true`

### OAUTH_VALIDATE_EXP (Expiry)
- **Type:** boolean
- **Default:** true
- **Required:** No
- **Description:** Validate JWT expiry time
- **Example:** `export OAUTH_VALIDATE_EXP=true`

### OAUTH_USERNAME_CLAIM
- **Type:** string
- **Default:** "sub"
- **Required:** No (Phase 2+)
- **Description:** JWT claim to extract as username (for credential exchange)
- **Example:** `export OAUTH_USERNAME_CLAIM="preferred_username"`
- **Note:** Phase 1 uses "sub" by default

### OAUTH_GROUPS_CLAIM
- **Type:** string
- **Default:** "groups"
- **Required:** No (Phase 2+)
- **Description:** JWT claim to extract as user groups (for role mapping)
- **Example:** `export OAUTH_GROUPS_CLAIM="org.roles"`
- **Note:** Phase 2+ feature for credential exchange

## Configuration File Format

Location: `config/oauth.yml` or set via `CONFIG_DIR` environment variable

```yaml
oauth:
  enabled: false
  provider: oidc  # or: okta, google, azure
  
  # OIDC/Okta specific
  oidc_issuer_url: ""  # e.g., https://dev-123456.okta.com/oauth2/v1
  client_id: ""
  client_secret: ""
  audience: ""
  
  # Google specific (Phase 2+)
  service_account_key_file: ""  # Path to downloaded JSON key
  token_uri: "https://oauth2.googleapis.com/token"
  
  # Claim validation
  validate_claims:
    iss: true    # Issuer
    exp: true    # Expiry
    aud: true    # Audience
    nbf: false   # Not before (optional)
  
  # Phase 2+: Credential exchange
  mode: bearer   # or: credential_exchange
  username_claim: "sub"      # JWT claim for username
  groups_claim: "groups"     # JWT claim for groups
  
  # Phase 2+: LDAP integration (optional)
  ldap:
    enabled: false
    url: ""          # e.g., ldap://ldap-host:389
    base_dn: ""      # e.g., dc=company,dc=com
    user_search_filter: "(uid={username})"
    group_search_filter: "(memberUid={username})"
    timeout: 5000    # milliseconds
```

## Precedence

Environment variables override config file settings. Example:

1. Default from code
2. Override from config/oauth.yml
3. Override from environment variables (highest priority)

## Validation Rules

- If `OAUTH_ENABLED=true`, then `OAUTH_OIDC_ISSUER_URL` and `OAUTH_CLIENT_ID` are required
- If `OAUTH_VALIDATE_AUD=true`, then `OAUTH_AUDIENCE` must be set
- If credential exchange mode is enabled, `OAUTH_USERNAME_CLAIM` must be set
```

#### 4. `docs/oauth/TROUBLESHOOTING.md` — Troubleshooting Guide

**Contents:**
- Common errors and solutions
- Debug logging
- How to validate JWTs
- How to test with curl
- Connection issues
- Token refresh issues

**Example sections:**
```markdown
# OAuth Troubleshooting Guide

## Common Errors

### Error: "Invalid token signature"
**Cause:** JWT signature doesn't match public keys from OIDC provider

**Solutions:**
1. Verify OAUTH_OIDC_ISSUER_URL is correct
2. Ensure JWKS (JSON Web Key Set) endpoint is accessible
3. Check that OAUTH_CLIENT_ID and OAUTH_CLIENT_SECRET are correct
4. Validate the token was issued by the correct provider

**Debug:**
```bash
# Extract JWT header and payload (without verification)
TOKEN="your_jwt_token"
echo "$TOKEN" | cut -d'.' -f1 | base64 -d | jq .
echo "$TOKEN" | cut -d'.' -f2 | base64 -d | jq .

# Visit JWKS endpoint to check available keys
curl https://your-org.okta.com/oauth2/v1/keys
```

### Error: "Token expired"
**Cause:** JWT expiry time (exp) is in the past

**Solutions:**
1. Request a new token from your IdP
2. Check server time is synchronized (use NTP)
3. If testing, use JWTs with future expiry

**Debug:**
```bash
# Check expiry time
TOKEN="your_jwt_token"
echo "$TOKEN" | cut -d'.' -f2 | base64 -d | jq '.exp'
# Convert Unix timestamp to readable format:
date -d @$(echo "$TOKEN" | cut -d'.' -f2 | base64 -d | jq '.exp')
```

### Error: "Audience mismatch"
**Cause:** `aud` claim in JWT doesn't match `OAUTH_AUDIENCE`

**Solutions:**
1. Check `OAUTH_AUDIENCE` is set correctly
2. Verify the token's `aud` claim matches (see debug below)
3. If audience validation is optional, set `OAUTH_VALIDATE_AUD=false`

**Debug:**
```bash
TOKEN="your_jwt_token"
echo "$TOKEN" | cut -d'.' -f2 | base64 -d | jq '.aud'
echo "Expected: $OAUTH_AUDIENCE"
```

### Error: "Unable to fetch JWKS from issuer"
**Cause:** Cannot reach the OIDC provider's JWKS endpoint

**Solutions:**
1. Verify network connectivity to the issuer
2. Check firewall/proxy rules allow HTTPS outbound
3. Verify `OAUTH_OIDC_ISSUER_URL` is correct
4. Check issuer is up and running

**Debug:**
```bash
# Test connectivity to issuer
curl -I https://your-org.okta.com/oauth2/v1/keys

# Test with verbose output
curl -v https://your-org.okta.com/oauth2/v1/keys
```

## Enabling Debug Logging

Set environment variable to enable detailed logging:

```bash
export LOG_LEVEL=DEBUG
uv run teradata-mcp-server --database_uri "$DATABASE_URI"
```

Debug output will include:
- JWT validation steps
- Claims extraction
- Token exchange details
- Connection pool operations

## Testing with curl

```bash
# 1. Get a token from your IdP
# For Okta:
TOKEN=$(curl -X POST https://your-org.okta.com/oauth2/v1/token \
  -d "client_id=$OAUTH_CLIENT_ID" \
  -d "client_secret=$OAUTH_CLIENT_SECRET" \
  -d "audience=$OAUTH_AUDIENCE" \
  -d "grant_type=client_credentials" | jq -r '.access_token')

# For Google:
JWT_ASSERTION=$(python3 -c "...")  # Generate JWT assertion
TOKEN=$(curl -X POST https://oauth2.googleapis.com/token \
  -d "grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer" \
  -d "assertion=$JWT_ASSERTION" | jq -r '.access_token')

# 2. Verify token format
echo "$TOKEN" | jq -R 'split(".") | .[0] | @base64d | fromjson'

# 3. Test MCP server connection
curl -X POST http://localhost:8001/mcp/tools \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"tool": "base_readQuery", "query": "SELECT 1"}'
```

## Validating Tokens Manually

Use online JWT decoder (for non-sensitive tokens only):
- https://jwt.io/

Or validate locally:
```bash
python3 << 'EOF'
import jwt
import json

token = "your_jwt_token"

# Decode without verification (to see structure)
decoded = jwt.decode(token, options={"verify_signature": False})
print(json.dumps(decoded, indent=2))

# Validate signature (requires issuer's public key)
# See https://pyjwt.readthedocs.io/en/latest/usage.html
EOF
```
```

#### 5. `docs/oauth/README.md` — OAuth Documentation Index

**Contents:**
```markdown
# OAuth Integration Documentation

This directory contains comprehensive documentation for setting up OAuth with the Teradata MCP Server.

## Quick Start

- **[Setup with Okta](SETUP_OKTA.md)** — Step-by-step guide for Okta integration
- **[Setup with Google](SETUP_GOOGLE.md)** — Step-by-step guide for Google OAuth
- **[Configuration Reference](CONFIGURATION_REFERENCE.md)** — Complete environment variable and config file reference

## Troubleshooting

- **[Troubleshooting Guide](TROUBLESHOOTING.md)** — Common errors and solutions

## Concepts

See main [OAuth Plan](../oauth_plan.md) for:
- Architecture overview
- Supported identity providers
- Phased implementation approach
- Testing strategy
```

### Updates to Existing Documentation

#### Update `README.md`
Add OAuth section to main README:

```markdown
## Authentication

### Traditional Methods (Default)
- Username/password (TD2)
- LDAP
- Kerberos

### OAuth (New)
- Okta
- Google Cloud
- Azure AD
- Generic OIDC providers

See [OAuth Documentation](docs/oauth/) for setup instructions.
```

#### Update `CLAUDE.md`
Add OAuth development notes:

```markdown
### OAuth Development

OAuth testing requires:
```bash
uv sync --extra dev
export OAUTH_OIDC_ISSUER_URL="http://localhost:9999"  # Mock OIDC server
uv run pytest tests/integration/test_oauth_e2e.py
```

See [OAuth Plan](docs/oauth_plan.md) for architecture and [OAuth Setup Guides](docs/oauth/) for Okta/Google configuration.
```

---

## Configuration Examples

### Example 1: VantageCloud Lake with Okta (Phase 1)

```bash
export DATABASE_URI="teradataml://oauth@vantagecloud.teradata.com"
export OAUTH_OIDC_ISSUER_URL="https://your-okta-domain.okta.com/oauth2/v1"
export OAUTH_CLIENT_ID="0oa1234567890"
export OAUTH_CLIENT_SECRET="your_client_secret"
export OAUTH_AUDIENCE="your-teradata-api"

uv run teradata-mcp-server --database_uri "$DATABASE_URI"
```

### Example 2: On-Premises with Okta + Credential Exchange (Phase 2)

```bash
export DATABASE_URI="teradata://placeholder@on-prem-host:1025/db"
export OAUTH_ENABLED=true
export OAUTH_MODE=credential_exchange
export OAUTH_OIDC_ISSUER_URL="https://your-okta-domain.okta.com/oauth2/v1"
export OAUTH_CLAIM_USERNAME="preferred_username"
export OAUTH_LDAP_ENABLED=true
export OAUTH_LDAP_URL="ldap://your-ldap-host:389"

uv run teradata-mcp-server
```

### Example 3: Dual Auth (Traditional + OAuth, Phase 3)

```bash
export DATABASE_URI="teradata://service_account:password@host:1025/db"
export OAUTH_ENABLED=true
export OAUTH_OIDC_ISSUER_URL="https://your-okta-domain.okta.com/oauth2/v1"

# Default pool from DATABASE_URI (existing)
# OAuth token in Authorization header routes to per-request auth
uv run teradata-mcp-server
```

---

## Timeline & Priorities

| Phase | Scope | Effort | Priority | Timeline |
|-------|-------|--------|----------|----------|
| **Phase 1** | JWT validation, per-request auth, VantageCloud Lake | ~3-4 weeks | **High** | Q3 2026 |
| **Phase 2** | Credential exchange, LDAP integration, on-prem | ~2-3 weeks | Medium | Q4 2026 |
| **Phase 3** | Multi-pool architecture, dual auth | ~1-2 weeks | Low | As needed |

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Breaking existing auth | All changes backwards compatible; existing DATABASE_URI unchanged |
| Token validation bugs | Comprehensive unit + integration test suite; use well-tested PyJWT library |
| Per-request pool overhead | Connection pooling within request; consider async cleanup |
| Identity mapping complexity | Start simple (direct claim mapping); plugin system for advanced cases |
| LDAP lookups slow requests | Cache LDAP results; make optional; set request timeout |

---

## Success Criteria

- ✅ OAuth tokens accepted and validated
- ✅ JWT claims extracted and mapped to user identity
- ✅ Teradata connections created with bearer token (Phase 1) or mapped credentials (Phase 2)
- ✅ Backwards compatibility with existing auth methods maintained
- ✅ Comprehensive test coverage (unit, integration, edge cases)
- ✅ Documentation for configuration and usage
- ✅ Customer pilot successful with Okta + VantageCloud Lake

---

## Documentation Deliverables Summary

### Setup Guides
- ✅ `docs/oauth/SETUP_OKTA.md` — Complete Okta configuration and testing
- ✅ `docs/oauth/SETUP_GOOGLE.md` — Complete Google OAuth configuration and testing
- ✅ `docs/oauth/README.md` — Documentation index and quick start

### Reference Material
- ✅ `docs/oauth/CONFIGURATION_REFERENCE.md` — All env vars, config options, examples
- ✅ `docs/oauth/TROUBLESHOOTING.md` — Common errors, debug steps, validation tools
- ✅ Updates to README.md and CLAUDE.md with OAuth pointers

### Testing Infrastructure
- ✅ Mock OIDC server (`tests/integration/mock_oidc_server.py`)
- ✅ Unit test suite (`tests/unit/test_oauth_*.py`)
- ✅ Integration test suite (`tests/integration/test_oauth_e2e.py`)
- ✅ Test fixtures and mock data
- ✅ Test configuration templates

---

## Next Steps

1. **Validate** — Confirm customer deployment is VantageCloud Lake or on-prem, and which IdPs they use
2. **Prototype** — Build Phase 1 MVP with JWT validation and per-request auth
3. **Integrate** — Merge into middleware and connection pool
4. **Test** — Unit + integration tests with mock OIDC provider (see Testing Strategy section)
5. **Document** — Create setup guides for Okta and Google (see Documentation Changes section)
6. **Iterate** — Gather feedback, move to Phase 2 if needed

