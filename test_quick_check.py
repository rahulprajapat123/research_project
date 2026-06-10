"""
Quick endpoint connectivity test
"""
import requests

print("=" * 70)
print("🔗 TESTING BACKEND CONNECTIVITY")
print("=" * 70)

# Test 1: Health check
print("\n1. Testing /api/v1/health...")
try:
    response = requests.get("http://localhost:8000/api/v1/health")
    if response.status_code == 200:
        print(f"   ✅ Health: {response.json()}")
    else:
        print(f"   ❌ Status: {response.status_code}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 2: Copilot health
print("\n2. Testing /api/v1/copilot/health...")
try:
    response = requests.get("http://localhost:8000/api/v1/copilot/health")
    if response.status_code == 200:
        print(f"   ✅ Copilot Health: {response.json()}")
    else:
        print(f"   ❌ Status: {response.status_code}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 3: Check what's configured
print("\n3. Checking configuration...")
from config import get_settings
settings = get_settings()
print(f"   OpenAI Key: {'✅ Configured' if settings.openai_api_key else '❌ Missing'}")
print(f"   Anthropic Key: {'✅ Configured' if settings.anthropic_api_key else '❌ Missing'}")
print(f"   LLM Provider: {settings.llm_provider}")

if not settings.openai_api_key and not settings.anthropic_api_key:
    print("\n⚠️  WARNING: No LLM API key configured!")
    print("   The copilot endpoint requires OpenAI or Anthropic API key.")
    print("   Add OPENAI_API_KEY= or ANTHROPIC_API_KEY= to your .env file")

# Test 4: Simple copilot request
print("\n4. Testing copilot endpoint with minimal request...")
try:
    response = requests.post(
        "http://localhost:8000/api/v1/copilot/analyze",
        json={
            "project_name": "Test",
            "project_brief": "Build a simple chatbot"
        },
        timeout=10
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print("   ✅ Endpoint is working!")
    elif response.status_code == 500:
        print("   ❌ 500 Error - Check server logs above")
        error = response.json()
        print(f"   Error: {error.get('detail', 'Unknown error')[:100]}")
    else:
        print(f"   ⚠️  Response: {response.text[:200]}")
except requests.exceptions.Timeout:
    print("   ⏰ Request timeout (expected - LLM processing)")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n" + "=" * 70)
print("📝 SUMMARY")
print("=" * 70)
print("If you see a 500 error, the most common causes are:")
print("  1. Missing OpenAI/Anthropic API key")
print("  2. Network connectivity issues")
print("  3. Invalid API key")
print("\nCheck the server terminal for detailed error logs.")
print("=" * 70)
