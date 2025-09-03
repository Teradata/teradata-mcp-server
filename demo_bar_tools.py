#!/usr/bin/env python3
"""
Demo script showing the BAR tools integration with Teradata MCP Server
"""

import os
import asyncio
import json

# Set up DSA environment variables
os.environ['DSA_HOST'] = 'pe06-dsc-0015.labs.teradata.com'
os.environ['DSA_PORT'] = '9090'
os.environ['DSA_PROTOCOL'] = 'https'
os.environ['DSA_VERIFY_SSL'] = 'false'

from src.teradata_mcp_server.tools.bar.bar_tools import handle_bar_manageDsaDiskFileSystemOperations

def demo_bar_tools():
    """Demonstrate BAR tools functionality"""
    print("🚀 BAR Tools Integration Demo")
    print("=" * 60)
    print(f"DSA Server: https://{os.environ['DSA_HOST']}:{os.environ['DSA_PORT']}")
    print(f"SSL Verify: {os.environ['DSA_VERIFY_SSL']}")
    print("=" * 60)
    
    # Test 1: List disk file systems
    print("\n📋 Test 1: List Disk File Systems")
    print("-" * 40)
    
    try:
        result = handle_bar_manageDsaDiskFileSystemOperations(
            conn=None,
            operation='list'
        )
        
        print(f"✅ Response received successfully!")
        print(f"📊 Result type: {type(result)}")
        print("\n📄 Full Response:")
        print(result)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    demo_bar_tools()
