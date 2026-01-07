#!/usr/bin/env python3
"""
Backfill source_file metadata based on creation timestamps
"""
import psycopg2
from pathlib import Path

# Database connection
conn_str = 'postgresql://mcp_user:mcp_password@postgres:5432/mcp_documents'
conn = psycopg2.connect(conn_str)

# Get list of document files in alphabetical order
docs_path = Path("data/documents")
files = sorted(list(docs_path.glob("**/*.pdf")) + list(docs_path.glob("**/*.docx")))
filenames = [f.name for f in files]

print(f"Found {len(filenames)} files in documents folder")

# Get distinct timestamps and their ID ranges
cur = conn.cursor()
cur.execute("""
    SELECT DISTINCT created_at, 
           MIN(id) as first_id, 
           MAX(id) as last_id,
           COUNT(*) as chunk_count
    FROM documents 
    GROUP BY created_at 
    ORDER BY created_at;
""")

timestamp_groups = cur.fetchall()
print(f"Found {len(timestamp_groups)} timestamp groups in database")

# Map each timestamp group to a filename
updates = []
for i, (timestamp, first_id, last_id, chunk_count) in enumerate(timestamp_groups):
    if i < len(filenames):
        filename = filenames[i]
        file_type = Path(filename).suffix.lower()
        updates.append((filename, file_type, first_id, last_id))
        print(f"{i+1}. {filename}: IDs {first_id}-{last_id} ({chunk_count} chunks)")

# Apply updates
print(f"\nUpdating {len(updates)} file groups...")
for filename, file_type, first_id, last_id in updates:
    cur.execute("""
        UPDATE documents 
        SET source_file = %s, file_type = %s
        WHERE id >= %s AND id <= %s;
    """, (filename, file_type, first_id, last_id))

conn.commit()

# Verify
cur.execute("SELECT COUNT(DISTINCT source_file) FROM documents WHERE source_file IS NOT NULL;")
unique_files = cur.fetchone()[0]
print(f"\n✓ Updated! {unique_files} unique files now in database")

cur.close()
conn.close()
