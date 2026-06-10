"""Test settings endpoint"""
import asyncio
import httpx

async def test_settings():
    base_url = "http://localhost:8000"
    
    print("Testing settings endpoint...")
    
    async with httpx.AsyncClient() as client:
        # Test GET endpoint
        print("\n1. Testing GET /api/v1/settings/team-email")
        try:
            response = await client.get(f"{base_url}/api/v1/settings/team-email")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.json()}")
        except Exception as e:
            print(f"   Error: {e}")
        
        # Test POST endpoint
        print("\n2. Testing POST /api/v1/settings/team-email")
        test_data = {
            "team_email": "test@example.com",
            "send_time": "09:00",
            "timezone": "America/New_York",
            "provider": "smtp",
            "enabled": True,
            "topics": ["RAG", "LLM"]
        }
        try:
            response = await client.post(
                f"{base_url}/api/v1/settings/team-email",
                json=test_data
            )
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.json()}")
        except Exception as e:
            print(f"   Error: {e}")
        
        # Verify settings were saved
        print("\n3. Verifying saved settings")
        try:
            response = await client.get(f"{base_url}/api/v1/settings/team-email")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.json()}")
        except Exception as e:
            print(f"   Error: {e}")

if __name__ == "__main__":
    print("="*60)
    print("Settings API Test")
    print("="*60)
    print("\nMake sure the server is running: python main.py")
    print("\nStarting test...\n")
    asyncio.run(test_settings())
    print("\n" + "="*60)
    print("Test complete!")
    print("="*60)
