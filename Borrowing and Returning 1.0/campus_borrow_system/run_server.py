"""Lightweight runner to start the backend when executing from the project root.

Use this if you get "No module named 'backend'" when running `python backend/server.py`.

Preferred: run the app from the project root using the module form:
  python -m backend.server

This runner ensures the project root is on sys.path and then starts the server.
"""
import os
import sys

# Ensure project root (directory containing this file) is on sys.path so `import backend` works
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend import server

if __name__ == '__main__':
    # Default host/port match server.run defaults; change if needed
    server.run()
