"""
Test the running docker-compose container
"""
import subprocess
import json
import time

def test_container():
    print("=== Testing Running Container (document-mcp-server) ===\n")
    
    # Connect to the running container
    cmd = ["docker", "exec", "-i", "document-mcp-server", "python", "src/server.py"]
    
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    
    def send_and_receive(method, params=None):
        """Send MCP message and receive response"""
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
        }
        if params is not None:
            message["params"] = params
        
        msg_str = json.dumps(message) + "\n"
        print(f">>> {method}")
        proc.stdin.write(msg_str)
        proc.stdin.flush()
        
        response = proc.stdout.readline()
        if response:
            try:
                resp_obj = json.loads(response)
                print(json.dumps(resp_obj, indent=2))
                return resp_obj
            except json.JSONDecodeError:
                print(f"Raw: {response}")
                return None
        return None
    
    try:
        print("1. Initialize")
        send_and_receive("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "1.0"}
        })
        
        print("\n2. List tools")
        send_and_receive("tools/list")
        
        print("\n3. Index documents")
        send_and_receive("tools/call", {
            "name": "index_documents",
            "arguments": {"reindex": True}
        })
        
        time.sleep(2)
        
        print("\n4. Get stats")
        send_and_receive("tools/call", {
            "name": "get_stats",
            "arguments": {}
        })
        
        print("\n5. Search for 'machine learning'")
        result = send_and_receive("tools/call", {
            "name": "search_documents",
            "arguments": {
                "query": "machine learning semantic search",
                "max_results": 2
            }
        })
        
    finally:
        proc.stdin.close()
        
        # Read any stderr output
        stderr_output = proc.stderr.read()
        if stderr_output:
            print("\n=== Stderr (logging) ===")
            print(stderr_output)
        
        proc.wait(timeout=5)
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    test_container()
