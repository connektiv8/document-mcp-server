"""
Mining claim parser using LLM for entity extraction.

This module uses OpenAI's GPT-4o-mini to parse natural language descriptions
of mining claim locations and extract structured data.
"""

from typing import Dict, List, Optional
import json
import os
from openai import OpenAI


class ClaimParser:
    """LLM-powered parser for mining claim descriptions"""
    
    def __init__(self):
        # Initialize OpenAI client
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("Warning: OPENAI_API_KEY environment variable not set.")
            print("Set OPENAI_API_KEY to enable claim parsing functionality.")
            print("Without it, claim parsing will return errors.")
        
        self.client = OpenAI(api_key=api_key) if api_key else None
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")  # Default to cost-effective model
        
        # System prompt for entity extraction
        self.system_prompt = """You are a specialized assistant that extracts location information from mining claim descriptions.

Extract the following information from the claim description and return it as JSON:
- claim_name: Name of the mining claim (if mentioned)
- reference_location: A known landmark, town, or place name used as reference
- direction: Cardinal direction from reference (n, ne, e, se, s, sw, w, nw, north, south, etc.)
- distance: Numeric distance value
- distance_unit: Unit of distance (miles, kilometers, feet, etc.)
- natural_feature: Name of any creek, river, mountain, or ridge mentioned
- feature_type: Classification of the feature (waterway, peak, road, ridge, etc.)
- feature_direction: Relationship to feature (upstream, downstream, along, near, etc.)
- additional_landmarks: Array of other landmarks or reference points mentioned

Return ONLY valid JSON. If a field cannot be determined, use null. Be precise and extract exact values from the text."""
    
    def parse_claim_description(self, description: str) -> Optional[Dict]:
        """
        Parse a mining claim description using GPT-4o-mini.
        
        Args:
            description: Natural language description of claim location
        
        Returns:
            Dictionary with extracted entities or None if parsing fails
        """
        if not self.client:
            return {
                'error': 'OpenAI API key not configured',
                'claim_name': None,
                'reference_location': None,
                'direction': None,
                'distance': None,
                'distance_unit': None,
                'natural_feature': None,
                'feature_type': None,
                'feature_direction': None,
                'additional_landmarks': []
            }
        
        try:
            # Call OpenAI API for entity extraction
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": f"Extract location information from this claim description:\n\n{description}"}
                ],
                temperature=0,  # Deterministic output
                max_tokens=500
            )
            
            # Parse JSON response
            content = response.choices[0].message.content.strip()
            
            # Remove markdown code blocks if present
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            parsed_data = json.loads(content)
            
            # Ensure all expected fields are present
            default_fields = {
                'claim_name': None,
                'reference_location': None,
                'direction': None,
                'distance': None,
                'distance_unit': None,
                'natural_feature': None,
                'feature_type': None,
                'feature_direction': None,
                'additional_landmarks': []
            }
            
            # Merge with defaults
            for key, default_value in default_fields.items():
                if key not in parsed_data:
                    parsed_data[key] = default_value
            
            return parsed_data
        
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON from LLM response: {str(e)}")
            return None
        except Exception as e:
            print(f"Error parsing claim description: {str(e)}")
            return None
    
    def parse_batch(self, descriptions: List[str]) -> List[Dict]:
        """
        Parse multiple claim descriptions.
        
        Args:
            descriptions: List of claim description strings
        
        Returns:
            List of parsed data dictionaries
        """
        results = []
        
        for i, description in enumerate(descriptions):
            print(f"Parsing claim {i+1}/{len(descriptions)}...")
            parsed = self.parse_claim_description(description)
            
            if parsed:
                results.append({
                    'description': description,
                    'parsed': parsed,
                    'success': 'error' not in parsed
                })
            else:
                results.append({
                    'description': description,
                    'parsed': None,
                    'success': False,
                    'error': 'Parsing failed'
                })
        
        return results
    
    def link_to_documents(self, parsed_claims: List[Dict], 
                         search_results: List[Dict]) -> List[Dict]:
        """
        Link parsed claim data to source documents.
        
        Args:
            parsed_claims: List of parsed claim dictionaries
            search_results: List of search result dictionaries from document store
        
        Returns:
            List of claims with linked document metadata
        """
        linked_claims = []
        
        for i, claim in enumerate(parsed_claims):
            if i < len(search_results):
                claim['source_document'] = search_results[i].get('metadata', {})
                claim['source_text'] = search_results[i].get('text', '')
            
            linked_claims.append(claim)
        
        return linked_claims
