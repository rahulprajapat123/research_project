"""
Quick test to verify Neon PostgreSQL connection is working
"""
import psycopg2
from psycopg2.extras import RealDictCursor

connection_string = "postgresql://neondb_owner:npg_LwePgm6vAnh7@ep-still-violet-aooo7qxw.c-2.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"

print("🔍 Testing Neon PostgreSQL Connection...\n")

try:
    conn = psycopg2.connect(connection_string)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Test 1: Connection
    print("✅ Database connection successful!")
    
    # Test 2: Check extensions
    cursor.execute("SELECT extname, extversion FROM pg_extension WHERE extname IN ('vector', 'pgcrypto');")
    extensions = cursor.fetchall()
    print(f"\n📦 Installed Extensions:")
    for ext in extensions:
        print(f"   ✓ {ext['extname']} v{ext['extversion']}")
    
    # Test 3: List all tables
    cursor.execute("""
        SELECT table_name, 
               (SELECT COUNT(*) FROM information_schema.columns 
                WHERE table_name = t.table_name AND table_schema = 'public') as column_count
        FROM information_schema.tables t
        WHERE table_schema = 'public'
        ORDER BY table_name;
    """)
    tables = cursor.fetchall()
    
    print(f"\n📊 Database Tables ({len(tables)} total):")
    for table in tables:
        print(f"   ✓ {table['table_name']} ({table['column_count']} columns)")
    
    # Test 4: Check if we can write
    cursor.execute("""
        INSERT INTO system_metadata (key, value) 
        VALUES ('neon_test', '{"status": "connected", "timestamp": "2026-06-10"}')
        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()
        RETURNING key, value;
    """)
    result = cursor.fetchone()
    conn.commit()
    print(f"\n✍️  Write Test: Successfully wrote to system_metadata table")
    
    # Test 5: Database info
    cursor.execute("SELECT version();")
    version = cursor.fetchone()['version']
    print(f"\n🐘 PostgreSQL Version:")
    print(f"   {version[:80]}...")
    
    cursor.execute("SELECT pg_size_pretty(pg_database_size('neondb')) as size;")
    size = cursor.fetchone()['size']
    print(f"\n💾 Database Size: {size}")
    
    cursor.close()
    conn.close()
    
    print("\n" + "="*60)
    print("🎉 All tests passed! Neon PostgreSQL is fully operational!")
    print("="*60)
    
except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)
