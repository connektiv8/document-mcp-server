# PostgreSQL + pgvector Setup Guide

This guide covers using PostgreSQL with pgvector instead of FAISS for vector storage.

## Why PostgreSQL + pgvector?

**Advantages over FAISS:**
- ✅ **Metadata filtering**: Search within specific years, locations, or document types
- ✅ **Persistent storage**: No need to save/load indexes manually
- ✅ **ACID transactions**: Reliable data operations
- ✅ **SQL queries**: Combine vector search with traditional database queries
- ✅ **Hybrid search**: Filter by metadata, then semantic search

**Example queries:**
- "What gold nuggets were found in Bendigo between 1851-1855?"
- "Show me discoveries in the 1860s"
- "Search documents from Castlemaine only"

## Quick Start

### 1. Start Services with PostgreSQL

```powershell
# Stop FAISS-based services if running
docker-compose -f docker-compose.rag.yml down

# Start PostgreSQL-based services
docker-compose -f docker-compose.pgvector.yml up -d
```

### 2. Wait for PostgreSQL to Initialize

```powershell
# Check if postgres is ready
docker logs mcp-postgres

# Should see: "database system is ready to accept connections"
```

### 3. Index Your Documents

```powershell
# Run indexing script (extracts years and locations automatically)
docker exec -it document-mcp-server python index_documents_pg.py

# Or reindex (clears existing first)
docker exec -it document-mcp-server python index_documents_pg.py --reindex
```

### 4. Download Ollama Model

```powershell
docker exec -it ollama ollama pull llama3.2:1b
```

### 5. Access the Web UI

Open: **http://localhost:3000**

## Architecture

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────────┐
│  React/Vite UI  │───▶│ RAG Backend  │────▶│ Document MCP    │
│  (Port 3000)    │     │  (FastAPI)   │     │ Server          │
└─────────────────┘     │  (Port 8001) │     │ (Port 8000)     │
                        └──────────────┘     └─────────────────┘
                              │                        │
                              ▼                        ▼
                        ┌──────────────┐     ┌─────────────────┐
                        │   Ollama     │     │  PostgreSQL     │
                        │ (Port 11434) │     │  + pgvector     │
                        └──────────────┘     │ (Port 5566)     │
                                             └─────────────────┘
```

## PostgreSQL Access

### Connection Details

- **Host**: localhost
- **Port**: 5566 (external), 5432 (internal)
- **Database**: mcp_documents
- **User**: mcp_user
- **Password**: mcp_password

### Connect from Host Machine

```powershell
# Using psql
psql -h localhost -p 5566 -U mcp_user -d mcp_documents

# Connection string
postgresql://mcp_user:mcp_password@localhost:5566/mcp_documents
```

### Useful SQL Queries

```sql
-- Count documents
SELECT COUNT(*) FROM documents;

-- Count unique files
SELECT COUNT(DISTINCT source_file) FROM documents;

-- View year distribution
SELECT date_year, COUNT(*) 
FROM documents 
WHERE date_year IS NOT NULL 
GROUP BY date_year 
ORDER BY date_year;

-- View location distribution
SELECT location, COUNT(*) 
FROM documents 
WHERE location IS NOT NULL 
GROUP BY location 
ORDER BY COUNT(*) DESC;

-- Search specific year
SELECT content, source_file, date_year 
FROM documents 
WHERE date_year = 1852 
LIMIT 5;

-- Sample data
SELECT id, LEFT(content, 100) as preview, source_file, date_year, location 
FROM documents 
LIMIT 10;
```

## Metadata Extraction

The `index_documents_pg.py` script automatically extracts:

### Year Detection
- Finds years in format 1800-2099
- Stores in `date_year` column
- Example: "In 1852, the Welcome Nugget was found" → date_year: 1852

### Location Detection
- Matches Victorian goldfield locations:
  - Bendigo, Ballarat, Castlemaine, Yea, Beechworth
  - Ararat, Dunolly, Maryborough, Clunes, Stawell
  - Melbourne, Victoria
- Stores in `location` column

## Advanced Search Features

### Using the MCP Server Directly

The pgvector store supports additional search parameters:

```python
# Search with year filter
results = doc_store.search(
    query="gold nuggets",
    k=5,
    date_year=1852
)

# Search with year range
results = doc_store.search(
    query="discoveries",
    k=10,
    date_year_range=(1851, 1855)
)

# Search with location filter
results = doc_store.search(
    query="mining",
    k=5,
    location="Bendigo"
)

# Combine filters
results = doc_store.search(
    query="gold finds",
    k=5,
    date_year_range=(1850, 1860),
    location="Castlemaine"
)
```

## Database Schema

```sql
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    embedding vector(384) NOT NULL,
    source_file TEXT,
    file_type TEXT,
    file_path TEXT,
    chunk_index INTEGER,
    date_year INTEGER,
    location TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX documents_embedding_idx 
    ON documents USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX documents_source_file_idx ON documents(source_file);
CREATE INDEX documents_date_year_idx ON documents(date_year);
CREATE INDEX documents_location_idx ON documents(location);
```

## Performance Tuning

### IVFFlat Index

The vector index uses IVFFlat (Inverted File with Flat quantization):
- Current setting: `lists = 100` (good for <100K vectors)
- Adjust for larger datasets in `document_store_pg.py`

### Resource Limits

Adjust in `docker-compose.pgvector.yml`:
```yaml
postgres:
  deploy:
    resources:
      limits:
        cpus: '2'
        memory: 2G
```

## Backup & Restore

### Backup Database

```powershell
# Backup to file
docker exec mcp-postgres pg_dump -U mcp_user mcp_documents > backup.sql

# Or using docker
docker exec mcp-postgres pg_dump -U mcp_user mcp_documents -f /tmp/backup.sql
docker cp mcp-postgres:/tmp/backup.sql ./backup.sql
```

### Restore Database

```powershell
# Restore from file
docker exec -i mcp-postgres psql -U mcp_user mcp_documents < backup.sql
```

## Troubleshooting

### Connection Errors

```powershell
# Check if PostgreSQL is running
docker ps | grep postgres

# View PostgreSQL logs
docker logs mcp-postgres

# Test connection
docker exec -it mcp-postgres psql -U mcp_user -d mcp_documents -c "\dt"
```

### Indexing Issues

```powershell
# Check MCP server logs
docker logs document-mcp-server

# Verify Python can connect
docker exec -it document-mcp-server python -c "
from document_store_pg import PgVectorDocumentStore
store = PgVectorDocumentStore()
print(store.get_stats())
"
```

### Reset Everything

```powershell
# Stop services
docker-compose -f docker-compose.pgvector.yml down

# Remove volumes (WARNING: deletes all data)
docker-compose -f docker-compose.pgvector.yml down -v

# Start fresh
docker-compose -f docker-compose.pgvector.yml up -d
```

## Switching Between FAISS and PostgreSQL

### FAISS version:
```powershell
docker-compose -f docker-compose.rag.yml up -d
```

### PostgreSQL version:
```powershell
docker-compose -f docker-compose.pgvector.yml up -d
```

Both use the same frontend and backend, just different vector storage.

## See Also

- [RAG-SETUP.md](RAG-SETUP.md) - General RAG system setup
- [INSTALL.md](INSTALL.md) - Initial installation
- [QUERYING.md](QUERYING.md) - MCP querying guide
