# Architecture Overview

> **📍 Navigation:** [Documentation Home](../README.md) | [Server Guide](../README.md#-server-guide) | **Architecture** | [Quick Start](QUICK_START.md) | [Installation](INSTALLATION.md)

> **🎯 Goal:** Understand how Teradata MCP Server components work together

![](../media/client-server-platform.png)

## 🏗 The Big Picture

The Teradata MCP Server creates a bridge between AI clients and your Teradata platform:

```
[AI Client] ←→ [MCP Server] ←→ [Teradata Platform]
     ↓              ↓                ↓
 Claude Desktop  Toolkit        Analytic Engine
 VS Code         Security          Metadata
 Google Gemini   Profiles         Database  
 Web Clients     Custom Logic   Vector Store
```

## 🔧 Core Components

### 1. **MCP Server**
- **Role**: Protocol translator and request router
- **What it does**: 
  - Receives requests from AI clients via MCP protocol
  - Translates requests into database operations
  - Routes to appropriate Teradata services
  - Returns formatted responses

### 2. **Tool System**
- **Role**: Business logic and database operations
- **Categories**:
  - **Base Tools**: SQL queries, schema exploration, data reading
  - **Analytics Tools**: Feature Store, Vector Store, Data Quality
  - **Admin Tools**: DBA operations, security management
  - **Custom Tools**: Your business-specific logic

### 3. **Security Layer**
- **Authentication**: Validate user identity
- **Authorization**: Database RBAC enforcement  
- **Audit**: Query banding and logging
- **Rate Limiting**: Prevent abuse

### 4. **Configuration System**
- **Profiles**: Control which tools are available
- **Custom Objects**: YAML-defined tools, prompts, cubes
- **Environment**: Database connections and server settings

## 🚦 Request Flow

### User Interaction

```mermaid
sequenceDiagram
    User->>AI Client: "Show me sales data"
    AI Client->>MCP Server: MCP protocol request
    MCP Server->>Security Layer: Authenticate user
    Security Layer->>Toolkit: Route to sales_cube tool
    Toolkit->>Teradata: Execute SQL query
    Teradata->>Toolkit: Return results
    Toolkit->>MCP Server: Format response
    MCP Server->>AI Client: MCP protocol response  
    AI Client->>User: Natural language answer
```

### Request Processing Flow

1. **AI Client**: Sends MCP protocol request with user intent
2. **MCP Server**: Receives and parses structured JSON-RPC request
3. **Security Layer**: Enforces authentication and validates user identity
4. **Toolkit**: Routes to appropriate tool and builds SQL query
5. **Teradata**: Executes query with query banding and RBAC enforcement
6. **Toolkit**: Formats database results for LLM consumption
7. **MCP Server**: Returns structured MCP protocol response
8. **AI Client**: Presents natural language answer to user

## 🎭 Deployment Patterns

### Pattern 1: Bundled with Application

```mermaid
flowchart LR
    A[Claude Desktop] -->|stdio| B[MCP Server Process]
    B -->|Database Connection Pool| E[(Teradata Database)]
    
    subgraph "Application Runtime"
        B
        F[Application Logic]
    end
    
    subgraph "Security Context"
        G[Single DB User]
        H[Server Credentials]
    end
    
    G -.->|Database Auth| E
    H -.-> B
```

- **Use case**: Individual data analysis, application with dedicated MCP server instance
- **Transport**: stdio if server co-located with application or HTTP for remote access
- **Security**: One database user for the application, configured at the server level
- **Scaling**: Single server process, configurable database connection pool

### Pattern 2: Shared Server

```mermaid
flowchart LR
    A[Claude Desktop] -->|HTTP| D[MCP Server]
    B[VS Code] -->|HTTP| D
    E[Custom App 1] -->|HTTP| D
    F[Custom App 2] -->|HTTP| D
    D -->|Connection Pool| G[(Teradata Database)]
    
    subgraph "Authentication & RBAC"
        H[App User 1]
        I[App User 2]
        J[App User 3]
    end
    
    H -.->|Database Auth| G
    I -.->|Database Auth| G
    J -.->|Database Auth| G
```

- **Use case**: Shared MCP server for multiple applications
- **Transport**: streamable-http
- **Security**: One database user per application, configured at the application level, database service account for the MCP server. User identity validated by MCP server using database authentication method, RBAC policies applied to application database user.
- **Scaling**: Single server process, configurable database connection pool

### Pattern 3: Enterprise Integration

```mermaid
flowchart TB
    A[Enterprise Web Apps] -->|HTTPS| B[Reverse Proxy]
    C[Developers IDEs] -->|HTTPS| B
    E[End-user desktop tools] -->|HTTPS| B
    
    B -->|TLS Termination| F[Load Balancer]
    
    subgraph "Container Orchestration Platform"
        F -->|HTTP| G[MCP Server Instance 1]
        F -->|HTTP| H[MCP Server Instance 2]
        F -->|HTTP| I[MCP Server Instance N]
    end
    
    subgraph "Data Tier"
        G -->|Connection Pool| J[(Teradata Database)]
        H -->|Connection Pool| J
        I -->|Connection Pool| J
    end
    
    subgraph "Security & Identity"
        K[Identity Provider]
        L[Certificate Authority]
        M[User Directory]
    end
    
    subgraph "Monitoring & Observability"
        N[Metrics Collection]
        O[Centralized Logging]
        P[Health Monitoring]
    end
    
    K -.->|Authentication| B
    L -.->|TLS Certificates| B
    M -.->|User Lookup| G
    M -.->|User Lookup| H
    M -.->|User Lookup| I
    
    G -.-> N
    H -.-> N
    I -.-> N
    G -.-> O
    H -.-> O
    I -.-> O
    
    style B fill:#e1f5fe
    style F fill:#f3e5f5
    style J fill:#e8f5e8
```

- **Use case**: Large end-user base, high variety of applications, production workloads
- **Transport**: HTTPS with TLS termination at reverse proxy, HTTP internally
- **Security**: 
  - TLS encryption for external communication
  - Identity provider integration for authentication
  - Per-user database credentials with RBAC enforcement
  - Certificate management and rotation
- **Scaling**: Horizontal scaling with container orchestration, load balancing, and connection pooling

## 🛡 Security Architecture

### Security Request Flow

```mermaid
flowchart TD
    A[User Request] --> B[RequestContext Middleware]
    B --> C{Transport Mode?}
    C -->|stdio| D[Generate Request ID]
    C -->|HTTP/SSE| E[Extract Headers]
    E --> F{Auth Mode?}
    F -->|none| G[Optional X-Assume-User]
    F -->|basic| H[Validate Authorization Header]
    H --> I[Check Auth Cache]
    I -->|Cache Hit| J[Use Cached Principal]
    I -->|Cache Miss| K[Database Authentication]
    K -->|Success| L[Cache Principal]
    K -->|Failure| M[Authentication Error]
    D --> N[Set RequestContext]
    G --> N
    J --> N
    L --> N
    N --> O[Tool Execution]
    O --> P[Query Band Generation]
    P --> Q[Database RBAC Enforcement]
    Q --> R[Return Results]
    M --> S[Permission Denied]
```

### Security Layers
1. **Transport Level**: stdio (trusted) vs HTTP (authenticated)
2. **Authentication Level**: Database credential validation and caching
3. **Authorization Level**: Teradata RBAC and row-level security  
4. **Tool Level**: Parameter validation and SQL injection prevention
5. **Audit Level**: Query banding for request traceability

## 🎯 Customization Architecture

### Extension Points
1. **Custom Tools**: Python functions for business logic
2. **YAML Objects**: Declarative tools, prompts, and cubes
3. **Profiles**: Control tool availability per environment
4. **Middleware**: Request/response transformation

## ✨ Getting Started Paths

Now that you understand the architecture, choose your path:

### 🚀 **Want to try it immediately?**
→ [5-Minute Quick Start](QUICK_START.md)
- Get running with Claude Desktop in 5 minutes
- Perfect for evaluation and learning

### 🏗 **Setting up for your team?**  
→ [Installation Guide](INSTALLATION.md)
- Compare deployment options
- Production-ready configurations
- Docker and enterprise setups

### 🔒 **Need enterprise security?**
→ [Security Configuration](SECURITY.md)  
- Authentication and authorization
- Audit logging and compliance
- Production security patterns

### 🛠 **Want to customize for your business?**
→ [Customization Guide](CUSTOMIZING.md)
- Add domain-specific tools
- Create semantic layers
- Business logic integration

### 👥 **Ready to connect clients?**
→ [Client Guide](../client_guide/CLIENT_GUIDE.md)
- AI client configurations
- Desktop and web integrations
- API usage patterns

---
*This overview covers the conceptual architecture. For hands-on implementation, start with the [Quick Start Guide](QUICK_START.md).*