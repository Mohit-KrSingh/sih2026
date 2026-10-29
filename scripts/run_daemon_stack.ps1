# scripts/run_daemon_stack.ps1 - Long running daemon keeping PostgreSQL, Redis, Backend, and Frontend alive
$ErrorActionPreference = "Continue"

$pgBin = "C:\Users\Mohit\.local\share\apaar-tools\pgsql\postgresql-16.1.4-x86_64-pc-windows-msvc\bin"
$redisBin = "C:\Users\Mohit\.local\share\apaar-tools\redis\Redis-7.4.11-Windows-x64-msys2"

# Ensure directories
if (-not (Test-Path "data")) { New-Item -ItemType Directory -Path "data" | Out-Null }
if (-not (Test-Path "data/redis")) { New-Item -ItemType Directory -Path "data/redis" | Out-Null }

# Clean stale pid
if (Test-Path "data/postgres/postmaster.pid") {
    Write-Host "Removing stale postmaster.pid..."
    Remove-Item "data/postgres/postmaster.pid" -Force -ErrorAction SilentlyContinue
}

Write-Host "Starting PostgreSQL..."
& "$pgBin\pg_ctl.exe" -D "data/postgres" -l "data/pg_service.log" start
Start-Sleep -Seconds 3

Write-Host "Starting Redis..."
$redisProc = Start-Process -FilePath "$redisBin\redis-server.exe" -ArgumentList "--dir data/redis --port 6379" -PassThru -NoNewWindow
Start-Sleep -Seconds 1

Write-Host "Starting Backend..."
$py = (Resolve-Path ".venv\Scripts\python.exe").Path
$env:PYTHONPATH = (Resolve-Path "backend").Path
$backendProc = Start-Process -FilePath $py -ArgumentList "-m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000" -PassThru -NoNewWindow
Start-Sleep -Seconds 2

Write-Host "Starting Frontend..."
$frontendProc = Start-Process -FilePath "cmd.exe" -ArgumentList "/c npm run dev" -WorkingDirectory (Resolve-Path "frontend").Path -PassThru -NoNewWindow

Write-Host "Daemon stack started. Monitoring child processes..."

while ($true) {
    Start-Sleep -Seconds 15
    $pgStatus = & "$pgBin\pg_ctl.exe" -D "data/postgres" status 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "PostgreSQL not running, starting..."
        if (Test-Path "data/postgres/postmaster.pid") {
            Remove-Item "data/postgres/postmaster.pid" -Force -ErrorAction SilentlyContinue
        }
        & "$pgBin\pg_ctl.exe" -D "data/postgres" -l "data/pg_service.log" start
    }
    if ($redisProc.HasExited) {
        Write-Host "Redis exited, restarting..."
        $redisProc = Start-Process -FilePath "$redisBin\redis-server.exe" -ArgumentList "--dir data/redis --port 6379" -PassThru -NoNewWindow
    }
    if ($backendProc.HasExited) {
        Write-Host "Backend exited, restarting..."
        $backendProc = Start-Process -FilePath $py -ArgumentList "-m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000" -PassThru -NoNewWindow
    }
}
