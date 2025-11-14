Param(
  [string]$HostName = "127.0.0.1",
  [string]$User = "root",
  [string]$Password = "",
  [string]$Database = "campus_borrowing_system",
  [int]$Port = 8000,
  [switch]$InitDB
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$backendDir = Join-Path $scriptDir 'backend'
$dbConfigPath = Join-Path $backendDir 'db_config.json'

Write-Host "Writing DB config to $dbConfigPath"
$cfg = @{
  host = $HostName
  user = $User
  password = $Password
  database = $Database
  raise_on_warnings = $true
}
$json = $cfg | ConvertTo-Json -Depth 5
Set-Content -Path $dbConfigPath -Value $json -Encoding UTF8

Write-Host "Checking for mysql-connector-python..."
& python -c 'import mysql.connector'
if ($LASTEXITCODE -ne 0) {
  Write-Host 'mysql-connector-python not found - installing via pip (may require admin rights)...'
  & pip install mysql-connector-python
  if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to install mysql-connector-python. Please install it manually and re-run this script." -ForegroundColor Red
    exit 1
  }
}

if ($InitDB) {
  Write-Host "Initializing database (will create DB and tables if needed)..."
  & python -c 'from backend.database import init_db; init_db()'
  if ($LASTEXITCODE -ne 0) {
    Write-Host "Database initialization had errors. Check MySQL credentials and server." -ForegroundColor Yellow
  }
} else {
  Write-Host "Skipping DB init (use -InitDB to run schema)."
}

Write-Host 'Ensuring default admin user exists (username: admin, password: AdminPass123)'
& python -m backend.create_admin
if ($LASTEXITCODE -ne 0) {
  Write-Host "Admin creation script returned an error. Check DB and backend/create_admin.py" -ForegroundColor Yellow
}

Write-Host "Starting backend server (blocking) on $($HostName):$($Port)..."
& python -m backend.server
