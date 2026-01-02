#!/usr/bin/env python3
"""
Script to index documents into PostgreSQL with pgvector
Extracts metadata like year and location from document content
"""

import sys
import os
import re
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from document_store_pg import PgVectorDocumentStore
from document_processor import DocumentProcessor

def extract_year(text: str) -> int | None:
    """Extract year from text (1800-2099 range)"""
    years = re.findall(r'\b(1[89]\d{2}|20\d{2})\b', text)
    if years:
        return int(years[0])
    return None

def extract_location(text: str) -> str | None:
    """Extract location mentions from text"""
    # Common Victorian goldfield locations
    locations = [
        'Bendigo', 'Ballarat', 'Castlemaine', 'Yea', 'Beechworth',
        'Ararat', 'Dunolly', 'Maryborough', 'Clunes', 'Stawell',
        'Melbourne', 'Victoria'
    ]
    
    text_lower = text.lower()
    for location in locations:
        if location.lower() in text_lower:
            return location
    return None

def index_documents(reindex=False):
    """Index documents with metadata extraction"""
    print("Initializing PostgreSQL document store...")
    doc_store = PgVectorDocumentStore()
    doc_processor = DocumentProcessor()
    
    if reindex:
        print("Clearing existing documents...")
        doc_store.clear()
    
    docs_path = Path("/app/data/documents")
    if not docs_path.exists():
        docs_path = Path("data/documents")
    
    if not docs_path.exists():
        print(f"Documents directory not found: {docs_path}")
        return
    
    # Find all PDF and DOCX files
    files = list(docs_path.glob("**/*.pdf")) + list(docs_path.glob("**/*.docx"))
    
    if not files:
        print(f"No documents found in {docs_path}")
        return
    
    print(f"Found {len(files)} documents to index")
    
    for file_path in files:
        print(f"\nProcessing: {file_path.name}")
        
        try:
            # Process document into chunks
            chunks_data = doc_processor.process_and_chunk(str(file_path))
            
            if not chunks_data:
                print(f"  No content extracted from {file_path.name}")
                continue
            
            texts = [chunk['text'] for chunk in chunks_data]
            
            # Enhance metadata with extracted year and location
            metadatas = []
            for chunk in chunks_data:
                metadata = chunk['metadata'].copy()
                
                # Extract year from chunk text
                year = extract_year(chunk['text'])
                if year:
                    metadata['date_year'] = year
                
                # Extract location from chunk text
                location = extract_location(chunk['text'])
                if location:
                    metadata['location'] = location
                
                metadatas.append(metadata)
            
            # Add to store
            doc_store.add_documents(texts, metadatas)
            print(f"  ✓ Indexed {len(texts)} chunks")
            
        except Exception as e:
            print(f"  ✗ Error processing {file_path.name}: {e}", file=sys.stderr)
            continue
    
    # Show stats
    stats = doc_store.get_stats()
    print("\n" + "="*50)
    print("Indexing Complete!")
    print(f"Total chunks: {stats['total_chunks']}")
    print(f"Unique files: {stats['unique_files']}")
    if stats['year_range']:
        print(f"Year range: {stats['year_range']}")
    print("="*50)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Index documents into PostgreSQL')
    parser.add_argument('--reindex', action='store_true', help='Clear existing documents before indexing')
    args = parser.parse_args()
    
    index_documents(reindex=args.reindex)
