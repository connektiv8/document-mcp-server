import asyncio
import os
import sys
from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp.server.stdio import stdio_server
from pathlib import Path
from typing import Optional
import json

# Import document stores based on STORE_TYPE environment variable
STORE_TYPE = os.getenv('STORE_TYPE', 'faiss')

if STORE_TYPE == 'postgres':
    from document_store_pg import PgVectorDocumentStore as DocumentStore
else:
    from document_store import FastDocumentStore as DocumentStore

from document_processor import DocumentProcessor

# Initialize components
doc_store = DocumentStore()
doc_processor = DocumentProcessor()

# Create MCP server
app = Server("document-search-server")

@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools"""
    return [
        Tool(
            name="search_documents",
            description="Search through uploaded PDF and DOCX documents using semantic similarity. Returns relevant text chunks from the documents.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to find relevant document chunks"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 5)",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="index_documents",
            description="Index all PDF and DOCX files from the documents folder. This processes the files and makes them searchable.",
            inputSchema={
                "type": "object",
                "properties": {
                    "reindex": {
                        "type": "boolean",
                        "description": "If true, clear existing index and reindex all documents",
                        "default": False
                    }
                }
            }
        ),
        Tool(
            name="get_stats",
            description="Get statistics about the document store (number of indexed chunks, etc.)",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="clear_index",
            description="Clear all indexed documents from the vector store",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls"""
    
    if name == "search_documents":
        query = arguments.get("query", "")
        max_results = arguments.get("max_results", 5)
        
        if not query:
            return [TextContent(type="text", text="Error: query parameter is required")]
        
        results = doc_store.search(query, k=max_results)
        
        if not results:
            return [TextContent(
                type="text",
                text="No results found. Make sure documents are indexed using the 'index_documents' tool."
            )]
        
        # Format results
        response = f"Found {len(results)} relevant chunks:\n\n"
        for i, result in enumerate(results, 1):
            response += f"--- Result {i} (similarity: {result['similarity']:.3f}) ---\n"
            response += f"Source: {result['metadata'].get('source', 'Unknown')}\n"
            text_preview = result['text'][:500]
            if len(result['text']) > 500:
                text_preview += '...'
            response += f"Text: {text_preview}\n\n"
        
        return [TextContent(type="text", text=response)]
    
    elif name == "index_documents":
        reindex = arguments.get("reindex", False)
        
        if reindex:
            doc_store.clear()
        
        docs_path = Path("/app/data/documents")
        files = list(docs_path.glob("*.pdf")) + list(docs_path.glob("*.docx"))
        
        if not files:
            return [TextContent(
                type="text",
                text="No PDF or DOCX files found in /app/data/documents/"
            )]
        
        all_chunks = []
        all_metadata = []
        
        errors = []
        for file in files:
            try:
                chunks, metadata = doc_processor.process_and_chunk(file)
                all_chunks.extend(chunks)
                all_metadata.extend(metadata)
            except Exception as e:
                error_msg = f"Error processing {file.name}: {str(e)}"
                print(error_msg)
                errors.append(error_msg)
        
        if all_chunks:
            doc_store.add_documents(all_chunks, all_metadata)
        
        stats = doc_store.get_stats()
        result_text = f"Indexed {len(files)} files into {stats['total_chunks']} chunks"
        if errors:
            result_text += f"\n\nWarnings:\n" + "\n".join(errors)
        return [TextContent(
            type="text",
            text=result_text
        )]
    
    elif name == "get_stats":
        stats = doc_store.get_stats()
        return [TextContent(
            type="text",
            text=json.dumps(stats, indent=2)
        )]
    
    elif name == "clear_index":
        doc_store.clear()
        return [TextContent(type="text", text="Index cleared successfully")]
    
    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]

async def main():
    """Run the MCP server"""
    mode = os.environ.get('MCP_MODE', 'stdio')
    
    if mode == 'http':
        # HTTP/SSE mode
        from mcp.server.sse import SseServerTransport
        from starlette.applications import Starlette
        from starlette.routing import Route
        import uvicorn
        
        sse = SseServerTransport("/messages")
        
        async def handle_sse(request):
            async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
                await app.run(streams[0], streams[1], app.create_initialization_options())
        
        async def handle_messages(request):
            await sse.handle_post_message(request.scope, request.receive, request._send)
        
        starlette_app = Starlette(
            routes=[
                Route("/sse", endpoint=handle_sse),
                Route("/messages", endpoint=handle_messages, methods=["POST"]),
            ]
        )
        
        port = int(os.environ.get('MCP_PORT', '8000'))
        print(f"Starting MCP server in HTTP mode on port {port}", file=sys.stderr)
        config = uvicorn.Config(starlette_app, host="0.0.0.0", port=port, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()
    else:
        # stdio mode (default)
        async with stdio_server() as (read_stream, write_stream):
            await app.run(
                read_stream,
                write_stream,
                app.create_initialization_options()
            )

if __name__ == "__main__":
    asyncio.run(main())
