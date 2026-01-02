"""
Geospatial tools for mining claim location and mapping.

This module provides functions for:
- Geocoding place names to GPS coordinates
- Calculating destination coordinates from bearings and distances
- Finding nearby natural features using OpenStreetMap
- Generating claim boundary polygons
- Formatting geospatial data for external mapping systems
"""

from typing import Dict, List, Optional, Tuple
from pathlib import Path
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from geopy.point import Point
import math
import time
from datetime import datetime
from OSMPythonTools.overpass import Overpass, overpassQueryBuilder


class GeoTools:
    """Geospatial utilities for mining claim location and mapping"""
    
    def __init__(self):
        # Initialize Nominatim geocoder with user agent
        self.geocoder = Nominatim(user_agent="document-mcp-server")
        
        # Initialize Overpass API for OSM queries
        self.overpass = Overpass()
        
        # Cache for geocoding results to minimize API calls
        self.geocode_cache = {}
        
        # Rate limiting: 1 request per second for Nominatim
        self.last_geocode_time = 0
        self.geocode_delay = 1.0
    
    def geocode(self, location: str, region: str = "California, USA") -> Optional[Dict]:
        """
        Convert a place name to GPS coordinates using Nominatim API.
        
        Args:
            location: Place name to geocode (e.g., "Deadwood")
            region: Geographic region for context (e.g., "South Dakota, USA")
        
        Returns:
            Dictionary with 'latitude', 'longitude', 'display_name' or None if not found
        """
        # Create full query with region context
        full_query = f"{location}, {region}"
        
        # Check cache first
        if full_query in self.geocode_cache:
            return self.geocode_cache[full_query]
        
        # Rate limiting
        current_time = time.time()
        time_since_last = current_time - self.last_geocode_time
        if time_since_last < self.geocode_delay:
            time.sleep(self.geocode_delay - time_since_last)
        
        try:
            result = self.geocoder.geocode(full_query)
            self.last_geocode_time = time.time()
            
            if result:
                geo_data = {
                    'latitude': result.latitude,
                    'longitude': result.longitude,
                    'display_name': result.address
                }
                # Cache the result
                self.geocode_cache[full_query] = geo_data
                return geo_data
            return None
        except Exception as e:
            print(f"Geocoding error for '{full_query}': {str(e)}")
            return None
    
    def cardinal_to_bearing(self, direction: str) -> float:
        """
        Convert cardinal direction to bearing in degrees.
        
        Args:
            direction: Cardinal direction (n, ne, e, se, s, sw, w, nw, etc.)
        
        Returns:
            Bearing in degrees (0-360, where 0/360 is North)
        """
        direction = direction.lower().strip()
        
        # Mapping of cardinal directions to bearings
        directions = {
            'n': 0, 'north': 0,
            'ne': 45, 'northeast': 45,
            'e': 90, 'east': 90,
            'se': 135, 'southeast': 135,
            's': 180, 'south': 180,
            'sw': 225, 'southwest': 225,
            'w': 270, 'west': 270,
            'nw': 315, 'northwest': 315
        }
        
        return directions.get(direction, 0)
    
    def calculate_destination(self, origin_lat: float, origin_lon: float, 
                            bearing: float, distance_miles: float) -> Tuple[float, float]:
        """
        Calculate destination coordinates given origin, bearing, and distance.
        
        Args:
            origin_lat: Origin latitude in decimal degrees
            origin_lon: Origin longitude in decimal degrees
            bearing: Bearing in degrees (0-360, where 0/360 is North)
            distance_miles: Distance in miles
        
        Returns:
            Tuple of (latitude, longitude) for destination point
        """
        # Create origin point
        origin = Point(origin_lat, origin_lon)
        
        # Calculate destination using geodesic distance
        destination = geodesic(miles=distance_miles).destination(origin, bearing)
        
        return (destination.latitude, destination.longitude)
    
    def find_nearby_features(self, lat: float, lon: float, 
                            feature_type: str = "waterway",
                            radius_km: float = 5.0) -> List[Dict]:
        """
        Find nearby natural features using Overpass API.
        
        Args:
            lat: Latitude of search center
            lon: Longitude of search center
            feature_type: Type of feature (waterway, peak, road, etc.)
            radius_km: Search radius in kilometers (default: 5km)
        
        Returns:
            List of features with name, type, and coordinates
        """
        try:
            # Build Overpass query based on feature type
            if feature_type == "waterway":
                element_type = "way"
                selector = '"waterway"~"river|stream|creek"'
            elif feature_type == "peak":
                element_type = "node"
                selector = '"natural"="peak"'
            elif feature_type == "road":
                element_type = "way"
                selector = '"highway"'
            else:
                # Generic query
                element_type = "node"
                selector = f'"{feature_type}"'
            
            # Create query
            query = overpassQueryBuilder(
                bbox=[lat - 0.05, lon - 0.05, lat + 0.05, lon + 0.05],
                elementType=element_type,
                selector=selector,
                out='body',
                includeGeometry=True
            )
            
            result = self.overpass.query(query)
            
            features = []
            for element in result.elements():
                tags = element.tags()
                name = tags.get('name', 'Unnamed')
                
                # Get coordinates
                if hasattr(element, 'lat') and hasattr(element, 'lon'):
                    feature_lat = element.lat()
                    feature_lon = element.lon()
                elif hasattr(element, 'centerLat') and hasattr(element, 'centerLon'):
                    feature_lat = element.centerLat()
                    feature_lon = element.centerLon()
                else:
                    continue
                
                features.append({
                    'name': name,
                    'type': feature_type,
                    'latitude': feature_lat,
                    'longitude': feature_lon,
                    'tags': tags
                })
            
            return features[:10]  # Limit to 10 features
        
        except Exception as e:
            print(f"Error finding nearby features: {str(e)}")
            return []
    
    def generate_claim_boundary(self, center_lat: float, center_lon: float,
                               acres: float = 160) -> List[Tuple[float, float]]:
        """
        Generate rectangular polygon for mining claim boundary.
        
        Args:
            center_lat: Center point latitude
            center_lon: Center point longitude
            acres: Claim size in acres (default: 160)
        
        Returns:
            List of (lat, lon) tuples forming the boundary polygon
        """
        # Calculate approximate side length for a square claim
        # 1 acre = 0.0015625 square miles
        square_miles = acres * 0.0015625
        side_miles = math.sqrt(square_miles)
        
        # Half the side length (distance from center to edge)
        half_side = side_miles / 2
        
        # Calculate corner points
        # NW corner
        nw = self.calculate_destination(center_lat, center_lon, 315, half_side * 1.414)
        # NE corner
        ne = self.calculate_destination(center_lat, center_lon, 45, half_side * 1.414)
        # SE corner
        se = self.calculate_destination(center_lat, center_lon, 135, half_side * 1.414)
        # SW corner
        sw = self.calculate_destination(center_lat, center_lon, 225, half_side * 1.414)
        
        # Return as closed polygon (first point repeated at end)
        return [nw, ne, se, sw, nw]
    
    def format_geojson(self, claims: List[Dict], reference_points: List[Dict] = None,
                      features: List[Dict] = None) -> Dict:
        """
        Format geospatial data as GeoJSON for external mapping systems.
        
        Args:
            claims: List of claim dictionaries with 'name', 'latitude', 'longitude', 'boundary'
            reference_points: List of reference point dictionaries with 'name', 'latitude', 'longitude'
            features: List of natural feature dictionaries
        
        Returns:
            GeoJSON FeatureCollection with all geospatial data
        """
        geojson = {
            "type": "FeatureCollection",
            "features": []
        }
        
        # Add claims as polygons with center point markers
        for claim in claims:
            # Add claim boundary polygon
            if 'boundary' in claim and claim['boundary']:
                polygon_coords = [[lon, lat] for lat, lon in claim['boundary']]
                geojson["features"].append({
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [polygon_coords]
                    },
                    "properties": {
                        "type": "claim_boundary",
                        "name": claim['name'],
                        "center_lat": claim['latitude'],
                        "center_lon": claim['longitude'],
                        "acres": claim.get('acres', 160)
                    }
                })
            
            # Add claim center point
            geojson["features"].append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [claim['longitude'], claim['latitude']]
                },
                "properties": {
                    "type": "claim",
                    "name": claim['name'],
                    "marker_color": "red"
                }
            })
        
        # Add reference points
        if reference_points:
            for ref in reference_points:
                geojson["features"].append({
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [ref['longitude'], ref['latitude']]
                    },
                    "properties": {
                        "type": "reference",
                        "name": ref['name'],
                        "marker_color": "blue"
                    }
                })
        
        # Add natural features
        if features:
            for feat in features:
                geojson["features"].append({
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [feat['longitude'], feat['latitude']]
                    },
                    "properties": {
                        "type": "natural_feature",
                        "name": feat['name'],
                        "feature_type": feat['type'],
                        "marker_color": "green"
                    }
                })
        
        return geojson
    
    def get_google_maps_link(self, lat: float, lon: float) -> str:
        """
        Generate Google Maps link for verification.
        
        Args:
            lat: Latitude
            lon: Longitude
        
        Returns:
            Google Maps URL
        """
        return f"https://www.google.com/maps?q={lat},{lon}"
