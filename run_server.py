"""Launcher: load .env then start uvicorn so the server process inherits the repo .env.

Run this from the repo root:
    python run_server.py

This avoids PowerShell quoting issues when loading .env into the shell.
"""
from pathlib import Path
import os
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
env_path = ROOT / '.env'
if env_path.exists():
    load_dotenv(env_path)
    print(f"Loaded .env from: {env_path}")
else:
    print(f"No .env found at: {env_path}; proceeding with existing environment")

print(f"MYSQL_USER={os.environ.get('MYSQL_USER')}, MYSQL_HOST={os.environ.get('MYSQL_HOST')} (password masked)")

import uvicorn

if __name__ == '__main__':
    # run uvicorn programmatically so it inherits env we just loaded
    uvicorn.run('scanner_api:app', host='127.0.0.1', port=5000, reload=True)
