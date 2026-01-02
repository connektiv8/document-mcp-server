#!/usr/bin/env python3
"""
Simple test client for the Document MCP Server
This script sends MCP protocol messages to test the server functionality
"""
import json
import sys

def send_mcp_message(method: str, params: dict = None):
    """Send an MCP JSON-RPC 2.0 message"""
    message = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
    }
    if params:
        message["params"] = params
    
    print(json.dumps(message), flush=True)

def main():
    print("=== Testing Document MCP Server ===\n", file=sys.stderr)
    
    # 1. Initialize the connection
    print("1. Initializing connection...", file=sys.stderr)
    send_mcp_message("initialize", {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {
            "name": "test-client",
            "version": "1.0.0"
        }
    })
    
    # Wait for response
    response = input()
    print(f"   Response: {response[:100]}...\n", file=sys.stderr)
    
    # 2. List available tools
    print("2. Listing available tools...", file=sys.stderr)
    send_mcp_message("tools/list")
    response = input()
    print(f"   Response: {response[:200]}...\n", file=sys.stderr)
    
    # 3. Index documents
    print("3. Indexing documents...", file=sys.stderr)
    send_mcp_message("tools/call", {
        "name": "index_documents",
        "arguments": {"reindex": True}
    })
    response = input()
    print(f"   Response: {response}\n", file=sys.stderr)
    
    # 4. Get stats
    print("4. Getting stats...", file=sys.stderr)
    send_mcp_message("tools/call", {
        "name": "get_stats",
        "arguments": {}
    })
    response = input()
    print(f"   Response: {response}\n", file=sys.stderr)
    
    # 5. Search documents
    print("5. Searching for 'machine learning'...", file=sys.stderr)
    send_mcp_message("tools/call", {
        "name": "search_documents",
        "arguments": {
            "query": "machine learning and document search",
            "max_results": 3
        }
    })
    response = input()
    print(f"   Response: {response}\n", file=sys.stderr)
    
    print("\n=== Test Complete ===", file=sys.stderr)

if __name__ == "__main__":
    main()
