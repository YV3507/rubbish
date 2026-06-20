<#
.SYNOPSIS
    Unified test runner for Rubbish monorepo.
    Runs tests for backend, compute-node, or frontend.

.PARAMETER Module
    "backend", "compute-node", "frontend", or "all" (default).

.PARAMETER Watch
    Frontend vitest watch mode.

.PARAMETER Coverage
    Backend pytest with coverage.

.PARAMETER Integration
    Include integration tests (requires compute-node binary built).

.EXAMPLE
    .\runtests.ps1
    .\runtests.ps1 -Module backend
    .\runtests.ps1 -Module frontend
    .\runtests.ps1 -Integration
#>

param(
    [ValidateSet("backend", "compute-node", "frontend", "all")]
    [string]$Module = "all",
    [switch]$Watch,
    [switch]$Coverage,
    [switch]$Integration
)

$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Passed = 0; $Failed = 0; $Skipped = 0
$BackendDir = "$RootDir/backend"
$ComputeDir = "$RootDir/compute-node"
$FrontendDir = "$RootDir/frontend"

function Run-Backend {
    Write-Host "`n--- Backend (pytest) ---" -ForegroundColor Cyan
    $pytestArgs = @()
    if ($Integration) {
        $pytestArgs += @("-m", "integration")
    } else {
        $pytestArgs += @("-m", "not integration")
    }
    if ($Coverage) {
        $pytestArgs += @("--cov=app", "--cov-report=term-missing")
    }
    python -m pytest $BackendDir/tests/ @pytestArgs
    if ($LASTEXITCODE -eq 0) { $script:Passed++ } else { $script:Failed++ }
}

function Run-Compute {
    Write-Host "`n--- Compute Node (cargo test) ---" -ForegroundColor Cyan
    cargo test --manifest-path $ComputeDir/Cargo.toml
    if ($LASTEXITCODE -eq 0) { $script:Passed++ } else { $script:Failed++ }
}

function Run-Frontend {
    Write-Host "`n--- Frontend (vitest) ---" -ForegroundColor Cyan
    if (-not (Test-Path "$FrontendDir/node_modules")) {
        Write-Host "  [SKIP] node_modules missing, run 'npm install' first"
        $script:Skipped++; return
    }
    npx --prefix $FrontendDir vitest run
    if ($LASTEXITCODE -eq 0) { $script:Passed++ } else { $script:Failed++ }
}

# ── Main ──
Write-Host "`n  === Rubbish Test Runner ===" -ForegroundColor Green

if ($Module -eq "all") { $targets = @("backend","compute-node","frontend") }
else { $targets = @($Module) }

foreach ($m in $targets) {
    switch ($m) {
        "backend"      { Run-Backend }
        "compute-node" { Run-Compute }
        "frontend"     { Run-Frontend }
    }
}

Write-Host "`n--- Results: $Passed passed, $Failed failed$(if($Skipped){", $Skipped skipped"}) ---`n"
exit $Failed
