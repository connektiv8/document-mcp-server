import asyncio
from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp.server.stdio import stdio_server
from pathlib import Path
from typing import Optional
import json

from document_store import FastDocumentStore
from document_processor import DocumentProcessor
from geo_tools import GeoTools
from claim_parser import ClaimParser

# Initialize components
doc_store = FastDocumentStore()
doc_processor = DocumentProcessor()
geo_tools = GeoTools()
claim_parser = ClaimParser()

# Default region for geocoding
DEFAULT_REGION = "California, USA"

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
        ),
        Tool(
            name="locate_mining_claim",
            description="Parse a mining claim description and calculate its GPS coordinates. Extracts location data from natural language, geocodes reference points, and returns geospatial data in GeoJSON format for use with external mapping systems.",
            inputSchema={
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "Natural language description of claim location (e.g., '2 miles northwest of Deadwood following Whitewood Creek')"
                    },
                    "region": {
                        "type": "string",
                        "description": "Geographic region for geocoding context (e.g., 'South Dakota, USA')",
                        "default": DEFAULT_REGION
                    }
                },
                "required": ["description"]
            }
        ),
        Tool(
            name="map_all_claims",
            description="Search documents for mining claims and locate them all automatically. Performs document search, parses all matching claims, and returns combined geospatial data in GeoJSON format.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query to find relevant claim documents (e.g., 'mining claim location')"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of claims to process (default: 10)",
                        "default": 10
                    }
                },
                "required": ["query"]
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
    
    elif name == "locate_mining_claim":
        description = arguments.get("description", "")
        region = arguments.get("region", DEFAULT_REGION)
        
        if not description:
            return [TextContent(type="text", text="Error: description parameter is required")]
        
        # Parse the claim description using LLM
        print("Parsing claim description...")
        parsed_data = claim_parser.parse_claim_description(description)
        
        if not parsed_data or 'error' in parsed_data:
            error_msg = parsed_data.get('error', 'Failed to parse claim description') if parsed_data else 'Failed to parse claim description'
            return [TextContent(type="text", text=f"Error parsing claim: {error_msg}")]
        
        # Extract parsed fields
        claim_name = parsed_data.get('claim_name') or 'Unknown Claim'
        reference_location = parsed_data.get('reference_location')
        direction = parsed_data.get('direction')
        distance = parsed_data.get('distance')
        distance_unit = parsed_data.get('distance_unit', 'miles')
        natural_feature = parsed_data.get('natural_feature')
        feature_type = parsed_data.get('feature_type', 'waterway')
        
        if not reference_location:
            return [TextContent(type="text", text="Error: Could not extract reference location from description")]
        
        # Geocode reference location
        print(f"Geocoding reference location: {reference_location}")
        ref_coords = geo_tools.geocode(reference_location, region)
        
        if not ref_coords:
            return [TextContent(type="text", text=f"Error: Could not geocode reference location '{reference_location}' in region '{region}'")]
        
        reference_point = {
            'name': reference_location,
            'latitude': ref_coords['latitude'],
            'longitude': ref_coords['longitude']
        }
        
        # Calculate claim coordinates if direction and distance provided
        if direction and distance:
            # Convert distance to miles
            distance_miles = geo_tools.convert_distance_to_miles(float(distance), distance_unit)
            
            # Convert direction to bearing
            bearing = geo_tools.cardinal_to_bearing(direction)
            
            # Calculate claim center
            claim_lat, claim_lon = geo_tools.calculate_destination(
                ref_coords['latitude'],
                ref_coords['longitude'],
                bearing,
                distance_miles
            )
        else:
            # If no direction/distance, use reference location as claim location
            claim_lat = ref_coords['latitude']
            claim_lon = ref_coords['longitude']
        
        # Generate claim boundary (160 acres default)
        boundary = geo_tools.generate_claim_boundary(claim_lat, claim_lon, acres=160)
        
        # Find nearby natural features if specified
        features = []
        if natural_feature and feature_type:
            print(f"Searching for nearby {feature_type} features...")
            features = geo_tools.find_nearby_features(claim_lat, claim_lon, feature_type)
        
        # Prepare claim data
        claim_data = {
            'name': claim_name,
            'latitude': claim_lat,
            'longitude': claim_lon,
            'boundary': boundary,
            'acres': 160
        }
        
        # Generate GeoJSON
        print("Formatting geospatial data...")
        geojson_data = geo_tools.format_geojson(
            claims=[claim_data],
            reference_points=[reference_point],
            features=features
        )
        
        # Generate response
        google_maps_link = geo_tools.get_google_maps_link(claim_lat, claim_lon)
        
        response = f"""Mining Claim Location Analysis
=====================================

Claim Name: {claim_name}

Parsed Information:
- Reference Location: {reference_location}
- Direction: {direction or 'N/A'}
- Distance: {distance} {distance_unit if distance else 'N/A'}
- Natural Feature: {natural_feature or 'None specified'}

Calculated Coordinates:
- Latitude: {claim_lat:.6f}°
- Longitude: {claim_lon:.6f}°

Reference Point:
- {reference_location}: {ref_coords['latitude']:.6f}°, {ref_coords['longitude']:.6f}°

Nearby Natural Features Found: {len(features)}"""
        
        if features:
            response += "\n\nFeatures:"
            for feat in features[:5]:
                response += f"\n- {feat['name']} ({feat['type']}): {feat['latitude']:.6f}°, {feat['longitude']:.6f}°"
        
        response += f"""

Claim Boundary: 160 acres (rectangular polygon)
Google Maps Link: {google_maps_link}

GeoJSON Data:
{json.dumps(geojson_data, indent=2)}

The GeoJSON data includes:
- Claim boundary polygon (red)
- Claim center point marker (red)
- Reference point marker (blue)
- Natural feature markers (green)

This data can be loaded into your existing OSM-based map server."""
        
        return [TextContent(type="text", text=response)]
    
    elif name == "map_all_claims":
        query = arguments.get("query", "")
        max_results = arguments.get("max_results", 10)
        
        if not query:
            return [TextContent(type="text", text="Error: query parameter is required")]
        
        # Search for claim documents
        print(f"Searching for claims with query: {query}")
        search_results = doc_store.search(query, k=max_results)
        
        if not search_results:
            return [TextContent(type="text", text="No claim documents found for the given query")]
        
        # Parse all claim descriptions
        descriptions = [result['text'] for result in search_results]
        print(f"Parsing {len(descriptions)} claim descriptions...")
        parsed_claims = claim_parser.parse_batch(descriptions)
        
        # Process each claim and collect valid ones
        valid_claims = []
        failed_claims = []
        
        for i, parsed_claim in enumerate(parsed_claims):
            if not parsed_claim['success']:
                failed_claims.append({
                    'index': i + 1,
                    'error': parsed_claim.get('error', 'Unknown error')
                })
                continue
            
            parsed_data = parsed_claim['parsed']
            
            # Extract fields
            claim_name = parsed_data.get('claim_name') or f'Claim {i+1}'
            reference_location = parsed_data.get('reference_location')
            direction = parsed_data.get('direction')
            distance = parsed_data.get('distance')
            distance_unit = parsed_data.get('distance_unit', 'miles')
            
            if not reference_location:
                failed_claims.append({
                    'index': i + 1,
                    'claim_name': claim_name,
                    'error': 'No reference location found'
                })
                continue
            
            # Geocode reference location
            ref_coords = geo_tools.geocode(reference_location, DEFAULT_REGION)
            
            if not ref_coords:
                failed_claims.append({
                    'index': i + 1,
                    'claim_name': claim_name,
                    'error': f'Could not geocode: {reference_location}'
                })
                continue
            
            # Calculate claim coordinates
            if direction and distance:
                # Convert distance to miles
                distance_miles = geo_tools.convert_distance_to_miles(float(distance), distance_unit)
                
                bearing = geo_tools.cardinal_to_bearing(direction)
                claim_lat, claim_lon = geo_tools.calculate_destination(
                    ref_coords['latitude'],
                    ref_coords['longitude'],
                    bearing,
                    distance_miles
                )
            else:
                claim_lat = ref_coords['latitude']
                claim_lon = ref_coords['longitude']
            
            # Generate boundary
            boundary = geo_tools.generate_claim_boundary(claim_lat, claim_lon, acres=160)
            
            valid_claims.append({
                'name': claim_name,
                'latitude': claim_lat,
                'longitude': claim_lon,
                'boundary': boundary,
                'acres': 160
            })
        
        if not valid_claims:
            return [TextContent(type="text", text="Error: No claims could be successfully geocoded")]
        
        # Generate GeoJSON for all claims
        print(f"Formatting geospatial data for {len(valid_claims)} claims...")
        geojson_data = geo_tools.format_geojson(claims=valid_claims)
        
        # Generate response
        response = f"""Batch Mining Claim Mapping
==========================

Successfully located: {len(valid_claims)} claims
Failed to locate: {len(failed_claims)} claims

Valid Claims:"""
        
        for i, claim in enumerate(valid_claims, 1):
            response += f"\n{i}. {claim['name']}: {claim['latitude']:.6f}°, {claim['longitude']:.6f}°"
        
        if failed_claims:
            response += "\n\nFailed Claims:"
            for fail in failed_claims:
                claim_name = fail.get('claim_name', f"Claim {fail['index']}")
                response += f"\n- {claim_name}: {fail['error']}"
        
        response += f"""

GeoJSON Data:
{json.dumps(geojson_data, indent=2)}

The GeoJSON data includes markers and boundaries for all successfully located claims.
This data can be loaded into your existing OSM-based map server."""
        
        return [TextContent(type="text", text=response)]
    
    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]

async def main():
    """Run the MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())
