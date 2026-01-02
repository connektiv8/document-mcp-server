import psycopg2
from psycopg2.extras import execute_values
from sentence_transformers import SentenceTransformer
import sys
from typing import List, Dict, Optional
import os

class PgVectorDocumentStore:
    def __init__(self, connection_string: Optional[str] = None):
        if connection_string is None:
            connection_string = os.getenv(
                'DATABASE_URL',
                'postgresql://mcp_user:mcp_password@postgres:5432/mcp_documents'
            )
        
        self.connection_string = connection_string
        print("Loading embedding model...", file=sys.stderr)
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.dimension = 384
        
        # Initialize database
        self._init_database()
        print(f"Document store initialized with {self._count_documents()} documents", file=sys.stderr)
    
    def _get_connection(self):
        """Get database connection"""
        return psycopg2.connect(self.connection_string)
    
    def _init_database(self):
        """Initialize database schema"""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                # Enable pgvector extension
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                
                # Create documents table with vector column
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS documents (
                        id SERIAL PRIMARY KEY,
                        content TEXT NOT NULL,
                        embedding vector(384) NOT NULL,
                        source_file TEXT,
                        file_type TEXT,
                        file_path TEXT,
                        chunk_index INTEGER,
                        date_year INTEGER,
                        location TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                
                # Create index for vector similarity search (using cosine distance)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS documents_embedding_idx 
                    ON documents USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = 100);
                """)
                
                # Create indexes for metadata filtering
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS documents_source_file_idx 
                    ON documents(source_file);
                """)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS documents_date_year_idx 
                    ON documents(date_year);
                """)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS documents_location_idx 
                    ON documents(location);
                """)
                
                conn.commit()
                print("Database initialized successfully", file=sys.stderr)
        finally:
            conn.close()
    
    def _count_documents(self) -> int:
        """Count total documents"""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM documents;")
                return cur.fetchone()[0]
        finally:
            conn.close()
    
    def add_documents(self, texts: List[str], metadatas: Optional[List[Dict]] = None):
        """Add documents in batches"""
        if not texts:
            return
        
        print(f"Encoding {len(texts)} text chunks...", file=sys.stderr)
        embeddings = self.model.encode(
            texts,
            batch_size=32,
            show_progress_bar=True,
            convert_to_numpy=True
        )
        
        if metadatas is None:
            metadatas = [{}] * len(texts)
        
        # Prepare data for insertion
        data = []
        for text, embedding, metadata in zip(texts, embeddings, metadatas):
            data.append((
                text,
                embedding.tolist(),
                metadata.get('source_file'),
                metadata.get('file_type'),
                metadata.get('file_path'),
                metadata.get('chunk_index'),
                metadata.get('date_year'),
                metadata.get('location')
            ))
        
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                execute_values(
                    cur,
                    """
                    INSERT INTO documents 
                    (content, embedding, source_file, file_type, file_path, 
                     chunk_index, date_year, location)
                    VALUES %s
                    """,
                    data
                )
                conn.commit()
                print(f"Added {len(texts)} chunks. Total: {self._count_documents()}", file=sys.stderr)
        finally:
            conn.close()
    
    def search(
        self, 
        query: str, 
        k: int = 5,
        date_year: Optional[int] = None,
        date_year_range: Optional[tuple] = None,
        location: Optional[str] = None,
        source_file: Optional[str] = None
    ) -> List[Dict]:
        """
        Search for similar documents with optional metadata filters
        
        Args:
            query: Search query text
            k: Number of results to return
            date_year: Filter by specific year
            date_year_range: Filter by year range (start_year, end_year)
            location: Filter by location
            source_file: Filter by source file
        """
        # Encode query
        query_vector = self.model.encode([query], convert_to_numpy=True)[0]
        query_vector_list = query_vector.tolist()
        
        # Build WHERE clause for filters
        where_clauses = []
        params = []
        
        if date_year is not None:
            where_clauses.append("date_year = %s")
            params.append(date_year)
        
        if date_year_range is not None:
            where_clauses.append("date_year BETWEEN %s AND %s")
            params.append(date_year_range[0])
            params.append(date_year_range[1])
        
        if location is not None:
            where_clauses.append("location ILIKE %s")
            params.append(f"%{location}%")
        
        if source_file is not None:
            where_clauses.append("source_file = %s")
            params.append(source_file)
        
        where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        
        # Cosine similarity query - need query_vector twice (for SELECT and ORDER BY)
        query_sql = f"""
            SELECT 
                content,
                source_file,
                file_type,
                file_path,
                chunk_index,
                date_year,
                location,
                1 - (embedding <=> %s::vector) as similarity
            FROM documents
            {where_sql}
            ORDER BY embedding <=> %s::vector
            LIMIT %s;
        """
        
        # Params order: [filters..., query_vector (for SELECT), query_vector (for ORDER BY), k]
        final_params = params + [query_vector_list, query_vector_list, k]
        
        # Debug logging
        print(f"DEBUG: Query SQL = {query_sql}", file=sys.stderr)
        print(f"DEBUG: Params count = {len(final_params)}, k={k}", file=sys.stderr)
        print(f"DEBUG: Vector length = {len(query_vector_list)}", file=sys.stderr)
        
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                try:
                    cur.execute(query_sql, final_params)
                except Exception as e:
                    print(f"DEBUG: SQL execution error: {e}", file=sys.stderr)
                    print(f"DEBUG: SQL was: {query_sql}", file=sys.stderr)
                    print(f"DEBUG: Params were: {final_params[:2] + [final_params[-1]]}", file=sys.stderr)  # Don't print huge vectors
                    raise
                
                rows = cur.fetchall()
                print(f"DEBUG: Fetched {len(rows)} rows from database", file=sys.stderr)
                
                results = []
                for row in rows:
                    results.append({
                        'text': row[0],
                        'metadata': {
                            'source_file': row[1],
                            'file_type': row[2],
                            'file_path': row[3],
                            'chunk_index': row[4],
                            'date_year': row[5],
                            'location': row[6]
                        },
                        'similarity': float(row[7])
                    })
                return results
        finally:
            conn.close()
    
    def clear(self):
        """Clear all documents"""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("TRUNCATE TABLE documents;")
                conn.commit()
                print("All documents cleared", file=sys.stderr)
        finally:
            conn.close()
    
    def get_stats(self) -> Dict:
        """Get statistics about the store"""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM documents;")
                total_chunks = cur.fetchone()[0]
                
                cur.execute("SELECT COUNT(DISTINCT source_file) FROM documents WHERE source_file IS NOT NULL;")
                unique_files = cur.fetchone()[0]
                
                cur.execute("SELECT MIN(date_year), MAX(date_year) FROM documents WHERE date_year IS NOT NULL;")
                year_range = cur.fetchone()
                
                return {
                    'total_chunks': total_chunks,
                    'unique_files': unique_files,
                    'dimension': self.dimension,
                    'year_range': f"{year_range[0]}-{year_range[1]}" if year_range[0] else None
                }
        finally:
            conn.close()
    
    def save(self):
        """No-op for PostgreSQL (auto-persisted)"""
        pass
    
    def load(self):
        """No-op for PostgreSQL (auto-loaded)"""
        pass
