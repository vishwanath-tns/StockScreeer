# MySQL MCP Server Setup Guide for StockScreener Project

## Prerequisites

You need Node.js installed to use MCP servers.

### Install Node.js

1. Download Node.js LTS from: https://nodejs.org/
2. Run the installer (choose all default options)
3. Restart PowerShell after installation

## Quick Setup (After Node.js is installed)

Run this command in your project directory:
```powershell
.\setup_mcp_mysql.ps1
```

## Manual Setup (If you prefer)

### 1. Install MySQL MCP Server
```powershell
npm install -g @modelcontextprotocol/server-mysql
```

### 2. Add to VS Code Settings

Open VS Code Settings (Ctrl + ,), click the "Open Settings (JSON)" icon in the top right.

Add this configuration (replace password with your actual password):

```json
{
  "github.copilot.chat.mcp.servers": {
    "mysql-marketdata": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-mysql",
        "mysql://root:Ganesh%40%402283%40%40@localhost:3306/marketdata"
      ]
    }
  }
}
```

**Note:** The `%40%40` is the URL-encoded version of `@@` in your password.

### 3. Restart VS Code

Close and reopen VS Code for the MCP server to start.

## What This Enables

Once set up, I can:

✅ Query your database directly without Python scripts
```
Example: "Show me all NIFTY candles from today"
Example: "Count rows in intraday_advance_decline table"
Example: "Show table structure for nse_yahoo_symbol_map"
```

✅ Analyze data patterns
```
Example: "Find stocks with highest volume today"
Example: "Show advance/decline ratio trends"
```

✅ Debug data issues
```
Example: "Check for any NULL values in prev_close column"
Example: "Find duplicate entries in intraday_1min_candles"
```

## Verification

After setup, test with: "Show all tables in marketdata database"

## Troubleshooting

**"npm is not recognized"**
- Node.js not installed or not in PATH
- Restart PowerShell after Node.js installation

**"Connection refused"**
- MySQL server not running
- Check credentials in connection string

**MCP server not working after restart**
- Check VS Code Output panel → "MCP Servers" for errors
- Verify settings.json syntax is valid JSON
