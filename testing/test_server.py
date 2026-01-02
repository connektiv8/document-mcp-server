"""
Direct test of the MCP server by running it in a container
"""
import subprocess
import json
import time

def test_mcp_server():
    print("=== Testing Document MCP Server ===\n")
    
    # Start an interactive container
    print("Starting interactive test container...")
    
    cmd = [
        "docker", "run", "-i", "--rm",
        "-v", r"c:\localdev\document-mcp-server\data\documents:/app/data/documents:ro",
        "-v", r"c:\localdev\document-mcp-server\data\vector_store:/app/data/vector_store",
        "document-mcp-server:local"
    ]
    
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    
    def send_message(method, params=None):
        """Send an MCP JSON-RPC message"""
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
        }
        if params is not None:
            message["params"] = params
        
        msg_str = json.dumps(message) + "\n"
        print(f"\n>>> Sending: {method}")
        proc.stdin.write(msg_str)
        proc.stdin.flush()
        
        # Read response
        response = proc.stdout.readline()
        if response:
            try:
                resp_obj = json.loads(response)
                print(f"<<< Response:")
                print(json.dumps(resp_obj, indent=2))
                return resp_obj
            except json.JSONDecodeError as e:
                print(f"<<< Raw response: {response}")
                return response
        return None
    
    try:
        # Test sequence
        print("\n1. Initialize")
        send_message("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0"}
        })
        
        time.sleep(0.5)
        
        print("\n2. List tools")
        send_message("tools/list")
        
        time.sleep(0.5)
        
        print("\n3. Index documents")
        send_message("tools/call", {
            "name": "index_documents",
            "arguments": {"reindex": True}
        })
        
        time.sleep(2)
        
        print("\n4. Get stats")
        send_message("tools/call", {
            "name": "get_stats",
            "arguments": {}
        })
        
        time.sleep(0.5)
        
        print("\n5. Search documents")
        send_message("tools/call", {
            "name": "search_documents",
            "arguments": {
                "query": "machine learning and NLP",
                "max_results": 3
            }
        })
        
        time.sleep(1)
        
    finally:
        print("\n\n=== Closing connection ===")
        proc.stdin.close()
        proc.wait(timeout=5)
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    test_mcp_server()
