FROM python:3.11-slim

# Install system dependencies for PDF/DOCX processing
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download the embedding model during build to /root/.cache
# This ensures it's available offline at runtime
ENV TRANSFORMERS_OFFLINE=0
RUN python -c "from sentence_transformers import SentenceTransformer; model = SentenceTransformer('all-MiniLM-L6-v2'); print('Model cached successfully')"

# Copy application code
COPY src/ ./src/

# Copy indexing scripts
COPY index_documents_pg.py ./

# Create directories for data
RUN mkdir -p /app/data/documents /app/data/vector_store

# Expose MCP server port
EXPOSE 8000

# Run the server
CMD ["python", "src/server.py"]
