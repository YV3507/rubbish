<#
.SYNOPSIS
    Unified run entry point for the Rubbish monorepo.
    Start/stop individual sub-projects for development or the full stack via docker-compose.

.DESCRIPTION
    Provides shortcuts for common development workflows:
      - Start backend  (FastAPI / uvicorn)
      - Start frontend (Vite dev server)
      - Start compute  (Rust Axum microservice)
      - Full stack     (docker-compose up)
      - Stop all       (gracefully stop background services)

.PARAMETER Target
    What to run: "backend", "frontend", "compute", "docker", "all", "stop", or "help".

.PARAMETER Port
    Override the default port for the target service.

.PARAMETER Detach
    (docker only) Run containers in detached mode (-d).

.PARAMETER Dev
    (all mode only) Open separate terminal windows for each service instead of running silently in background. Useful for development and debugging.

.PARAMETER Install
    Install dependencies before running (npm install / cargo build).

.PARAMETER Help
    Show this help message.

.EXAMPLE
    .\run.ps1 backend
    .\run.ps1 frontend
    .\run.ps1 compute
    .\run.ps1 all                    # Starts 3 services in background (silent)
    .\run.ps1 all -Dev               # Starts 3 services in separate windows (dev mode)
    .\run.ps1 stop                   # Stops all background services gracefully
    .\run.ps1 docker
    .\run.ps1 backend -Port 9000
    .\run.ps1 docker -Detach
    .\run.ps1 all -Install
#>

param(
    [ValidateSet("backend", "frontend", "compute", "docker", "all", "stop", "help")]
    [string]$Target = "help",

    [int]$Port = 0,
    [switch]$Detach,
    [switch]$Install,
    [switch]$Dev,
    [switch]$Help
)

$ErrorActionPreference = "Stop"
$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RunDir = "$RootDir/run"

function Show-Help {
    Get-Content -Path $MyInvocation.ScriptName | Select-String -Pattern "^#" | ForEach-Object {
        $_ -replace "^#\s?", ""
    }
}

function Write-Header {
    param([string]$Title, [string]$Color = "Cyan")
    Write-Host "`n$("-" * 50)" -ForegroundColor $Color
    Write-Host "  $Title" -ForegroundColor $Color
    Write-Host "$("-" * 50)" -ForegroundColor $Color
}

# ── PID file helpers ──
function Save-Pid {
    param([string]$Name, [int]$ProcessId)
    if (-not (Test-Path $RunDir)) { New-Item -ItemType Directory -Path $RunDir -Force | Out-Null }
    $ProcessId | Out-File "$RunDir/$Name.pid" -Force
}

function Read-Pid {
    param([string]$Name)
    $path = "$RunDir/$Name.pid"
    if (Test-Path $path) {
        try { return [int](Get-Content $path -Raw).Trim() } catch { return $null }
    }
    return $null
}

function Remove-PidFile {
    param([string]$Name)
    $path = "$RunDir/$Name.pid"
    if (Test-Path $path) { Remove-Item $path -Force }
}

function Clear-All-PidFiles {
    if (Test-Path $RunDir) { Remove-Item "$RunDir/*.pid" -Force -ErrorAction SilentlyContinue }
}

function Stop-ServiceByPid {
    param([string]$Name, [string]$Label)
    $savedPid = Read-Pid $Name
    if (-not $savedPid) {
        Write-Host "  [SKIP] $Label — no PID file found" -ForegroundColor Gray
        return
    }
    try {
        $proc = Get-Process -Id $savedPid -ErrorAction Stop
        Write-Host "  Stopping $Label (PID $savedPid)..." -ForegroundColor Yellow
        # Stop-Process sends WM_CLOSE on Windows = graceful shutdown
        Stop-Process -Id $savedPid -Force -ErrorAction SilentlyContinue
        # Wait up to 5 seconds for process to exit
        $wait = 0
        while ($wait -lt 5 -and (Get-Process -Id $savedPid -ErrorAction SilentlyContinue)) {
            Start-Sleep -Milliseconds 500
            $wait += 0.5
        }
        # If still running, force kill
        if (Get-Process -Id $savedPid -ErrorAction SilentlyContinue) {
            Write-Host "  Force killing $Label..." -ForegroundColor DarkYellow
            Stop-Process -Id $savedPid -Force -ErrorAction SilentlyContinue
        } else {
            Write-Host "  [OK] $Label stopped gracefully" -ForegroundColor Green
        }
    } catch {
        Write-Host "  [OK] $Label is not running" -ForegroundColor Green
    }
    Remove-PidFile $Name
}

# ── Backend ──
function Start-Backend {
    Write-Header "Starting Backend (FastAPI + Uvicorn)"

    Push-Location "$RootDir/backend"
    try {
        if ($Install) {
            Write-Host "  Installing Python dependencies..." -ForegroundColor Yellow
            pip install -e . 2>&1 | Out-Null
        }

        $svcPort = if ($Port -gt 0) { $Port } else { 8000 }

        Write-Host "  Backend starting at http://localhost:$svcPort" -ForegroundColor Green
        python -m uvicorn app.main:app --reload --host 0.0.0.0 --port $svcPort
    }
    finally {
        Pop-Location
    }
}

# ── Frontend ──
function Start-Frontend {
    Write-Header "Starting Frontend (Vite Dev Server)"

    Push-Location "$RootDir/frontend"
    try {
        if (-not (Test-Path "node_modules")) {
            if ($Install) {
                Write-Host "  Installing npm dependencies..." -ForegroundColor Yellow
                npm install 2>&1 | Out-Null
            } else {
                Write-Host "  node_modules not found. Run '.\run.ps1 frontend -Install' first." -ForegroundColor Red
                exit 1
            }
        }

        $frontendPort = if ($Port -gt 0) { $Port } else { 5173 }

        Write-Host "  Frontend starting at http://localhost:$frontendPort" -ForegroundColor Green
        npx vite --port $frontendPort
    }
    finally {
        Pop-Location
    }
}

# ── Compute Node ──
function Start-Compute {
    Write-Header "Starting Compute Node (Rust Axum)"

    Push-Location "$RootDir/compute-node"
    try {
        if ($Install) {
            Write-Host "  Building Rust project..." -ForegroundColor Yellow
            cargo build 2>&1 | Out-Null
        }

        # Check if binary exists
        $binaryPath = "target/debug/rubbish-compute.exe"
        if (-not (Test-Path $binaryPath)) {
            Write-Host "  Binary not found at $binaryPath. Run '.\run.ps1 compute -Install' first." -ForegroundColor Red
            exit 1
        }

        if ($Port -gt 0) {
            $env:COMPUTE_PORT = $Port.ToString()
        } else {
            $env:COMPUTE_PORT = "8080"
        }

        # Default DB path to project-local data directory
        $dataDir = "$RootDir/data/compute"
        if (-not (Test-Path $dataDir)) { New-Item -ItemType Directory -Path $dataDir -Force | Out-Null }
        $env:COMPUTE_DB_PATH = "$dataDir/codegraph.db"

        Write-Host "  Compute Node starting at http://localhost:$env:COMPUTE_PORT" -ForegroundColor Green
        Write-Host "  DB path: $env:COMPUTE_DB_PATH" -ForegroundColor Gray
        cargo run
    }
    finally {
        Pop-Location
    }
}

# ── Docker Compose ──
function Start-Docker {
    Write-Header "Starting Full Stack (docker-compose)"

    Push-Location $RootDir
    try {
        Write-Host "  Starting backend:8000 + compute:8080 + frontend:3000" -ForegroundColor Green
        if ($Detach) {
            docker-compose up --build -d
        }
        else {
            docker-compose up --build
        }
    }
    finally {
        Pop-Location
    }
}

# ── Stop all background services ──
function Stop-All {
    Write-Header "Stopping Background Services"

    # Stop in reverse order: frontend → backend → compute
    Stop-ServiceByPid "frontend" "Frontend (Vite)"
    Stop-ServiceByPid "backend"  "Backend (FastAPI)"
    Stop-ServiceByPid "compute"  "Compute (Rust)"

    Clear-All-PidFiles
    Write-Host "`n  All services stopped." -ForegroundColor Cyan
}

# ── All (backend + compute + frontend in parallel) ──
function Start-All {
    Write-Header "Starting Backend + Compute + Frontend"

    $backendPort = if ($Port -gt 0) { $Port } else { 8000 }
    $computePort = $backendPort + 80   # 8080
    $frontendPort = $backendPort + 3000

    if ($Dev) {
        # ── Dev mode: open separate terminal windows ──
        $installFlag = if ($Install) { "-Install" } else { "" }

        Write-Host "  Opening 3 terminal windows..." -ForegroundColor Yellow
        Write-Host "  Backend:  http://localhost:$backendPort" -ForegroundColor Green
        Write-Host "  Compute:  http://localhost:$computePort" -ForegroundColor Green
        Write-Host "  Frontend: http://localhost:$frontendPort" -ForegroundColor Green
        Write-Host "  Use Ctrl+C in each window, or run '.\run.ps1 stop'`n" -ForegroundColor Yellow

        # Compute Node
        $compProc = Start-Process powershell -ArgumentList "-NoExit", "-Command", "& '$RootDir\run.ps1' compute -Port $computePort $installFlag" -PassThru
        Save-Pid "compute" $compProc.Id
        Start-Sleep -Seconds 3

        # Backend
        $beProc = Start-Process powershell -ArgumentList "-NoExit", "-Command", "& '$RootDir\run.ps1' backend -Port $backendPort $installFlag" -PassThru
        Save-Pid "backend" $beProc.Id
        Start-Sleep -Seconds 2

        # Frontend
        $feProc = Start-Process powershell -ArgumentList "-NoExit", "-Command", "& '$RootDir\run.ps1' frontend -Port $frontendPort $installFlag" -PassThru
        Save-Pid "frontend" $feProc.Id

        Write-Host "  All 3 services started in separate windows." -ForegroundColor Cyan
        Write-Host "  To stop: .\run.ps1 stop" -ForegroundColor Yellow
    }
    else {
        # ── Background silent mode (default) ──

        # Prepare log directory
        $logDir = "$RootDir/logs"
        if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }

        Write-Host "  Starting services in background (silent mode)..." -ForegroundColor Yellow
        Write-Host "  Logs directory: $logDir" -ForegroundColor Gray
        Write-Host "  Backend:  http://localhost:$backendPort" -ForegroundColor Green
        Write-Host "  Compute:  http://localhost:$computePort" -ForegroundColor Green
        Write-Host "  Frontend: http://localhost:$frontendPort" -ForegroundColor Green

        # Compute Node
        Write-Host "  [1/3] Starting Compute Node..." -ForegroundColor Gray
        $env:COMPUTE_PORT = $computePort.ToString()
        $dataDir = "$RootDir/data/compute"
        if (-not (Test-Path $dataDir)) { New-Item -ItemType Directory -Path $dataDir -Force | Out-Null }
        $env:COMPUTE_DB_PATH = "$dataDir/codegraph.db"
        $compLog = "$logDir/compute.log"
        $compErr = "$logDir/compute.err"
        $compProc = Start-Process -WindowStyle Hidden -FilePath "cargo" -ArgumentList "run" `
            -WorkingDirectory "$RootDir/compute-node" `
            -RedirectStandardOutput $compLog -RedirectStandardError $compErr -PassThru
        Save-Pid "compute" $compProc.Id
        Start-Sleep -Seconds 8

        # Backend
        Write-Host "  [2/3] Starting Backend..." -ForegroundColor Gray
        $beLog = "$logDir/backend.log"
        $beErr = "$logDir/backend.err"
        $beProc = Start-Process -WindowStyle Hidden -FilePath "python" -ArgumentList "-m", "uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", $backendPort `
            -WorkingDirectory "$RootDir/backend" `
            -RedirectStandardOutput $beLog -RedirectStandardError $beErr -PassThru
        Save-Pid "backend" $beProc.Id
        Start-Sleep -Seconds 3

        # Frontend
        Write-Host "  [3/3] Starting Frontend..." -ForegroundColor Gray
        $feLog = "$logDir/frontend.log"
        $feErr = "$logDir/frontend.err"
        $feProc = Start-Process -WindowStyle Hidden -FilePath "cmd.exe" -ArgumentList "/c", "npx", "vite", "--port", $frontendPort `
            -WorkingDirectory "$RootDir/frontend" `
            -RedirectStandardOutput $feLog -RedirectStandardError $feErr -PassThru
        Save-Pid "frontend" $feProc.Id

        Write-Host "`n  All 3 services started in background." -ForegroundColor Cyan
        Write-Host "  View logs: $logDir\*.log / *.err" -ForegroundColor Yellow
        Write-Host "  To stop: .\run.ps1 stop" -ForegroundColor Yellow
    }
}

# ── Entry Point ──
if ($Help -or $Target -eq "help") {
    Show-Help
    exit 0
}

switch ($Target) {
    "backend"  { Start-Backend }
    "frontend" { Start-Frontend }
    "compute"  { Start-Compute }
    "docker"   { Start-Docker }
    "all"      { Start-All }
    "stop"     { Stop-All }
}
