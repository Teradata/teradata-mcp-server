#!/usr/bin/env python3
"""
Diagnostic script to check if graph_queryDependenciesAgent tool is registered.
Run this from your teradata-mcp-server directory.
"""

import sys
import os

# Add the src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

print("=" * 70)
print("GRAPH TOOL DIAGNOSTIC")
print("=" * 70)

# Test 1: Check if module can be imported
print("\n[TEST 1] Checking if graph module can be imported...")
try:
    from teradata_mcp_server.tools.graph import handle_graph_queryDependenciesAgent
    print("✅ SUCCESS: Module imported successfully")
    print(f"   Function: {handle_graph_queryDependenciesAgent.__name__}")
except ImportError as e:
    print(f"❌ FAILED: Cannot import graph module")
    print(f"   Error: {e}")
    sys.exit(1)

# Test 2: Check function signature
print("\n[TEST 2] Checking function signature...")
import inspect
sig = inspect.signature(handle_graph_queryDependenciesAgent)
print(f"✅ Function signature:")
for param_name, param in sig.parameters.items():
    default = f" = {param.default}" if param.default != inspect.Parameter.empty else ""
    print(f"   - {param_name}: {param.annotation}{default}")

# Test 3: Check if server can find the tool
print("\n[TEST 3] Checking if server auto-discovers the tool...")
try:
    # This simulates what the MCP server does
    import importlib
    import pkgutil
    
    # Load the graph module
    graph_module = importlib.import_module('teradata_mcp_server.tools.graph')
    
    # Find all handle_* functions
    handlers = []
    for name in dir(graph_module):
        if name.startswith('handle_'):
            obj = getattr(graph_module, name)
            if callable(obj):
                handlers.append(name)
    
    if handlers:
        print(f"✅ Found {len(handlers)} handler(s):")
        for handler in handlers:
            # Extract tool name (remove 'handle_' prefix)
            tool_name = handler.replace('handle_', '')
            print(f"   - {handler} → tool name: '{tool_name}'")
    else:
        print("❌ No handlers found in graph module")
        sys.exit(1)
        
except Exception as e:
    print(f"❌ FAILED: Error during discovery")
    print(f"   Error: {e}")
    sys.exit(1)

# Test 4: Check profiles.yml
print("\n[TEST 4] Checking profiles.yml configuration...")
try:
    import yaml
    
    if os.path.exists('profiles.yml'):
        with open('profiles.yml', 'r') as f:
            profiles = yaml.safe_load(f)
        
        print("✅ profiles.yml loaded successfully")
        
        # Check if 'all' profile would match
        all_profile = profiles.get('all', {})
        tool_patterns = all_profile.get('tool', [])
        
        print(f"\n   'all' profile tool patterns:")
        for pattern in tool_patterns:
            print(f"   - {pattern}")
        
        # Test if our tool name matches
        import re
        tool_name = "graph_queryDependenciesAgent"
        matched = False
        for pattern in tool_patterns:
            if re.match(pattern, tool_name):
                print(f"\n   ✅ Tool '{tool_name}' MATCHES pattern '{pattern}'")
                matched = True
                break
        
        if not matched:
            print(f"\n   ⚠️  Tool '{tool_name}' does NOT match any patterns in 'all' profile")
            print(f"   💡 Add pattern '^graph_' to enable graph tools")
            
    else:
        print("❌ profiles.yml not found in current directory")
        
except Exception as e:
    print(f"❌ Error reading profiles.yml: {e}")

# Test 5: Check file structure
print("\n[TEST 5] Checking file structure...")
graph_dir = "src/teradata_mcp_server/tools/graph"
required_files = {
    "__init__.py": os.path.join(graph_dir, "__init__.py"),
    "graph_tools.py": os.path.join(graph_dir, "graph_tools.py")
}

all_exist = True
for name, path in required_files.items():
    if os.path.exists(path):
        size = os.path.getsize(path)
        print(f"   ✅ {name}: {size} bytes")
    else:
        print(f"   ❌ {name}: NOT FOUND at {path}")
        all_exist = False

if not all_exist:
    print("\n   💡 Make sure files are in: src/teradata_mcp_server/tools/graph/")

# Summary
print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print("\nIf all tests passed, the tool should be available in Claude when using:")
print("  --profile all")
print("\nTo verify in Claude:")
print("  1. Restart Claude Desktop")
print("  2. Start a new conversation")
print("  3. Ask: 'What tools do you have access to?'")
print("  4. Look for: graph_queryDependenciesAgent")
print("\nIf still not visible, check Claude Desktop logs:")
print("  macOS: ~/Library/Logs/Claude/")
print("  Windows: %APPDATA%\\Claude\\logs\\")
print("=" * 70)
