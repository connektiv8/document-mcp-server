# Querying the Document MCP Server

This guide explains how to query the Document MCP Server directly using various methods.

## Method 1: Using Docker Exec (Direct MCP Protocol)

This method sends JSON-RPC messages directly to the MCP server running in the container.

### Basic Query Script

```python
import subprocess
import json

# Connect to the running container
cmd = ["docker", "exec", "-i", "document-mcp-server", "python", "src/server.py"]
proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, 
                       stderr=subprocess.PIPE, text=True, bufsize=1)

# Initialize the MCP connection
init_msg = {
    "jsonrpc": "2.0",
    "id": 0,
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "my-client", "version": "1.0"}
    }
}
proc.stdin.write(json.dumps(init_msg) + "\n")
proc.stdin.flush()
proc.stdout.readline()  # Read init response

# Search documents
search_msg = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
        "name": "search_documents",
        "arguments": {
            "query": "your search query here",
            "max_results": 5
        }
    }
}
proc.stdin.write(json.dumps(search_msg) + "\n")
proc.stdin.flush()

# Get response
response = json.loads(proc.stdout.readline())
print(response["result"]["content"][0]["text"])

# Close
proc.stdin.close()
proc.terminate()
```

### Command Line One-Liner (PowerShell)

```powershell
# Quick search
python -c "import subprocess, json; proc = subprocess.Popen(['docker', 'exec', '-i', 'document-mcp-server', 'python', 'src/server.py'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1); proc.stdin.write(json.dumps({'jsonrpc': '2.0', 'id': 0, 'method': 'initialize', 'params': {'protocolVersion': '2024-11-05', 'capabilities': {}, 'clientInfo': {'name': 'cli', 'version': '1.0'}}}) + '\n'); proc.stdin.flush(); proc.stdout.readline(); proc.stdin.write(json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call', 'params': {'name': 'search_documents', 'arguments': {'query': 'gold nuggets', 'max_results': 3}}}) + '\n'); proc.stdin.flush(); print(json.loads(proc.stdout.readline())['result']['content'][0]['text'])"
```

## Method 2: Using the HTTP/SSE Endpoint

If you're running the HTTP version (`docker-compose -f docker-compose.http.yml up`):

### Python HTTP Client

```python
import requests
import json
import sseclient

# Connect to SSE endpoint
response = requests.get('http://localhost:8000/sse', stream=True)
client = sseclient.SSEClient(response)

session_id = None
for event in client.events():
    if event.event == 'endpoint':
        # Extract session ID from endpoint data
        session_id = event.data.split('session_id=')[1]
        break

# Send search request
if session_id:
    search_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "search_documents",
            "arguments": {
                "query": "gold mining",
                "max_results": 3
            }
        }
    }
    
    requests.post(
        f'http://localhost:8000/messages?session_id={session_id}',
        json=search_request
    )
```

## Available MCP Tools

### 1. search_documents

Search through indexed documents using semantic similarity.

**Parameters:**

- `query` (string, required): The search query
- `max_results` (integer, optional): Number of results to return (default: 5)

**Example:**

```json
{
  "name": "search_documents",
  "arguments": {
    "query": "largest gold nuggets found",
    "max_results": 3
  }
}
```

### 2. index_documents

Index all PDF and DOCX files from the documents folder.

**Parameters:**

- `reindex` (boolean, optional): Clear existing index and reindex (default: false)
- `files` (array of strings, optional): Specific files to index (if omitted, indexes all)

**Example:**

```json
{
  "name": "index_documents",
  "arguments": {
    "reindex": true,
    "files": ["doc1.pdf", "doc2.docx"]
  }
}
```

### 3. get_stats

Get statistics about the document store.

**Parameters:** None

**Example:**

```json
{
  "name": "get_stats",
  "arguments": {}
}
```

### 4. clear_index

Clear all indexed documents from the vector store.

**Parameters:** None

**Example:**

```json
{
  "name": "clear_index",
  "arguments": {}
}
```

## Using the Provided Query Script

A simple query script is provided: `chat_query.py`

```bash
# Basic usage
python chat_query.py "your search query"

# Example
python chat_query.py "What gold nuggets were found in Bendigo?"
```

## Response Format

Responses follow the JSON-RPC 2.0 format:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "Found 3 relevant chunks:\n\n--- Result 1 (similarity: 0.543) ---\n..."
      }
    ],
    "isError": false
  }
}
```

## Troubleshooting

### Container not running

```bash
docker ps | grep document-mcp-server
# If not running:
docker-compose up -d
```

### No results found

```bash
# Check if documents are indexed
python chat_query.py "get stats"

# Or reindex
docker exec -i document-mcp-server python src/server.py << EOF
{"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "cli", "version": "1.0"}}}
{"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "index_documents", "arguments": {"reindex": true}}}
EOF
```

### Check server logs

```bash
docker logs document-mcp-server --tail 50
```

## Integration Examples

### With Copilot/AI Assistants

AI assistants can query the server using the docker exec method shown above. The server returns relevant document chunks that can be used for RAG (Retrieval Augmented Generation).

### With Claude Desktop

Add to `claude_desktop_config.json`:

**Stdio mode (default):**

```json
{
  "mcpServers": {
    "document-search": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-v", "/absolute/path/to/data/documents:/app/data/documents:ro",
        "-v", "/absolute/path/to/data/vector_store:/app/data/vector_store",
        "document-mcp-server:local"
      ]
    }
  }
}
```

**HTTP mode:**

```json
{
  "mcpServers": {
    "document-search": {
      "url": "http://localhost:8000/sse"
    }
  }
}
```

### With Ollama (RAG)

See `ollama_chat.py` for a complete conversational interface that:

1. Takes your questions
2. Queries the MCP server for relevant documents
3. Uses Ollama to generate natural language answers

```bash
python ollama_chat.py
```

## Performance Notes

- **Search latency:** <100ms for most queries
- **Indexing speed:** ~50-200 documents/sec (CPU-dependent)
- **Memory usage:** ~2GB base + document corpus
- **Concurrent queries:** Supported via HTTP mode

## See Also

- [INSTALL.md](INSTALL.md) - Installation and setup guide
- [README.md](README.md) - Project overview
- `test_few_docs.py` - Testing script example
- `ollama_chat.py` - Conversational RAG interface
