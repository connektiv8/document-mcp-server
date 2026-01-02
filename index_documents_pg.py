#!/usr/bin/env python3
"""
Script to index documents into PostgreSQL with pgvector
Extracts metadata like year and location from document content
"""

import sys
import os
import re
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from document_store_pg import PgVectorDocumentStore
from document_processor import DocumentProcessor

console = Console()

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
    
    console.print(f"[cyan]Found {len(files)} documents to index[/cyan]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        task = progress.add_task("[green]Indexing documents...", total=len(files))
        
        for file_path in files:
            progress.update(task, description=f"[green]Processing: {file_path.name}")
            
            try:
                # Process document into chunks (returns tuple of lists)
                chunks_data, metadatas_data = doc_processor.process_and_chunk(file_path)
                
                if not chunks_data:
                    console.print(f"  [yellow]No content extracted from {file_path.name}[/yellow]")
                    progress.advance(task)
                    continue
                
                # Enhance metadata with extracted year and location
                enhanced_metadatas = []
                for i, (chunk_text, metadata) in enumerate(zip(chunks_data, metadatas_data)):
                    enhanced_meta = metadata.copy()
                    
                    # Extract year from chunk text
                    year = extract_year(chunk_text)
                    if year:
                        enhanced_meta['date_year'] = year
                    
                    # Extract location from chunk text
                    location = extract_location(chunk_text)
                    if location:
                        enhanced_meta['location'] = location
                    
                    enhanced_metadatas.append(enhanced_meta)
                
                # Add to store
                doc_store.add_documents(chunks_data, enhanced_metadatas)
                console.print(f"  [green]✓[/green] Indexed {len(chunks_data)} chunks")
                progress.advance(task)
                
            except Exception as e:
                import traceback
                console.print(f"  [red]✗ Error processing {file_path.name}: {e}[/red]")
                traceback.print_exc()
                progress.advance(task)
                continue
    
    # Show stats
    stats = doc_store.get_stats()
    console.print("\n[bold green]" + "="*50 + "[/bold green]")
    console.print("[bold green]Indexing Complete![/bold green]")
    console.print(f"[cyan]Total chunks: {stats['total_chunks']}[/cyan]")
    console.print(f"[cyan]Unique files: {stats['unique_files']}[/cyan]")
    if stats['year_range']:
        console.print(f"[cyan]Year range: {stats['year_range']}[/cyan]")
    console.print("[bold green]" + "="*50 + "[/bold green]")
    
    # Clean up database connection
    doc_store.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Index documents into PostgreSQL')
    parser.add_argument('--reindex', action='store_true', help='Clear existing documents before indexing')
    args = parser.parse_args()
    
    try:
        index_documents(reindex=args.reindex)
        sys.exit(0)  # Explicitly exit with success code
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)  # Exit with error code
