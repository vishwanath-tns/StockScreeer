Chart Tool
==========

This is a lightweight charting tool that consumes data produced by the StockScreeer scanners.

Two integration options:
- Direct import: the chart tool imports scanner service functions (fast for local dev).
- REST API: the chart tool calls a small REST wrapper provided by the scanner service (recommended for process separation).

Quick start (direct import mode)
1. Create and activate a virtualenv in this folder:

    python -m venv .venv
    .\.venv\Scripts\Activate.ps1  # PowerShell on Windows

2. Install dependencies:

    pip install -r requirements.txt

3. Ensure the scanner project root (repo root) is on PYTHONPATH so the chart tool can import scanner services:

    $env:PYTHONPATH = 'D:\MyProjects\StockScreeer'

4. Run the app:

    python app.py

Configuration
- See `.env.example` for optional environment variables (REST_API_BASE or DB credentials).

Files
- `services_client.py`: adapter that fetches OHLCV/RSI/scan results from the scanner code (or REST wrapper).
- `plotting.py`: Plotly-based chart building helpers.
- `app.py`: minimal Dash app demonstrating interactive charting.

Next steps
- Add more plotting options (indicators, overlays), caching, and tests.
