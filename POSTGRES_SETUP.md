# PostgreSQL Setup Guide

## Current Status
✅ **System is working with local JSON storage** - no PostgreSQL needed for basic functionality
⚠️ PostgreSQL provides better performance for large datasets and concurrent access

---

## Option 1: Local PostgreSQL (Best for Production)

### Install PostgreSQL on Windows

1. **Download PostgreSQL 16**
   - Visit: https://www.enterprisedb.com/downloads/postgres-postgresql-downloads
   - Download Windows x86-64 version
   - Run installer

2. **Installation Settings**
   ```
   Port: 5432
   Password: research2026
   Locale: English, United States
   Components: 
     ✅ PostgreSQL Server
     ✅ pgAdmin 4 (optional GUI)
     ✅ Command Line Tools
     ✅ Stack Builder
   ```

3. **Enable pgvector Extension**
   ```powershell
   # After installation, run Stack Builder
   # Or install manually:
   cd "C:\Program Files\PostgreSQL\16\bin"
   
   # Download pgvector from: https://github.com/pgvector/pgvector/releases
   # Or use pre-built Windows binaries
   ```

4. **Create Database and User**
   ```powershell
   # Open PowerShell as Administrator
   cd "C:\Program Files\PostgreSQL\16\bin"
   
   # Connect to PostgreSQL
   .\psql.exe -U postgres
   ```
   
   ```sql
   -- Inside psql prompt:
   CREATE DATABASE research_intel;
   CREATE USER research_user WITH PASSWORD 'research2026';
   GRANT ALL PRIVILEGES ON DATABASE research_intel TO research_user;
   \c research_intel
   CREATE EXTENSION IF NOT EXISTS vector;
   CREATE EXTENSION IF NOT EXISTS pgcrypto;
   \q
   ```

5. **Run Database Schema**
   ```powershell
   cd C:\Users\praja\Desktop\research-agent-main\research-agent-main
   
   # Set password environment variable
   $env:PGPASSWORD="research2026"
   
   # Run schema
   "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U research_user -d research_intel -f database/schema.sql
   ```

6. **Update .env File**
   ```env
   # Uncomment these lines in .env:
   DATABASE_HOST=localhost
   DATABASE_NAME=research_intel
   DATABASE_USERNAME=research_user
   DATABASE_PASSWORD=research2026
   DATABASE_PORT=5432
   DATABASE_TYPE=postgresql
   ```

7. **Restart Server**
   ```powershell
   python main.py
   ```

---

## Option 2: Cloud PostgreSQL (Easiest - No Local Install)

### A. Neon (Free Tier - Recommended)

1. **Sign Up**
   - Visit: https://neon.tech
   - Create free account
   - Create new project

2. **Get Connection String**
   ```
   postgresql://user:password@ep-cool-name-123456.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```

3. **Enable pgvector**
   - Go to SQL Editor
   - Run:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   CREATE EXTENSION IF NOT EXISTS pgcrypto;
   ```

4. **Update .env**
   ```env
   DATABASE_CONNECTION_STRING=postgresql://user:password@ep-cool-name-123456.us-east-2.aws.neon.tech/neondb?sslmode=require
   DATABASE_TYPE=postgresql
   ```

5. **Run Schema**
   ```powershell
   pip install psycopg2-binary
   
   # Using Python to run schema
   python -c "
   import psycopg2
   conn = psycopg2.connect('YOUR_CONNECTION_STRING_HERE')
   with open('database/schema.sql', 'r') as f:
       conn.cursor().execute(f.read())
   conn.commit()
   "
   ```

### B. Supabase (Free Tier)

1. **Sign Up**: https://supabase.com
2. Create new project
3. Get connection string from Settings → Database
4. pgvector is pre-installed!
5. Run schema via SQL Editor or Python script

### C. Render (Free Tier)

1. **Sign Up**: https://render.com
2. Create PostgreSQL database (free tier: 90-day limit)
3. Get connection string
4. Install extensions and run schema

---

## Option 3: Continue with Local JSON (Simplest)

✅ **Already configured!** The `.env` file now uses local JSON storage.

### How It Works
- Fetched sources → `./storage/fetched_sources.json`
- Intelligence briefs → `./storage/intelligence_store.json`
- No database needed
- Perfect for development and testing

### Limitations
- No vector search (pgvector)
- No concurrent access optimization
- File-based storage (slower for large datasets)
- Manual backup needed

---

## Verification Steps

### Test Database Connection

```python
# test_db_connection.py
import asyncpg
import asyncio

async def test_connection():
    try:
        conn = await asyncpg.connect(
            host='localhost',
            port=5432,
            user='research_user',
            password='research2026',
            database='research_intel'
        )
        print("✅ Connected to PostgreSQL!")
        
        # Test pgvector
        result = await conn.fetchval("SELECT 1")
        print(f"✅ Query works: {result}")
        
        # Check extensions
        extensions = await conn.fetch("SELECT extname FROM pg_extension")
        print(f"✅ Installed extensions: {[e['extname'] for e in extensions]}")
        
        await conn.close()
    except Exception as e:
        print(f"❌ Connection failed: {e}")

asyncio.run(test_connection())
```

Run:
```powershell
pip install asyncpg
python test_db_connection.py
```

---

## Troubleshooting

### Issue: "FATAL: password authentication failed"
**Solution**: Reset password
```sql
-- As postgres user:
ALTER USER research_user WITH PASSWORD 'research2026';
```

### Issue: "could not connect to server"
**Solution**: Start PostgreSQL service
```powershell
# Check service status
Get-Service -Name postgresql*

# Start service
Start-Service postgresql-x64-16
```

### Issue: "extension 'vector' does not exist"
**Solution**: Install pgvector
- Download from: https://github.com/pgvector/pgvector/releases
- Or use Stack Builder in PostgreSQL installation

### Issue: "database 'research_intel' does not exist"
**Solution**: Create database
```powershell
"C:\Program Files\PostgreSQL\16\bin\createdb.exe" -U postgres research_intel
```

---

## Performance Comparison

| Feature | Local JSON | PostgreSQL |
|---------|-----------|------------|
| Setup Time | ✅ 0 minutes | ⚠️ 30-60 minutes |
| Vector Search | ❌ No | ✅ Yes (pgvector) |
| Concurrent Access | ❌ Limited | ✅ Optimized |
| Large Datasets | ⚠️ Slower | ✅ Fast |
| Backup | ⚠️ Manual | ✅ Automated |
| Cost | ✅ Free | ✅ Free (cloud tier) |
| Good For | Development | Production |

---

## Recommended Choice

### For Development/Testing
👉 **Use Local JSON (Option 3)** - Already working!

### For Production
👉 **Use Cloud PostgreSQL (Option 2)** - Neon or Supabase
- No local installation needed
- Free tier available
- pgvector pre-installed
- Automatic backups

### For On-Premise Production
👉 **Install Local PostgreSQL (Option 1)**
- Full control
- No internet dependency
- Better for sensitive data

---

## Next Steps

1. ✅ **Already done**: Configured for local JSON storage
2. ⏳ **Optional**: Install PostgreSQL if you need vector search
3. 📊 **Test**: Upload a brief and verify recommendations work
4. 🚀 **Deploy**: Choose cloud PostgreSQL when ready for production
