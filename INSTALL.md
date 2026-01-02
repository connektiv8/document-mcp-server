# Installation Guide

This guide walks you through setting up and testing the Document MCP Server on your local development machine using Docker Desktop.

## Prerequisites

- Docker Desktop installed and running
- Git (for cloning the repository)
- Basic familiarity with command line/terminal

## Setup Steps

### 1. Create Data Directories

First, create the required directories for storing documents and the vector database:

**PowerShell (Windows):**

```powershell
mkdir -p data/documents, data/vector_store
```

**Bash (Linux/macOS):**

```bash
mkdir -p data/documents data/vector_store
```

### 2. Build the Docker Image

Build the Docker image locally:

```bash
docker build -t document-mcp-server:local .
```

This will:

- Install Python 3.11 and system dependencies
- Install required Python packages (FAISS, sentence-transformers, etc.)
- Download the embedding model (`all-MiniLM-L6-v2`)
- Set up the application structure

**Note:** The first build may take 15-30 minutes as it downloads the embedding model.

### 3. Add Test Documents

Place your PDF or DOCX files in the `data/documents/` folder:

```bash
cp /path/to/your/documents/*.pdf data/documents/
```

Or create a test document using the provided script:

**PowerShell:**

```powershell
# Install reportlab in a virtual environment
python -m venv .venv
.venv\Scripts\activate
pip install reportlab
python create_test_doc.py
```

**Bash:**

```bash
# Install reportlab in a virtual environment
python -m venv .venv
source .venv/bin/activate
pip install reportlab
python create_test_doc.py
```

### 4. Run the Container

#### Option A: Using Docker Compose (Recommended)

Start the container in detached mode:

```bash
docker-compose up -d
```

Stop the container:

```bash
docker-compose down
```

View logs:

```bash
docker logs document-mcp-server
```

#### Option B: Using Docker Run Directly

For interactive testing:

```bash
docker run -i --rm \
  -v ./data/documents:/app/data/documents:ro \
  -v ./data/vector_store:/app/data/vector_store \
  document-mcp-server:local
```

**Windows PowerShell:**

```powershell
docker run -i --rm `
  -v ${PWD}/data/documents:/app/data/documents:ro `
  -v ${PWD}/data/vector_store:/app/data/vector_store `
  document-mcp-server:local
```

### 5. Test the Server

Run the test script to verify the server is working:

```bash
python test_server.py
```

This will:

1. Initialize the MCP connection
2. List available tools
3. Index your documents
4. Get statistics
5. Perform a test search

## Configuring MCP Clients

### Claude Desktop

Add the following to your Claude Desktop configuration:

**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`  
**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`  
**Linux:** `~/.config/Claude/claude_desktop_config.json`

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

**Important:** Replace `/absolute/path/to/` with the actual absolute path to your project directory.

**Windows Example:**

```json
{
  "mcpServers": {
    "document-search": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-v", "c:/localdev/document-mcp-server/data/documents:/app/data/documents:ro",
        "-v", "c:/localdev/document-mcp-server/data/vector_store:/app/data/vector_store",
        "document-mcp-server:local"
      ]
    }
  }
}
```

## Available Tools

Once configured, the following tools will be available in your MCP client:

1. **`index_documents`** - Process and index all PDF/DOCX files from the documents folder
   - Optional parameter: `reindex` (boolean) - Clear and reindex all documents

2. **`search_documents`** - Search indexed documents using semantic similarity
   - Required: `query` (string) - Search query
   - Optional: `max_results` (integer) - Number of results to return (default: 5)

3. **`get_stats`** - Get statistics about indexed documents
   - Returns: Number of chunks, index size, vector dimension

4. **`clear_index`** - Clear all indexed documents from the vector store

## Troubleshooting

### Container won't start

- Ensure Docker Desktop is running
- Check that ports aren't already in use
- Verify volume paths are correct

### No documents indexed

- Ensure PDF/DOCX files are in `data/documents/`
- Check file permissions (files should be readable)
- Run `index_documents` tool with `reindex: true`

### Search returns no results

- Verify documents have been indexed using `get_stats`
- Try a different search query
- Check that the vector store is persisted in `data/vector_store/`

### Performance issues

- Adjust CPU/memory limits in `docker-compose.yml`
- Reduce `chunk_size` in document processor if needed
- Consider indexing fewer documents for testing

## Next Steps

- Add your own documents to `data/documents/`
- Customize chunking parameters in `src/document_processor.py`
- Adjust resource limits in `docker-compose.yml`
- Deploy to production by pushing to a container registry

## Support

For issues or questions, please check the [GitHub repository](https://github.com/connektiv8/document-mcp-server).
