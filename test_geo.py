"""
Unit tests for geospatial tools and claim parsing.

Tests cover:
- Coordinate calculations
- Cardinal direction conversions
- Claim boundary generation
- Sample claim descriptions
"""

import unittest
from pathlib import Path
import sys
import os

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from geo_tools import GeoTools
from claim_parser import ClaimParser


class TestGeoTools(unittest.TestCase):
    """Test cases for GeoTools class"""
    
    def setUp(self):
        """Initialize GeoTools for each test"""
        self.geo = GeoTools()
    
    def test_cardinal_to_bearing(self):
        """Test cardinal direction to bearing conversion"""
        # Test basic directions
        self.assertEqual(self.geo.cardinal_to_bearing('n'), 0)
        self.assertEqual(self.geo.cardinal_to_bearing('north'), 0)
        self.assertEqual(self.geo.cardinal_to_bearing('e'), 90)
        self.assertEqual(self.geo.cardinal_to_bearing('east'), 90)
        self.assertEqual(self.geo.cardinal_to_bearing('s'), 180)
        self.assertEqual(self.geo.cardinal_to_bearing('south'), 180)
        self.assertEqual(self.geo.cardinal_to_bearing('w'), 270)
        self.assertEqual(self.geo.cardinal_to_bearing('west'), 270)
        
        # Test intermediate directions
        self.assertEqual(self.geo.cardinal_to_bearing('ne'), 45)
        self.assertEqual(self.geo.cardinal_to_bearing('northeast'), 45)
        self.assertEqual(self.geo.cardinal_to_bearing('nw'), 315)
        self.assertEqual(self.geo.cardinal_to_bearing('northwest'), 315)
        self.assertEqual(self.geo.cardinal_to_bearing('se'), 135)
        self.assertEqual(self.geo.cardinal_to_bearing('sw'), 225)
    
    def test_calculate_destination(self):
        """Test destination coordinate calculation"""
        # Test point: Deadwood, SD (approximately)
        origin_lat = 44.3769
        origin_lon = -103.7294
        
        # Calculate 2 miles north
        dest_lat, dest_lon = self.geo.calculate_destination(
            origin_lat, origin_lon, 0, 2
        )
        
        # Should move ~0.029 degrees north (roughly)
        self.assertAlmostEqual(dest_lat, origin_lat + 0.029, delta=0.005)
        self.assertAlmostEqual(dest_lon, origin_lon, delta=0.005)
        
        # Calculate 2 miles east
        dest_lat, dest_lon = self.geo.calculate_destination(
            origin_lat, origin_lon, 90, 2
        )
        
        # Latitude should stay roughly the same, longitude should increase
        self.assertAlmostEqual(dest_lat, origin_lat, delta=0.005)
        self.assertGreater(dest_lon, origin_lon)
    
    def test_generate_claim_boundary(self):
        """Test claim boundary polygon generation"""
        center_lat = 44.3769
        center_lon = -103.7294
        
        # Generate 160-acre claim boundary
        boundary = self.geo.generate_claim_boundary(center_lat, center_lon, acres=160)
        
        # Should return 5 points (4 corners + first point repeated)
        self.assertEqual(len(boundary), 5)
        
        # First and last points should be the same (closed polygon)
        self.assertEqual(boundary[0], boundary[4])
        
        # All points should be tuples of (lat, lon)
        for point in boundary:
            self.assertIsInstance(point, tuple)
            self.assertEqual(len(point), 2)
            self.assertIsInstance(point[0], float)
            self.assertIsInstance(point[1], float)
    
    def test_google_maps_link(self):
        """Test Google Maps link generation"""
        lat = 44.3769
        lon = -103.7294
        
        link = self.geo.get_google_maps_link(lat, lon)
        
        self.assertIn('google.com/maps', link)
        self.assertIn(str(lat), link)
        self.assertIn(str(lon), link)


class TestClaimParser(unittest.TestCase):
    """Test cases for ClaimParser class"""
    
    def setUp(self):
        """Initialize ClaimParser for each test"""
        self.parser = ClaimParser()
    
    def test_sample_claim_descriptions(self):
        """Test parsing of sample claim descriptions"""
        # Sample descriptions for testing
        test_cases = [
            {
                'description': "The Johnson Lode claim is situated approximately 2 miles northwest of Deadwood, South Dakota",
                'expected_fields': ['reference_location', 'direction', 'distance']
            },
            {
                'description': "Located 3 miles northeast of Virginia City, following Alder Creek upstream",
                'expected_fields': ['reference_location', 'direction', 'distance', 'natural_feature']
            },
            {
                'description': "The Silver King claim lies 1.5 miles south of Bodie, California, near the old stamp mill",
                'expected_fields': ['reference_location', 'direction', 'distance']
            }
        ]
        
        # Note: These tests require OPENAI_API_KEY to be set
        # Skip if not configured
        if not os.getenv('OPENAI_API_KEY'):
            self.skipTest("OPENAI_API_KEY not configured")
        
        for test_case in test_cases:
            with self.subTest(description=test_case['description'][:50]):
                result = self.parser.parse_claim_description(test_case['description'])
                
                # Should return a dictionary
                self.assertIsInstance(result, dict)
                
                # Should not have an error
                self.assertNotIn('error', result)
                
                # Should have all expected fields with non-null values
                for field in test_case['expected_fields']:
                    self.assertIn(field, result)
                    self.assertIsNotNone(result[field], f"Field '{field}' should not be None")


class TestIntegration(unittest.TestCase):
    """Integration tests for full workflow"""
    
    def setUp(self):
        """Initialize components"""
        self.geo = GeoTools()
        self.parser = ClaimParser()
    
    def test_simple_claim_workflow(self):
        """Test complete workflow with a simple claim"""
        # Skip if API key not configured
        if not os.getenv('OPENAI_API_KEY'):
            self.skipTest("OPENAI_API_KEY not configured")
        
        description = "2 miles north of Deadwood, South Dakota"
        
        # Parse the description
        parsed = self.parser.parse_claim_description(description)
        
        self.assertIsNotNone(parsed)
        self.assertIsInstance(parsed, dict)
        
        # Verify we got useful data
        if 'reference_location' in parsed and parsed['reference_location']:
            print(f"\nParsed reference location: {parsed['reference_location']}")
            print(f"Direction: {parsed.get('direction')}")
            print(f"Distance: {parsed.get('distance')} {parsed.get('distance_unit')}")
    
    def test_coordinate_accuracy(self):
        """Test that coordinate calculations are reasonable"""
        # Known location: Deadwood, SD
        origin_lat = 44.3769
        origin_lon = -103.7294
        
        # Calculate 10 miles in each cardinal direction
        distances_and_bearings = [
            (0, 10),    # North
            (90, 10),   # East
            (180, 10),  # South
            (270, 10)   # West
        ]
        
        for bearing, distance in distances_and_bearings:
            dest_lat, dest_lon = self.geo.calculate_destination(
                origin_lat, origin_lon, bearing, distance
            )
            
            # Coordinates should be valid
            self.assertGreaterEqual(dest_lat, -90)
            self.assertLessEqual(dest_lat, 90)
            self.assertGreaterEqual(dest_lon, -180)
            self.assertLessEqual(dest_lon, 180)
            
            # Should not be too far (10 miles ~ 0.145 degrees)
            lat_diff = abs(dest_lat - origin_lat)
            lon_diff = abs(dest_lon - origin_lon)
            self.assertLess(max(lat_diff, lon_diff), 0.5)


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)
