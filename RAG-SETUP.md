# RAG System - Full Stack Setup

Complete RAG (Retrieval Augmented Generation) system with React frontend, FastAPI backend, Ollama LLM, and Document MCP Server.

## Architecture

```text
┌─────────────────┐     ┌──────────────┐     ┌─────────────────┐
│  React/Vite UI  │───▶│ RAG Backend  │────▶│ Document MCP    │
│  (Port 3000)    │     │  (FastAPI)   │     │ Server          │
└─────────────────┘     │  (Port 8001) │     │ (Port 8000)     │
                        └──────────────┘     └─────────────────┘
                              │                        
                              ▼                        
                        ┌──────────────┐              
                        │   Ollama     │              
                        │ (Port 11434) │              
                        └──────────────┘              
```

## Quick Start

### 1. Build and Start All Services

```bash
# Build images
docker-compose -f docker-compose.rag.yml build

# Start all services
docker-compose -f docker-compose.rag.yml up -d
```

### 2. Download an Ollama Model

```bash
# Pull a small model (recommended for CPU)
docker exec -it ollama ollama pull llama3.2:3b

# Or an even smaller model
docker exec -it ollama ollama pull llama3.2:1b

# Or Qwen 2.5
docker exec -it ollama ollama pull qwen2.5:3b
```

### 3. Index Your Documents

```bash
# Make sure documents are in data/documents/
# Then index them (using test script for now)
python test_few_docs.py
```

### 4. Access the Web UI

Open your browser to: **http://localhost:3000**

## Services

### Frontend (Port 3000)

- React + TypeScript + Vite
- Modern chat interface
- Real-time streaming responses
- Source viewing

### Backend (Port 8001)

- FastAPI REST API
- Bridges Ollama and MCP Server
- RAG pipeline orchestration

### Document MCP Server (Port 8000)

- Semantic document search
- FAISS vector store
- PDF/DOCX processing

### Ollama (Port 11434)

- Local LLM inference
- Multiple model support
- CPU-optimized

## Usage

### Web Interface

1. Open http://localhost:3000
2. Select your preferred model
3. Ask questions about your documents
4. View sources used for answers

### API Usage

```bash
# Direct API call
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What gold nuggets were found?",
    "model": "llama3.2:3b",
    "max_results": 3
  }'
```

### Available Models

After pulling models, you can select from:
- `llama3.2:3b` - Good balance (3B params)
- `llama3.2:1b` - Fastest (1B params)
- `qwen2.5:3b` - Alternative (3B params)
- `phi3:mini` - Microsoft's small model

## Configuration

### Environment Variables

**rag-backend/.env:**
```bash
OLLAMA_URL=http://ollama:11434
MCP_SERVER_URL=http://document-mcp-server:8000
```

**rag-frontend/.env:**
```bash
VITE_API_URL=http://localhost:8001
```

### Resource Limits

Edit `docker-compose.rag.yml` to adjust:
- CPU limits
- Memory limits
- Port mappings

## Development Mode

### Frontend Development
```bash
cd rag-frontend
npm install
npm run dev  # Runs on port 3000
```

### Backend Development
```bash
cd rag-backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8001
```

## Troubleshooting

### Check Service Status
```bash
docker-compose -f docker-compose.rag.yml ps
```

### View Logs
```bash
# All services
docker-compose -f docker-compose.rag.yml logs -f

# Specific service
docker logs rag-backend -f
docker logs ollama -f
docker logs document-mcp-server -f
```

### Restart Services
```bash
# All services
docker-compose -f docker-compose.rag.yml restart

# Specific service
docker-compose -f docker-compose.rag.yml restart rag-backend
```

### Model Not Found
```bash
# List downloaded models
docker exec -it ollama ollama list

# Pull a model
docker exec -it ollama ollama pull llama3.2:3b
```

### No Search Results
```bash
# Check document stats
curl http://localhost:8000/stats

# Reindex documents
# (Use test_few_docs.py or similar)
```

## Performance Tips

1. **For CPU-only machines**: Use smaller models (1B-3B parameters)
2. **Memory**: Allocate at least 8GB for Ollama
3. **Documents**: Index only what you need for faster responses
4. **Chunks**: Default 512 tokens - adjust in document_processor.py

## Stopping the System

```bash
# Stop all services
docker-compose -f docker-compose.rag.yml down

# Stop and remove volumes
docker-compose -f docker-compose.rag.yml down -v
```

## Advanced

### Custom Prompts

Edit `rag-backend/main.py` to customize the prompt template used for RAG.

### Streaming Responses

The backend supports WebSocket streaming at `ws://localhost:8001/ws/chat`

### Adding More Models

```bash
# Check available models at ollama.ai/library
docker exec -it ollama ollama pull <model-name>
```

## See Also

- [INSTALL.md](INSTALL.md) - Initial setup
- [QUERYING.md](QUERYING.md) - Direct MCP queries
- [README.md](README.md) - Project overview
