"""
Vercel serverless function entry point
This wraps the FastAPI app for Vercel's serverless architecture
"""
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main import app

# Vercel expects an 'app' or 'handler' variable
handler = app

# Also export as 'app' for compatibility
__all__ = ['app', 'handler']
