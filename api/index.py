"""
Vercel serverless function entry point
This wraps the FastAPI app for Vercel's serverless architecture
"""
from main import app

# Vercel expects a handler function
handler = app
