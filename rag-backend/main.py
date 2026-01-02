"""
RAG Backend Service - FastAPI server that bridges Ollama and Document MCP Server
"""
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import httpx
import json
import asyncio
from typing import List, Optional
import os

app = FastAPI(title="RAG Backend Service")

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://document-mcp-server:8000")

class ChatRequest(BaseModel):
    message: str
    model: str = "llama3.2:1b"  # Use available model
    max_results: int = 3

class ChatResponse(BaseModel):
    response: str
    sources: List[dict]

async def query_mcp_server(query: str, max_results: int = 3):
    """Query the Document MCP Server for relevant chunks via HTTP"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{MCP_SERVER_URL}/search",
                json={
                    "query": query,
                    "max_results": max_results
                }
            )
            response.raise_for_status()
            data = response.json()
            
            if not data.get('success') or not data.get('results'):
                return "No relevant documents found."
            
            # Format results into readable text
            results = data['results']
            formatted = f"Found {len(results)} relevant document chunks:\n\n"
            for i, result in enumerate(results, 1):
                formatted += f"[Chunk {i}]\n"
                formatted += f"{result['text']}\n"
                if 'metadata' in result and result['metadata']:
                    meta = result['metadata']
                    if 'source_file' in meta:
                        formatted += f"Source: {meta['source_file']}\n"
                    if 'date_year' in meta:
                        formatted += f"Year: {meta['date_year']}\n"
                    if 'location' in meta:
                        formatted += f"Location: {meta['location']}\n"
                formatted += "\n"
            
            return formatted
            
        except Exception as e:
            print(f"Error querying MCP server: {e}")
            return f"Error searching documents: {str(e)}"

async def query_ollama(prompt: str, model: str = "llama3.2:1b"):
    """Query Ollama for response generation"""
    async with httpx.AsyncClient(timeout=300.0) as client:  # 5 minute timeout for slow models
        response = await client.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False
            }
        )
        return response.json()["response"]

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}

@app.get("/models")
async def list_models():
    """List available Ollama models"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{OLLAMA_URL}/api/tags")
            return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat")
async def chat(request: ChatRequest):
    """Main chat endpoint - RAG pipeline with streaming"""
    from starlette.responses import StreamingResponse
    
    async def generate():
        try:
            # Step 1: Search for relevant documents
            search_results = await query_mcp_server(request.message, request.max_results)
            
            # Step 2: Build prompt for Ollama
            prompt = f"""You are a helpful assistant that answers questions based on historical mining documents.

User Question: {request.message}

Relevant Document Excerpts:
{search_results}

Instructions:
- Answer the question based ONLY on the information provided in the excerpts above
- If the excerpts don't contain enough information to answer, say so
- Cite specific details from the excerpts when possible
- Be concise and factual

Answer:"""

            # Step 3: Stream response from Ollama
            async with httpx.AsyncClient(timeout=300.0) as client:
                async with client.stream(
                    "POST",
                    f"{OLLAMA_URL}/api/generate",
                    json={
                        "model": request.model,
                        "prompt": prompt,
                        "stream": True
                    }
                ) as response:
                    async for line in response.aiter_lines():
                        if line:
                            try:
                                chunk = json.loads(line)
                                if "response" in chunk and chunk["response"]:
                                    # Send each token as SSE
                                    yield f"data: {json.dumps({'token': chunk['response']})}\n\n"
                                if chunk.get("done", False):
                                    # Send done signal with sources
                                    yield f"data: {json.dumps({'done': True, 'sources': [search_results]})}\n\n"
                            except json.JSONDecodeError:
                                continue
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")

@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket endpoint for streaming chat"""
    await websocket.accept()
    
    try:
        while True:
            data = await websocket.receive_json()
            message = data.get("message", "")
            model = data.get("model", "llama3.2:1b")
            
            # Search documents
            await websocket.send_json({"type": "status", "message": "Searching documents..."})
            search_results = await query_mcp_server(message)
            
            # Build prompt
            prompt = f"""You are a helpful assistant that answers questions based on historical mining documents.

User Question: {message}

Relevant Document Excerpts:
{search_results}

Answer based on the excerpts:"""
            
            # Stream response from Ollama
            await websocket.send_json({"type": "status", "message": "Generating response..."})
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream(
                    "POST",
                    f"{OLLAMA_URL}/api/generate",
                    json={"model": model, "prompt": prompt, "stream": True}
                ) as response:
                    async for line in response.aiter_lines():
                        if line:
                            chunk = json.loads(line)
                            if "response" in chunk:
                                await websocket.send_json({
                                    "type": "token",
                                    "content": chunk["response"]
                                })
            
            await websocket.send_json({"type": "done"})
            
    except Exception as e:
        await websocket.send_json({"type": "error", "message": str(e)})
        await websocket.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
