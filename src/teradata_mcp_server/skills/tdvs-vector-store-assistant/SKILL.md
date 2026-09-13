---
name: tdvs-vector-store-assistant
description: Use when working with Teradata Enterprise Vector Store operations (health, list, create, update, destroy, permissions, similarity search) via a connected teradata-mcp-server — routes each request to the right tdvs_* tool.
---

Route the user's request to the right `tdvs_*` tool on the connected `teradata-mcp-server` (requires the server's `tdvs` module — see `src/teradata_mcp_server/tools/tdvs/README.md`):

- Health of Teradata Vector Store → `tdvs_get_health()`
- List of vector stores → `tdvs_list()`
- Details of a specific vector store → `tdvs_get_details()`
- Create a vector store → `tdvs_create()`
- Update, add, or delete data in a vector store → `tdvs_update()`
- Destroy/delete a vector store → `tdvs_destroy()`
- Grant a user permission on a vector store → `tdvs_grant_user_permission()`
- Revoke a user's permission on a vector store → `tdvs_revoke_user_permission()`
- Similarity search against a vector store → `tdvs_similarity_search()`
- Fetching contextual information from a specific vector store to answer a question → `tdvs_ask()`; if `tdvs_ask()` fails, fall back to `tdvs_similarity_search()`.
