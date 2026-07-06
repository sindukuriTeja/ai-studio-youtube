"""Vercel serverless entry point for the FastAPI app."""
import sys
from pathlib import Path

# Add project root to path so backend package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.main import app
