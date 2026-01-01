import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import pickle
import os
from typing import List, Dict, Optional
from pathlib import Path

class FastDocumentStore:
    def __init__(self, store_path: str = "/app/data/vector_store"):
        self.store_path = Path(store_path)
        self.store_path.mkdir(parents=True, exist_ok=True)
        
        print("Loading embedding model...")
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.dimension = 384
        
        # FAISS index
        self.index = faiss.IndexFlatL2(self.dimension)
        
        # Metadata storage
        self.documents = []
        self.metadata = []
        
        self.load()
        print(f"Document store initialized with {len(self.documents)} documents")
    
    def add_documents(self, texts: List[str], metadatas: Optional[List[Dict]] = None):
        """Add documents in batches"""
        if not texts:
            return
        
        print(f"Encoding {len(texts)} text chunks...")
        embeddings = self.model.encode(
            texts,
            batch_size=32,
            show_progress_bar=True,
            convert_to_numpy=True
        )
        
        # Add to FAISS
        self.index.add(embeddings.astype('float32'))
        
        # Store documents
        self.documents.extend(texts)
        if metadatas:
            self.metadata.extend(metadatas)
        else:
            self.metadata.extend([{}] * len(texts))
        
        self.save()
        print(f"Added {len(texts)} chunks. Total: {len(self.documents)}")
    
    def search(self, query: str, k: int = 5) -> List[Dict]:
        """Search for similar documents"""
        if self.index.ntotal == 0:
            return []
        
        query_vector = self.model.encode([query], convert_to_numpy=True)
        
        # FAISS search
        distances, indices = self.index.search(
            query_vector.astype('float32'), 
            min(k, self.index.ntotal)
        )
        
        results = []
        for idx, distance in zip(indices[0], distances[0]):
            if idx < len(self.documents) and idx >= 0:
                results.append({
                    'text': self.documents[idx],
                    'metadata': self.metadata[idx],
                    'distance': float(distance),
                    'similarity': float(1 / (1 + distance))  # Convert distance to similarity
                })
        return results
    
    def save(self):
        """Persist to disk"""
        faiss.write_index(self.index, str(self.store_path / "faiss.index"))
        with open(self.store_path / "docs.pkl", 'wb') as f:
            pickle.dump({
                'docs': self.documents,
                'meta': self.metadata
            }, f)
    
    def load(self):
        """Load from disk"""
        index_path = self.store_path / "faiss.index"
        docs_path = self.store_path / "docs.pkl"
        
        if index_path.exists():
            print(f"Loading existing index from {index_path}")
            self.index = faiss.read_index(str(index_path))
        
        if docs_path.exists():
            print(f"Loading existing documents from {docs_path}")
            with open(docs_path, 'rb') as f:
                data = pickle.load(f)
                self.documents = data['docs']
                self.metadata = data['meta']
    
    def clear(self):
        """Clear all documents"""
        self.index = faiss.IndexFlatL2(self.dimension)
        self.documents = []
        self.metadata = []
        self.save()
    
    def get_stats(self) -> Dict:
        """Get statistics about the store"""
        return {
            'total_chunks': len(self.documents),
            'index_size': self.index.ntotal,
            'dimension': self.dimension
        }
