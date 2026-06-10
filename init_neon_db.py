"""
Script to initialize Neon PostgreSQL database with schema
"""
import psycopg2
import os
from pathlib import Path

# Read connection string from .env
connection_string = "postgresql://neondb_owner:npg_LwePgm6vAnh7@ep-still-violet-aooo7qxw.c-2.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"

# Read schema file
schema_path = Path(__file__).parent / "database" / "schema.sql"
with open(schema_path, 'r', encoding='utf-8') as f:
    schema_sql = f.read()

print("🔌 Connecting to Neon PostgreSQL...")
try:
    conn = psycopg2.connect(connection_string)
    conn.autocommit = True
    cursor = conn.cursor()
    
    print("✅ Connected successfully!")
    
    # Enable extensions first
    print("📦 Enabling pgvector and pgcrypto extensions...")
    cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    cursor.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")
    print("✅ Extensions enabled!")
    
    # Execute schema
    print("🏗️  Creating database schema...")
    cursor.execute(schema_sql)
    print("✅ Schema created successfully!")
    
    # Verify tables
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name;
    """)
    tables = cursor.fetchall()
    
    print(f"\n📊 Created {len(tables)} tables:")
    for table in tables:
        print(f"   ✓ {table[0]}")
    
    cursor.close()
    conn.close()
    
    print("\n🎉 Database initialization complete!")
    print("✅ Ready to restart server with PostgreSQL enabled")
    
except Exception as e:
    print(f"❌ Error: {e}")
    print("\nTroubleshooting:")
    print("1. Check that the Neon database is accessible")
    print("2. Verify the connection string is correct")
    print("3. Ensure pgvector extension is available in Neon")
    exit(1)
