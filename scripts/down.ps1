# scripts/down.ps1 - Stop the APAAR stack
$ErrorActionPreference = "SilentlyContinue"

# Check if Docker is running
try {
    & docker compose down 2>$null
} catch {}

Write-Host "Stopping local services..."

# Stop frontend (node/vite) on port 5173
$port5173 = Get-NetTCPConnection -LocalPort 5173 -State Listen 2>$null
if ($port5173) {
    Stop-Process -Id $port5173.OwningProcess -Force 2>$null
}

# Stop backend on port 8000
$port8000 = Get-NetTCPConnection -LocalPort 8000 -State Listen 2>$null
if ($port8000) {
    Stop-Process -Id $port8000.OwningProcess -Force 2>$null
}

# Stop Redis
$redisBin = "C:\Users\Mohit\.local\share\apaar-tools\redis\Redis-7.4.11-Windows-x64-msys2"
try {
    & "$redisBin\redis-cli.exe" shutdown 2>$null
} catch {}
Get-Process "redis-server" 2>$null | Stop-Process -Force 2>$null

# Stop PostgreSQL
$pgBin = "C:\Users\Mohit\.local\share\apaar-tools\pgsql\postgresql-16.1.4-x86_64-pc-windows-msvc\bin"
try {
    & "$pgBin\pg_ctl.exe" -D "data/postgres" -m fast stop 2>$null
} catch {}
Get-Process "postgres" 2>$null | Stop-Process -Force 2>$null

Write-Host "All services stopped."
