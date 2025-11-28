# Setup MySQL MCP Server for VS Code
# This script installs and configures MySQL MCP server for your stock database

Write-Host "Setting up MySQL MCP Server..." -ForegroundColor Green

# Step 1: Install MySQL MCP Server globally
Write-Host "`n1. Installing MySQL MCP Server..." -ForegroundColor Yellow
npm install -g @modelcontextprotocol/server-mysql

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to install MySQL MCP server. Make sure Node.js and npm are installed." -ForegroundColor Red
    exit 1
}

Write-Host "✅ MySQL MCP Server installed successfully" -ForegroundColor Green

# Step 2: Load database credentials from .env
Write-Host "`n2. Loading database credentials..." -ForegroundColor Yellow
$envFile = Join-Path $PSScriptRoot ".env"

if (-not (Test-Path $envFile)) {
    Write-Host "❌ .env file not found. Please create it first." -ForegroundColor Red
    exit 1
}

$env:MYSQL_HOST = "localhost"
$env:MYSQL_PORT = "3306"
$env:MYSQL_DB = "marketdata"
$env:MYSQL_USER = "root"
$env:MYSQL_PASSWORD = ""

Get-Content $envFile | ForEach-Object {
    if ($_ -match '^MYSQL_HOST=(.+)$') { $env:MYSQL_HOST = $matches[1] }
    if ($_ -match '^MYSQL_PORT=(.+)$') { $env:MYSQL_PORT = $matches[1] }
    if ($_ -match '^MYSQL_DB=(.+)$') { $env:MYSQL_DB = $matches[1] }
    if ($_ -match '^MYSQL_USER=(.+)$') { $env:MYSQL_USER = $matches[1] }
    if ($_ -match '^MYSQL_PASSWORD=(.+)$') { $env:MYSQL_PASSWORD = $matches[1] }
}

Write-Host "   Host: $env:MYSQL_HOST" -ForegroundColor Cyan
Write-Host "   Port: $env:MYSQL_PORT" -ForegroundColor Cyan
Write-Host "   Database: $env:MYSQL_DB" -ForegroundColor Cyan
Write-Host "   User: $env:MYSQL_USER" -ForegroundColor Cyan

# Step 3: URL-encode the password
Add-Type -AssemblyName System.Web
$encodedPassword = [System.Web.HttpUtility]::UrlEncode($env:MYSQL_PASSWORD)

# Step 4: Create connection string
$connectionString = "mysql://$env:MYSQL_USER`:$encodedPassword@$env:MYSQL_HOST`:$env:MYSQL_PORT/$env:MYSQL_DB"

# Step 5: Create MCP configuration
Write-Host "`n3. Creating MCP configuration..." -ForegroundColor Yellow

$mcpConfig = @{
    "mysql-marketdata" = @{
        "command" = "npx"
        "args" = @(
            "-y"
            "@modelcontextprotocol/server-mysql"
            $connectionString
        )
    }
}

# Step 6: Find VS Code settings file
$settingsPath = "$env:APPDATA\Code\User\settings.json"

if (-not (Test-Path $settingsPath)) {
    Write-Host "Creating new VS Code settings file..." -ForegroundColor Yellow
    $settings = @{}
} else {
    Write-Host "Loading existing VS Code settings..." -ForegroundColor Yellow
    $settings = Get-Content $settingsPath | ConvertFrom-Json -AsHashtable
    if ($null -eq $settings) {
        $settings = @{}
    }
}

# Step 7: Add or update MCP configuration
if (-not $settings.ContainsKey("github.copilot.chat.mcp.servers")) {
    $settings["github.copilot.chat.mcp.servers"] = @{}
}

$settings["github.copilot.chat.mcp.servers"]["mysql-marketdata"] = $mcpConfig["mysql-marketdata"]

# Step 8: Save settings
Write-Host "`n4. Saving VS Code settings..." -ForegroundColor Yellow
$settings | ConvertTo-Json -Depth 10 | Set-Content $settingsPath -Encoding UTF8

Write-Host "✅ MCP configuration saved to: $settingsPath" -ForegroundColor Green

# Step 9: Display instructions
Write-Host "`n" + "="*80 -ForegroundColor Green
Write-Host "✅ MySQL MCP Server Setup Complete!" -ForegroundColor Green
Write-Host "="*80 -ForegroundColor Green

Write-Host "`nNext Steps:" -ForegroundColor Yellow
Write-Host "1. Restart VS Code for changes to take effect"
Write-Host "2. After restart, I'll be able to query your MySQL database directly"
Write-Host "3. Test by asking me to: 'Show tables in the database' or 'Query NIFTY data'"

Write-Host "`nMCP Server Name: mysql-marketdata" -ForegroundColor Cyan
Write-Host "Database: $env:MYSQL_DB on $env:MYSQL_HOST`:$env:MYSQL_PORT" -ForegroundColor Cyan

Write-Host "`nPress any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
