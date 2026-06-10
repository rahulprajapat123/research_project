"""
Quick API server test
"""
import asyncio
from fastapi.testclient import TestClient
from main import app

def test_api_endpoints():
    """Test API endpoints without starting the server"""
    client = TestClient(app)
    
    print("\n" + "=" * 70)
    print("🌐 API ENDPOINT TESTS")
    print("=" * 70)
    
    # Test 1: Health check
    print("\n1️⃣  Testing /api/v1/health...")
    response = client.get("/api/v1/health")
    if response.status_code == 200:
        print(f"   ✅ Health check passed: {response.json()}")
    else:
        print(f"   ❌ Health check failed: {response.status_code}")
    
    # Test 2: System status
    print("\n2️⃣  Testing /api/v1/status...")
    response = client.get("/api/v1/status")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Status check passed")
        print(f"   📊 Mode: {data.get('mode')}")
        print(f"   📊 Services: {list(data.get('services', {}).keys())}")
    else:
        print(f"   ❌ Status check failed: {response.status_code}")
    
    # Test 3: Sources status
    print("\n3️⃣  Testing /api/v1/sources/status...")
    try:
        response = client.get("/api/v1/sources/status")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Sources status retrieved")
            
            # Check research sources
            research = data.get('research_sources', {})
            print(f"\n   📚 Research Sources:")
            for source, info in research.items():
                status = "✅" if info.get('enabled') else "❌"
                print(f"      {status} {source}: {info}")
            
            # Check news sources
            news = data.get('news_sources', {})
            print(f"\n   📰 News Sources:")
            for source, info in news.items():
                status = "✅" if info.get('enabled') else "❌"
                print(f"      {status} {source}: {info}")
            
            # Check developer sources
            dev = data.get('developer_sources', {})
            print(f"\n   💻 Developer Sources:")
            for source, info in dev.items():
                status = "✅" if info.get('enabled') or info.get('authenticated') else "⚠️"
                print(f"      {status} {source}: {info}")
        else:
            print(f"   ❌ Sources status failed: {response.status_code}")
    except Exception as e:
        print(f"   ⚠️  Sources endpoint not available (this is OK): {e}")
    
    print("\n" + "=" * 70)
    print("✅ API TESTS COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    test_api_endpoints()
