import pymupdf  # PyMuPDF
from docx import Document
from pathlib import Path
from typing import List, Tuple
import re
import sys

class DocumentProcessor:
    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def process_pdf(self, filepath: Path) -> str:
        """Extract text from PDF"""
        doc = pymupdf.open(filepath)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    
    def process_docx(self, filepath: Path) -> str:
        """Extract text from DOCX"""
        doc = Document(filepath)
        text = "\n".join([para.text for para in doc.paragraphs])
        return text
    
    def process_file(self, filepath: Path) -> str:
        """Process a file based on extension"""
        suffix = filepath.suffix.lower()
        
        if suffix == '.pdf':
            return self.process_pdf(filepath)
        elif suffix == '.docx':
            return self.process_docx(filepath)
        else:
            raise ValueError(f"Unsupported file type: {suffix}. Only PDF and DOCX are supported.")
    
    def chunk_text(self, text: str, metadata: dict = None) -> Tuple[List[str], List[dict]]:
        """Split text into overlapping chunks"""
        # Clean text
        text = re.sub(r'\s+', ' ', text).strip()
        
        if not text:
            return [], []
        
        # Simple word-based chunking
        words = text.split()
        chunks = []
        metadatas = []
        
        for i in range(0, len(words), self.chunk_size - self.chunk_overlap):
            chunk = ' '.join(words[i:i + self.chunk_size])
            if chunk.strip():
                chunks.append(chunk)
                chunk_meta = metadata.copy() if metadata is not None else {}
                chunk_meta['chunk_index'] = len(chunks) - 1
                metadatas.append(chunk_meta)
        
        return chunks, metadatas
    
    def process_and_chunk(self, filepath: Path) -> Tuple[List[str], List[dict]]:
        """Process a file and return chunks with metadata"""
        print(f"Processing {filepath.name}...", file=sys.stderr)
        
        text = self.process_file(filepath)
        
        metadata = {
            'source': filepath.name,
            'type': filepath.suffix.lower(),
            'path': str(filepath)
        }
        
        chunks, metadatas = self.chunk_text(text, metadata)
        print(f"  Created {len(chunks)} chunks from {filepath.name}", file=sys.stderr)
        
        return chunks, metadatas
