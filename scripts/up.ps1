# scripts/up.ps1 - Start the APAAR stack
param (
    [switch]$Foreground
)

$ErrorActionPreference = "Stop"

# Check if Docker is available and running
$hasDocker = $false
try {
    $dockerVer = & docker --version 2>$null
    if ($LASTEXITCODE -eq 0) {
        $hasDocker = $true
    }
} catch {
    $hasDocker = $false
}

if ($hasDocker) {
    Write-Host "Starting stack with Docker Compose..."
    & docker compose up -d
    exit $LASTEXITCODE
}

Write-Host "Starting local services (Docker not detected)..."

# Ensure data directory exists
if (-not (Test-Path "data")) { New-Item -ItemType Directory -Path "data" | Out-Null }
if (-not (Test-Path "data/redis")) { New-Item -ItemType Directory -Path "data/redis" | Out-Null }

$pgBin = "C:\Users\Mohit\.local\share\apaar-tools\pgsql\postgresql-16.1.4-x86_64-pc-windows-msvc\bin"
$redisBin = "C:\Users\Mohit\.local\share\apaar-tools\redis\Redis-7.4.11-Windows-x64-msys2"

# 1. PostgreSQL
$pgRunning = $false
try {
    $conn = New-Object System.Net.Sockets.TcpClient
    $conn.Connect("127.0.0.1", 5432)
    $conn.Close()
    $pgRunning = $true
} catch {
    $pgRunning = $false
}

if (-not $pgRunning) {
    if (Test-Path "data/postgres/postmaster.pid") {
        Write-Host "Cleaning stale postmaster.pid..."
        Remove-Item "data/postgres/postmaster.pid" -Force -ErrorAction SilentlyContinue
    }
    if (-not (Test-Path "data/postgres")) {
        Write-Host "Initializing PostgreSQL cluster..."
        & "$pgBin\initdb.exe" -D "data/postgres" -U apaar -A trust -E UTF8 | Out-Null
    }
    Write-Host "Starting PostgreSQL server..."
    & "$pgBin\pg_ctl.exe" -D "data/postgres" -l "data/pg_service.log" start
    $retries = 40
    while ($retries -gt 0) {
        Start-Sleep -Seconds 1
        try {
            $conn = New-Object System.Net.Sockets.TcpClient
            $conn.Connect("127.0.0.1", 5432)
            $conn.Close()
            break
        } catch {
            $retries--
        }
    }

    # Create databases if they do not exist
    try { & "$pgBin\createdb.exe" -U apaar -h 127.0.0.1 apaar_db 2>$null } catch {}
    try { & "$pgBin\createdb.exe" -U apaar -h 127.0.0.1 apaar_test_db 2>$null } catch {}
} else {
    Write-Host "PostgreSQL is already running on port 5432."
}

# 2. Redis
$redisRunning = $false
try {
    $conn = New-Object System.Net.Sockets.TcpClient
    $conn.Connect("127.0.0.1", 6379)
    $conn.Close()
    $redisRunning = $true
} catch {
    $redisRunning = $false
}

if (-not $redisRunning) {
    Write-Host "Starting Redis server..."
    Start-Process -FilePath "$redisBin\redis-server.exe" -ArgumentList "--dir data/redis --port 6379" -WindowStyle Hidden
    Start-Sleep -Seconds 1
} else {
    Write-Host "Redis is already running on port 6379."
}

# 3. Backend (FastAPI / Uvicorn)
$backendRunning = $false
try {
    $conn = New-Object System.Net.Sockets.TcpClient
    $conn.Connect("127.0.0.1", 8000)
    $conn.Close()
    $backendRunning = $true
} catch {
    $backendRunning = $false
}

if (-not $backendRunning) {
    Write-Host "Starting backend API server on port 8000..."
    $pyPath = if (Test-Path ".venv\Scripts\python.exe") { (Resolve-Path ".venv\Scripts\python.exe").Path } else { "python" }
    $backendArgs = @("-m", "uvicorn", "app.main:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8000")
    Start-Process -FilePath $pyPath -ArgumentList $backendArgs -WindowStyle Hidden
    Start-Sleep -Seconds 3
} else {
    Write-Host "Backend is already running on port 8000."
}

# 4. Frontend (Vite)
$frontendRunning = $false
try {
    $conn = New-Object System.Net.Sockets.TcpClient
    $conn.Connect("127.0.0.1", 5173)
    $conn.Close()
    $frontendRunning = $true
} catch {
    $frontendRunning = $false
}

if (-not $frontendRunning) {
    Write-Host "Starting frontend dev server on port 5173..."
    Start-Process -FilePath "cmd.exe" -ArgumentList "/c npm run dev" -WorkingDirectory (Resolve-Path "frontend").Path -WindowStyle Hidden
    Start-Sleep -Seconds 2
} else {
    Write-Host "Frontend is already running on port 5173."
}

Write-Host "Stack started successfully."
Write-Host "Backend:  http://localhost:8000 (docs: http://localhost:8000/docs)"
Write-Host "Frontend: http://localhost:5173"

if ($Foreground) {
    Write-Host "Running in foreground mode (keeping daemon alive)..."
    while ($true) { Start-Sleep -Seconds 5 }
}
