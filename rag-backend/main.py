"""
RAG Backend Service - FastAPI server that bridges Ollama and Document MCP Server
"""
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
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
    model: str = "llama3.2:3b"
    max_results: int = 3

class ChatResponse(BaseModel):
    response: str
    sources: List[dict]

async def query_mcp_server(query: str, max_results: int = 3):
    """Query the Document MCP Server for relevant chunks"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        # For HTTP mode, we'd use SSE - for simplicity using docker exec approach
        # In production, implement proper SSE client
        import subprocess
        
        cmd = ["docker", "exec", "-i", "document-mcp-server", "python", "src/server.py"]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, 
                               stderr=subprocess.PIPE, text=True, bufsize=1)
        
        # Initialize
        init = {"jsonrpc": "2.0", "id": 0, "method": "initialize", 
                "params": {"protocolVersion": "2024-11-05", "capabilities": {}, 
                          "clientInfo": {"name": "rag-backend", "version": "1.0"}}}
        proc.stdin.write(json.dumps(init) + "\n")
        proc.stdin.flush()
        proc.stdout.readline()
        
        # Search
        search = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", 
                 "params": {"name": "search_documents", 
                           "arguments": {"query": query, "max_results": max_results}}}
        proc.stdin.write(json.dumps(search) + "\n")
        proc.stdin.flush()
        
        response = json.loads(proc.stdout.readline())
        proc.stdin.close()
        proc.terminate()
        
        return response["result"]["content"][0]["text"]

async def query_ollama(prompt: str, model: str = "llama3.2:3b"):
    """Query Ollama for response generation"""
    async with httpx.AsyncClient(timeout=60.0) as client:
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

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Main chat endpoint - RAG pipeline"""
    
    # Step 1: Search for relevant documents
    search_results = await query_mcp_server(request.message, request.max_results)
    
    # Parse sources from search results
    sources = []
    # Extract source information (simplified - you may want to parse more carefully)
    if "Found" in search_results:
        # Extract chunks for context
        context = search_results
    else:
        context = "No relevant documents found."
    
    # Step 2: Build prompt for Ollama
    prompt = f"""You are a helpful assistant that answers questions based on historical mining documents.

User Question: {request.message}

Relevant Document Excerpts:
{context}

Instructions:
- Answer the question based ONLY on the information provided in the excerpts above
- If the excerpts don't contain enough information to answer, say so
- Cite specific details from the excerpts when possible
- Be concise and factual

Answer:"""
    
    # Step 3: Generate response with Ollama
    response = await query_ollama(prompt, request.model)
    
    return ChatResponse(
        response=response,
        sources=[{"text": search_results}]
    )

@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket endpoint for streaming chat"""
    await websocket.accept()
    
    try:
        while True:
            data = await websocket.receive_json()
            message = data.get("message", "")
            model = data.get("model", "llama3.2:3b")
            
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
