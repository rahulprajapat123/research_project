"""Test if OpenAI API key is loaded"""
import os
from pathlib import Path

# Clear any cached settings
import config
if hasattr(config, '_get_settings'):
    config._get_settings.cache_clear()

from config import get_settings

print("=" * 70)
print("🔍 CHECKING API KEY LOADING")
print("=" * 70)

# Check .env file directly
env_file = Path(".env")
if env_file.exists():
    content = env_file.read_text(encoding='utf-8')
    if 'OPENAI_API_KEY=sk-' in content:
        print("\n✅ OpenAI API key found in .env file")
        # Extract just for verification (first 15 chars)
        for line in content.split('\n'):
            if line.startswith('OPENAI_API_KEY=sk-'):
                key_preview = line.split('=')[1][:15]
                print(f"   Preview: {key_preview}...")
    else:
        print("\n❌ OpenAI API key NOT found in .env file")
else:
    print("\n❌ .env file not found")

# Check if loaded by settings
settings = get_settings()
print(f"\n📦 Settings Configuration:")
print(f"   LLM Provider: {settings.llm_provider}")
print(f"   OpenAI Key Loaded: {bool(settings.openai_api_key)}")
if settings.openai_api_key:
    print(f"   Key Preview: {settings.openai_api_key[:15]}...")
else:
    print("   ❌ Key is None or empty!")

# Check environment variable
print(f"\n🌍 OS Environment Variable:")
env_key = os.getenv('OPENAI_API_KEY')
print(f"   OPENAI_API_KEY exists: {bool(env_key)}")
if env_key:
    print(f"   Preview: {env_key[:15]}...")

print("\n" + "=" * 70)

if settings.openai_api_key:
    print("✅ READY TO TEST - API key is configured!")
else:
    print("❌ NOT READY - API key not loaded by Pydantic Settings")
    print("\nTroubleshooting:")
    print("1. Make sure .env file has no BOM or encoding issues")
    print("2. Restart the FastAPI server completely")
    print("3. Check for any typos in variable name")

print("=" * 70)
