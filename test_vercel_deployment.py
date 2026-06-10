"""
Quick script to test if your Vercel deployment is working
"""
import httpx
import asyncio

async def test_vercel_deployment():
    """Test various endpoints of deployed application"""
    
    print("="*70)
    print("🧪 VERCEL DEPLOYMENT TEST")
    print("="*70)
    print()
    
    # Get deployment URL from user
    deployment_url = input("Enter your Vercel deployment URL (e.g., https://research-project-xxxx.vercel.app): ").strip()
    
    if not deployment_url:
        print("❌ No URL provided")
        return
    
    # Remove trailing slash
    deployment_url = deployment_url.rstrip('/')
    
    print()
    print(f"Testing: {deployment_url}")
    print()
    
    # Test endpoints
    endpoints = [
        {
            "name": "Root Endpoint",
            "url": f"{deployment_url}/",
            "method": "GET",
            "expected": 200
        },
        {
            "name": "Health Check",
            "url": f"{deployment_url}/api/v1/health",
            "method": "GET",
            "expected": 200
        },
        {
            "name": "API Documentation",
            "url": f"{deployment_url}/docs",
            "method": "GET",
            "expected": 200
        },
        {
            "name": "Frontend - Copilot",
            "url": f"{deployment_url}/frontend/copilot.html",
            "method": "GET",
            "expected": 200
        },
        {
            "name": "Frontend - Styles",
            "url": f"{deployment_url}/frontend/styles.css",
            "method": "GET",
            "expected": 200
        }
    ]
    
    results = []
    
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        for endpoint in endpoints:
            try:
                print(f"Testing: {endpoint['name']}...")
                response = await client.request(
                    method=endpoint['method'],
                    url=endpoint['url']
                )
                
                status = "✅" if response.status_code == endpoint['expected'] else "❌"
                results.append({
                    "name": endpoint['name'],
                    "status_code": response.status_code,
                    "expected": endpoint['expected'],
                    "success": response.status_code == endpoint['expected'],
                    "size": len(response.content)
                })
                
                print(f"   {status} Status: {response.status_code} (Expected: {endpoint['expected']})")
                print(f"   📦 Response size: {len(response.content)} bytes")
                print()
                
            except Exception as e:
                results.append({
                    "name": endpoint['name'],
                    "status_code": None,
                    "expected": endpoint['expected'],
                    "success": False,
                    "error": str(e)
                })
                print(f"   ❌ Error: {e}")
                print()
    
    # Summary
    print("="*70)
    print("📊 TEST SUMMARY")
    print("="*70)
    print()
    
    successful = sum(1 for r in results if r.get('success'))
    total = len(results)
    
    print(f"Passed: {successful}/{total}")
    print()
    
    for result in results:
        status = "✅" if result.get('success') else "❌"
        print(f"{status} {result['name']}")
        if result.get('error'):
            print(f"   Error: {result['error']}")
    
    print()
    print("="*70)
    
    if successful == total:
        print("🎉 ALL TESTS PASSED!")
        print("✅ Your deployment is working correctly!")
        print()
        print("Next steps:")
        print(f"1. Visit: {deployment_url}/frontend/copilot.html")
        print("2. Upload a project brief")
        print("3. Test the recommendation system")
    elif successful > 0:
        print("⚠️  PARTIAL SUCCESS")
        print(f"✅ {successful} endpoints working")
        print(f"❌ {total - successful} endpoints failed")
        print()
        print("Check Vercel logs for failed endpoints:")
        print("   Vercel Dashboard → Your Project → Logs")
    else:
        print("❌ ALL TESTS FAILED")
        print()
        print("Possible issues:")
        print("1. Deployment still in progress (wait 2-3 minutes)")
        print("2. Build failed (check Vercel dashboard)")
        print("3. Wrong URL (verify deployment URL)")
        print("4. Environment variables missing")
    
    print("="*70)

if __name__ == "__main__":
    asyncio.run(test_vercel_deployment())
