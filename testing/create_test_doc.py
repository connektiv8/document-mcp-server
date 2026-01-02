"""Quick script to create a test document for testing the MCP server"""
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

def create_test_pdf():
    """Create a simple test PDF with some content"""
    c = canvas.Canvas("../data/documents/test_document.pdf", pagesize=letter)
    
    # Add some test content
    c.setFont("Helvetica", 16)
    c.drawString(100, 750, "Test Document for MCP Server")
    
    c.setFont("Helvetica", 12)
    y_position = 700
    
    test_content = [
        "This is a test document for the Document MCP Server.",
        "",
        "The server provides semantic search capabilities using FAISS",
        "and sentence transformers for CPU-optimized performance.",
        "",
        "Key Features:",
        "- Fast indexing of PDF and DOCX documents",
        "- Semantic similarity search",
        "- CPU-optimized with FAISS",
        "- Docker containerized deployment",
        "",
        "This document contains information about machine learning,",
        "natural language processing, and document search systems.",
    ]
    
    for line in test_content:
        c.drawString(100, y_position, line)
        y_position -= 20
    
    c.save()
    print("Created test document: ../data/documents/test_document.pdf")

if __name__ == "__main__":
    create_test_pdf()
