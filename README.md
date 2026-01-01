# Document MCP Server

Fast, CPU-optimized MCP server for searching PDF and DOCX documents using semantic similarity.

## Quick Start

### 1. Build and Push to Registry

```bash
# Build the image
docker build -t your-registry.example.com/document-mcp-server:latest .

# Push to your registry
docker push your-registry.example.com/document-mcp-server:latest
```

### 2. Run the Container

```bash
# Create data directories
mkdir -p data/documents data/vector_store

# Add your PDF/DOCX files to data/documents/

# Run with docker-compose
docker-compose up -d

# Or run directly
docker run -it \
  -v $(pwd)/data/documents:/app/data/documents:ro \
  -v $(pwd)/data/vector_store:/app/data/vector_store \
  your-registry.example.com/document-mcp-server:latest
```

### 3. Use with MCP Client

Configure your MCP client (e.g., Claude Desktop) to connect to the server:

```json
{
  "mcpServers": {
    "document-search": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-v", "/path/to/data/documents:/app/data/documents:ro",
        "-v", "/path/to/data/vector_store:/app/data/vector_store",
        "your-registry.example.com/document-mcp-server:latest"
      ]
    }
  }
}
```

## Available Tools

1. **index_documents**: Process and index all PDF/DOCX files
2. **search_documents**: Search indexed documents
3. **get_stats**: Get indexing statistics
4. **clear_index**: Clear the vector store

## Performance

- ~50-200 documents/sec indexing (CPU-dependent)
- <100ms search queries
- FAISS-optimized for CPU-only servers
