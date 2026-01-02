# Geospatial Capabilities

This document describes the geospatial features for locating and mapping historical mining claims based on natural language descriptions.

## Overview

The document-mcp-server now includes geospatial capabilities that allow you to:

1. Parse mining claim descriptions from text documents
2. Extract location information (reference points, directions, distances)
3. Calculate GPS coordinates using OpenStreetMap data
4. Generate claim boundary polygons
5. Find nearby natural features
6. Output geospatial data in GeoJSON format for use with external mapping systems

**Note**: This MCP server provides geospatial data only. Map rendering should be handled by your separate OSM-based map server.

## Available Tools

### 1. `locate_mining_claim`

Parse a single mining claim description and calculate its GPS coordinates, returning structured geospatial data.

**Input Parameters:**
- `description` (required): Natural language description of the claim location
- `region` (optional): Geographic region for geocoding context (default: "California, USA")

**Example Usage:**

```json
{
  "name": "locate_mining_claim",
  "arguments": {
    "description": "The Johnson Lode claim is situated approximately 2 miles northwest of Deadwood, South Dakota, following Whitewood Creek upstream",
    "region": "South Dakota, USA"
  }
}
```

**Output:**
- Parsed claim information (name, reference location, direction, distance)
- Calculated GPS coordinates
- List of nearby natural features (if mentioned)
- GeoJSON data for use with your map server
- Google Maps verification link

**Example Output:**

```
Mining Claim Location Analysis
=====================================

Claim Name: Johnson Lode

Parsed Information:
- Reference Location: Deadwood
- Direction: northwest
- Distance: 2 miles
- Natural Feature: Whitewood Creek

Calculated Coordinates:
- Latitude: 44.398900°
- Longitude: -103.754200°

Reference Point:
- Deadwood: 44.376900°, -103.729400°

Nearby Natural Features Found: 3

Features:
- Whitewood Creek (waterway): 44.395600°, -103.748900°
- Strawberry Creek (waterway): 44.401200°, -103.756700°

Claim Boundary: 160 acres (rectangular polygon)
Google Maps Link: https://www.google.com/maps?q=44.398900,-103.754200

GeoJSON Data:
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Polygon",
        "coordinates": [[...]]
      },
      "properties": {
        "type": "claim_boundary",
        "name": "Johnson Lode",
        "center_lat": 44.398900,
        "center_lon": -103.754200,
        "acres": 160
      }
    },
    ...
  ]
}

The GeoJSON data includes:
- Claim boundary polygon (red)
- Claim center point marker (red)
- Reference point marker (blue)
- Natural feature markers (green)

This data can be loaded into your existing OSM-based map server.
```

### 2. `map_all_claims`

Search documents for mining claims and automatically locate them all, returning combined geospatial data.

**Input Parameters:**
- `query` (required): Search query to find relevant claim documents
- `max_results` (optional): Maximum number of claims to process (default: 10)

**Example Usage:**

```json
{
  "name": "map_all_claims",
  "arguments": {
    "query": "mining claim location",
    "max_results": 15
  }
}
```

**Output:**
- Count of successfully located claims
- Combined GeoJSON data for all claims
- List of any failed geocoding attempts

**Example Output:**

```
Batch Mining Claim Mapping
==========================

Successfully located: 12 claims
Failed to locate: 3 claims

Valid Claims:
1. Johnson Lode: 44.398900°, -103.754200°
2. Silver King: 38.207500°, -119.012300°
3. Lucky Strike: 39.301200°, -119.645800°
...

Failed Claims:
- Unknown Claim: No reference location found
- Mountain View: Could not geocode: Mountain Peak
- Old Mine #3: No reference location found

GeoJSON Data:
{
  "type": "FeatureCollection",
  "features": [...]
}

The GeoJSON data includes markers and boundaries for all successfully located claims.
This data can be loaded into your existing OSM-based map server.
```

## How It Works

### 1. Natural Language Parsing

The system uses OpenAI's GPT-4-turbo to extract structured location data from claim descriptions. It identifies:

- **Claim name**: Name of the mining claim
- **Reference location**: Known landmark or town (e.g., "Deadwood")
- **Direction**: Cardinal direction (N, NE, E, SE, S, SW, W, NW)
- **Distance**: Numeric distance value
- **Distance unit**: miles, kilometers, feet, etc.
- **Natural features**: Creeks, rivers, mountains, ridges
- **Feature relationships**: upstream, downstream, along, near

### 2. Geocoding

Reference locations are converted to GPS coordinates using the **Nominatim API** (OpenStreetMap's geocoding service).

- Respects rate limits (1 request per second)
- Caches results to minimize API calls
- Uses regional context for accurate results

### 3. Coordinate Calculation

Claim coordinates are calculated using geodesic (great circle) calculations:

1. Convert cardinal direction to bearing (0-360°)
2. Apply distance from reference point
3. Use WGS84 coordinate system (EPSG:4326)
4. Output precision: 6 decimal places (~0.1 meters)

### 4. Boundary Generation

Mining claim boundaries are generated as rectangular polygons:

- Default size: 160 acres (standard historical claim size)
- Calculated as approximate squares around the center point
- Returns closed polygon (first point repeated)
- Output as GeoJSON Polygon geometry

### 5. Natural Feature Discovery

The system can find nearby features using the **Overpass API**:

- Searches within configurable radius (default: 5km)
- Supports waterways (rivers, streams, creeks)
- Supports peaks and mountains
- Supports roads and trails
- Returns up to 10 features with names and coordinates

### 6. GeoJSON Output

All geospatial data is formatted as GeoJSON for easy integration with mapping systems:

**Feature Types:**
- `claim_boundary`: Polygon geometry for claim boundaries
- `claim`: Point geometry for claim centers (marker_color: red)
- `reference`: Point geometry for reference points (marker_color: blue)
- `natural_feature`: Point geometry for natural features (marker_color: green)

**Coordinate Format:** `[longitude, latitude]` (GeoJSON standard)

## GeoJSON Structure

The returned GeoJSON follows this structure:

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[lon1, lat1], [lon2, lat2], ...]]
      },
      "properties": {
        "type": "claim_boundary",
        "name": "Johnson Lode",
        "center_lat": 44.398900,
        "center_lon": -103.754200,
        "acres": 160
      }
    },
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [lon, lat]
      },
      "properties": {
        "type": "claim",
        "name": "Johnson Lode",
        "marker_color": "red"
      }
    },
    ...
  ]
}
```

## Integration with Map Server

To display the geospatial data on your OSM-based map server:

1. **Extract GeoJSON**: Parse the GeoJSON data from the tool response
2. **Load into Map**: Use a library like Leaflet, OpenLayers, or Mapbox GL JS
3. **Style Features**: Apply different styles based on `properties.type` and `marker_color`
4. **Add Interactivity**: Use `properties.name` for popups/tooltips

**Example with Leaflet:**

```javascript
// Parse GeoJSON from MCP response
const geojsonData = JSON.parse(response.geojson);

// Add to Leaflet map
L.geoJSON(geojsonData, {
  style: function(feature) {
    if (feature.properties.type === 'claim_boundary') {
      return {color: 'red', fillOpacity: 0.2};
    }
  },
  pointToLayer: function(feature, latlng) {
    const color = feature.properties.marker_color || 'gray';
    return L.marker(latlng, {
      icon: L.icon({iconUrl: `/markers/${color}.png`})
    });
  },
  onEachFeature: function(feature, layer) {
    if (feature.properties.name) {
      layer.bindPopup(feature.properties.name);
    }
  }
}).addTo(map);
```

## Configuration Options

The following options can be configured in the source code:

### Geocoding Settings
- **User Agent**: `"document-mcp-server"`
- **Rate Limit**: 1 request per second (Nominatim requirement)
- **Cache**: Enabled by default (in-memory)

### Distance Units
- **Primary Unit**: Miles (for historical claim compatibility)
- **Supported Units**: miles, kilometers, feet
- **Automatic Conversion**: Yes

### Claim Sizes
- **Default Size**: 160 acres
- **Shape**: Rectangular polygon (approximate square)

### Feature Search
- **Default Radius**: 5km
- **Max Results**: 10 features
- **Supported Types**: waterway, peak, road

## OpenStreetMap Attribution

When using OpenStreetMap data, you must provide attribution:

**Required Attribution:**
© OpenStreetMap contributors

**Nominatim Usage Policy:**
- Maximum 1 request per second
- Provide a valid User-Agent header
- Cache results when possible
- See: https://operations.osmfoundation.org/policies/nominatim/

**Overpass API Usage:**
- Be reasonable with query complexity
- Limit search radius to <5km when possible
- See: https://wiki.openstreetmap.org/wiki/Overpass_API

## Troubleshooting

### Geocoding Failures

**Problem**: Reference location cannot be found

**Solutions**:
1. Add more geographic context to the region parameter
2. Try variations of the place name
3. Use a nearby larger town if the exact location isn't in OSM
4. Check for spelling errors in place names

**Example**:
```json
// Instead of:
"region": "California"

// Try:
"region": "Nevada County, California, USA"
```

### API Rate Limits

**Problem**: `Too Many Requests` error from Nominatim

**Solution**: The system automatically rate-limits to 1 request/second. If you still encounter issues:
1. Reduce batch size in `map_all_claims`
2. Use cached results (automatic)
3. Wait a few minutes before retrying

### Parsing Errors

**Problem**: LLM fails to extract location information

**Solutions**:
1. Ensure OPENAI_API_KEY environment variable is set
2. Check that the description contains clear location references
3. Try rephrasing the description to be more explicit
4. Verify OpenAI API quota and billing

**Example of a good description**:
```
"The Lucky Strike claim is located 3 miles northeast of Virginia City, 
Montana, following Alder Gulch upstream to the junction with Granite Creek."
```

### Coordinate Accuracy

**Problem**: Calculated coordinates seem incorrect

**Solutions**:
1. Verify the reference location is correctly geocoded (check Google Maps link)
2. Check that direction and distance were parsed correctly
3. Remember that historical descriptions may be approximate
4. Use the Google Maps link to verify the calculated position

### Feature Discovery Issues

**Problem**: No natural features found

**Solutions**:
1. Check that the feature exists in OpenStreetMap data
2. Try different feature types (waterway, peak, road)
3. Small or unnamed features may not be in OSM
4. Historical feature names may differ from modern OSM names

## Example Claim Descriptions

### Simple Directional Claim
```
"Located 2 miles north of Deadwood, South Dakota"
```
- **Extracts**: Reference (Deadwood), Direction (north), Distance (2 miles)
- **Calculates**: Coordinates 2 miles north of Deadwood
- **Returns**: GeoJSON with claim marker and boundary

### Complex Claim with Features
```
"The Johnson Lode claim is situated approximately 3 miles northeast of 
Deadwood, following Whitewood Creek upstream to the junction with 
Strawberry Creek. The claim encompasses 160 acres."
```
- **Extracts**: Name (Johnson Lode), Reference (Deadwood), Direction (northeast), Distance (3 miles), Feature (Whitewood Creek)
- **Calculates**: Coordinates 3 miles NE of Deadwood
- **Searches**: For Whitewood Creek and nearby waterways
- **Returns**: GeoJSON with claim, reference point, and natural features

### Multiple Landmarks
```
"Beginning at the old stamp mill, 1.5 miles south of Bodie, California, 
thence running along the eastern ridge of the Sierra Nevada mountains"
```
- **Extracts**: Reference (Bodie), Direction (south), Distance (1.5 miles), Additional landmarks (stamp mill, Sierra Nevada)
- **Calculates**: Coordinates relative to Bodie
- **Returns**: GeoJSON with claim and reference point

## Dependencies

The geospatial features require the following Python packages:

```
geopy>=2.4.0          # Geocoding and geodesic calculations
OSMPythonTools>=0.3.5 # OpenStreetMap Overpass API queries
openai>=1.0.0         # LLM-powered claim parsing
```

These are automatically installed when building the Docker image.

## Environment Variables

### Required
- `OPENAI_API_KEY`: Your OpenAI API key for claim parsing

### Optional
- None currently (geocoding uses public Nominatim API)

## Performance Considerations

### Caching
- Geocoding results are cached in memory
- Reduces API calls for repeated locations
- Cache persists for the lifetime of the server process

### Batch Processing
- `map_all_claims` processes claims sequentially
- Each claim requires 1-2 API calls (geocoding + optional features)
- Rate limiting adds ~1 second per claim
- Typical batch of 10 claims takes ~15-20 seconds

### Resource Usage
- Minimal memory footprint
- No heavy computation (geodesic calculations are fast)
- GeoJSON output is compact and efficient

## Support

For issues or questions:
1. Check this documentation
2. Review error messages carefully
3. Verify API keys and configuration
4. Check OpenStreetMap data availability for your region
5. Review the source code in `src/geo_tools.py` and `src/claim_parser.py`
