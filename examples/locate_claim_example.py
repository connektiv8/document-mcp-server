#!/usr/bin/env python3
"""
Example usage of geospatial tools for mining claim location.

This script demonstrates how to use the geo_tools module to:
1. Geocode a reference location
2. Calculate claim coordinates from direction and distance  
3. Generate claim boundaries
4. Find nearby natural features
5. Format data as GeoJSON

Usage:
    python examples/locate_claim_example.py
"""

import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from geo_tools import GeoTools


def main():
    """Example: Locate a mining claim from natural language description"""
    
    # Initialize GeoTools
    geo = GeoTools()
    
    print("=" * 70)
    print("Mining Claim Location Example")
    print("=" * 70)
    print()
    
    # Example claim description:
    # "2 miles northwest of Deadwood, South Dakota"
    
    # Step 1: Geocode the reference location
    print("Step 1: Geocoding reference location...")
    reference_location = "Deadwood"
    region = "South Dakota, USA"
    
    ref_coords = geo.geocode(reference_location, region)
    
    if not ref_coords:
        print(f"Error: Could not geocode '{reference_location}' in '{region}'")
        return
    
    print(f"  ✓ {reference_location}: {ref_coords['latitude']:.6f}°, {ref_coords['longitude']:.6f}°")
    print(f"    ({ref_coords['display_name']})")
    print()
    
    # Step 2: Calculate claim coordinates
    print("Step 2: Calculating claim coordinates...")
    direction = "northwest"
    distance_miles = 2
    
    bearing = geo.cardinal_to_bearing(direction)
    print(f"  • Direction: {direction} ({bearing}°)")
    print(f"  • Distance: {distance_miles} miles")
    
    claim_lat, claim_lon = geo.calculate_destination(
        ref_coords['latitude'],
        ref_coords['longitude'],
        bearing,
        distance_miles
    )
    
    print(f"  ✓ Claim center: {claim_lat:.6f}°, {claim_lon:.6f}°")
    print(f"  • Google Maps: {geo.get_google_maps_link(claim_lat, claim_lon)}")
    print()
    
    # Step 3: Generate claim boundary
    print("Step 3: Generating claim boundary (160 acres)...")
    boundary = geo.generate_claim_boundary(claim_lat, claim_lon, acres=160)
    print(f"  ✓ Generated {len(boundary)} corner points (closed polygon)")
    print(f"  • Corners:")
    for i, (lat, lon) in enumerate(boundary[:-1], 1):  # Skip last point (duplicate)
        print(f"    {i}. {lat:.6f}°, {lon:.6f}°")
    print()
    
    # Step 4: Find nearby natural features
    print("Step 4: Searching for nearby waterways...")
    features = geo.find_nearby_features(claim_lat, claim_lon, feature_type="waterway", radius_km=5)
    
    if features:
        print(f"  ✓ Found {len(features)} features:")
        for feat in features[:5]:  # Show first 5
            print(f"    • {feat['name']}: {feat['latitude']:.6f}°, {feat['longitude']:.6f}°")
    else:
        print("  • No features found (OSM data may be limited)")
    print()
    
    # Step 5: Format as GeoJSON
    print("Step 5: Formatting as GeoJSON...")
    
    claim_data = {
        'name': 'Johnson Lode',
        'latitude': claim_lat,
        'longitude': claim_lon,
        'boundary': boundary,
        'acres': 160
    }
    
    reference_point = {
        'name': reference_location,
        'latitude': ref_coords['latitude'],
        'longitude': ref_coords['longitude']
    }
    
    geojson = geo.format_geojson(
        claims=[claim_data],
        reference_points=[reference_point],
        features=features[:3] if features else []  # Include up to 3 features
    )
    
    print(f"  ✓ Generated GeoJSON FeatureCollection")
    print(f"  • Total features: {len(geojson['features'])}")
    print()
    
    # Display GeoJSON (pretty printed)
    print("GeoJSON Output:")
    print("-" * 70)
    print(json.dumps(geojson, indent=2))
    print("-" * 70)
    print()
    
    print("✓ Example completed successfully!")
    print()
    print("Next steps:")
    print("  1. Use this GeoJSON with your OSM map server")
    print("  2. Style features based on 'type' and 'marker_color' properties")
    print("  3. Add popups using the 'name' property")


if __name__ == "__main__":
    main()
