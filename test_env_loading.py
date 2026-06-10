"""Test environment loading with explicit path"""
from pathlib import Path
from dotenv import load_dotenv

# Get current directory
current_dir = Path(__file__).parent
env_file = current_dir / ".env"

print(f"Current directory: {current_dir}")
print(f"Looking for .env at: {env_file}")
print(f".env exists: {env_file.exists()}")

if env_file.exists():
    print("\nLoading .env file...")
    load_dotenv(env_file, override=True)
    
    import os
    print("\n🔑 Environment Variables After Load:")
    print(f"  GNEWS_API_KEY: {os.getenv('GNEWS_API_KEY', 'NOT SET')[:20]}...")
    print(f"  NEWSAPI_KEY: {os.getenv('NEWSAPI_KEY', 'NOT SET')[:20]}...")
    print(f"  GITHUB_TOKEN: {os.getenv('GITHUB_TOKEN', 'NOT SET')[:20]}...")
    print(f"  APIFY_API_TOKEN: {os.getenv('APIFY_API_TOKEN', 'NOT SET')[:20]}...")
    print(f"  OPENALEX_CONTACT_EMAIL: {os.getenv('OPENALEX_CONTACT_EMAIL', 'NOT SET')}")
    
    # Now test with config
    print("\n📦 Testing with Pydantic Settings...")
    from config import get_settings
    settings = get_settings()
    print(f"  GNews: {'✅' if settings.gnews_api_key else '❌'}")
    print(f"  NewsAPI: {'✅' if settings.newsapi_key else '❌'}")
    print(f"  GitHub: {'✅' if settings.github_token else '❌'}")
    print(f"  Apify: {'✅' if settings.apify_api_token else '❌'}")
else:
    print("\n❌ .env file not found!")
