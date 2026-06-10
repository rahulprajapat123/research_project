"""Comprehensive endpoint testing script"""
import asyncio
import httpx
from datetime import datetime

BASE_URL = "http://localhost:8000"

async def check_endpoint(client, method, path, data=None, description=""):
    """Test a single endpoint"""
    url = f"{BASE_URL}{path}"
    print(f"\n{'='*60}")
    print(f"Testing: {method} {path}")
    print(f"Description: {description}")
    print(f"{'='*60}")
    
    try:
        if method == "GET":
            response = await client.get(url)
        elif method == "POST":
            response = await client.post(url, json=data or {})
        else:
            print(f"Unsupported method: {method}")
            return False
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code < 400:
            try:
                json_data = response.json()
                print(f"Response Preview: {str(json_data)[:200]}...")
                print(f"✅ SUCCESS")
                return True
            except:
                print(f"Response: {response.text[:200]}...")
                print(f"✅ SUCCESS")
                return True
        else:
            print(f"❌ FAILED - {response.status_code}")
            print(f"Error: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return False

async def test_all_endpoints():
    """Test all API endpoints"""
    print("\n" + "="*60)
    print("🧪 COMPREHENSIVE ENDPOINT TESTING")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    results = {}
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Health & System
        results["health"] = await check_endpoint(
            client, "GET", "/api/v1/health",
            description="System health check"
        )
        
        # Settings
        results["settings_get"] = await check_endpoint(
            client, "GET", "/api/v1/settings/team-email",
            description="Get team email settings"
        )
        
        results["settings_post"] = await check_endpoint(
            client, "POST", "/api/v1/settings/team-email",
            data={
                "team_email": "test@example.com",
                "send_time": "09:00",
                "timezone": "UTC",
                "provider": "disabled",
                "enabled": False,
                "topics": ["RAG", "LLM"]
            },
            description="Save team email settings"
        )
        
        # Sources
        results["sources_status"] = await check_endpoint(
            client, "GET", "/api/v1/sources/status",
            description="Get sources status"
        )
        
        results["sources_stats"] = await check_endpoint(
            client, "GET", "/api/v1/sources/stats",
            description="Get sources statistics"
        )
        
        # Note: Not testing fetch as it takes too long
        print("\n⏭️  Skipping /api/v1/sources/fetch (too slow for testing)")
        
        # Copilot
        results["copilot_health"] = await check_endpoint(
            client, "GET", "/api/v1/copilot/health",
            description="Copilot health check"
        )
        
        results["copilot_analyze"] = await check_endpoint(
            client, "POST", "/api/v1/copilot/analyze",
            data={
                "brief": "I need to build a RAG system for legal documents",
                "requirements": ["accurate", "fast retrieval"],
                "constraints": ["limited budget"]
            },
            description="Analyze brief with research copilot"
        )
        
        # Dashboard
        results["dashboard"] = await check_endpoint(
            client, "GET", "/api/v1/dashboard/overview",
            description="Get dashboard overview"
        )
        
        # Intelligence
        results["intelligence_daily"] = await check_endpoint(
            client, "GET", "/api/v1/intelligence/daily",
            description="Get daily intelligence report"
        )
        
        # Briefs
        results["briefs_upload"] = await check_endpoint(
            client, "POST", "/api/v1/briefs/upload",
            data={
                "title": "Test Brief",
                "content": "Need a RAG system",
                "requirements": ["fast", "accurate"]
            },
            description="Upload a new brief"
        )
    
    # Summary
    print("\n\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    print(f"\nResults: {passed}/{total} endpoints passed")
    print("\nDetailed Results:")
    for endpoint, status in results.items():
        status_icon = "✅" if status else "❌"
        print(f"  {status_icon} {endpoint}")
    
    if passed == total:
        print("\n🎉 All endpoints working perfectly!")
    elif passed > total * 0.7:
        print(f"\n⚠️  Most endpoints working ({passed}/{total})")
    else:
        print(f"\n❌ Many endpoints failing ({total - passed}/{total} failed)")
    
    print("\n" + "="*60)
    return passed, total

if __name__ == "__main__":
    print("Make sure server is running on http://localhost:8000")
    print("Starting tests in 3 seconds...\n")
    import time
    time.sleep(3)
    
    passed, total = asyncio.run(test_all_endpoints())
