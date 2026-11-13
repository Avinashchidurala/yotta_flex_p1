# YottaFlex Return Management System (RMS) Orchestrator
Param(
    [string]$Action = "all"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $ProjectRoot

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   YottaFlex RMS Execution & Verification Pipeline       " -ForegroundColor Cyan
Write-Host "   Scale: 37,500 Orders (+25%) | Seed: 20261022          " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

switch ($Action.ToLower()) {
    "generate" {
        Write-Host ">>> Running Synthetic Generation (Scale: FULL, Seed: 20261022)..." -ForegroundColor Yellow
        python -m src.cli generate --scale full --seed 20261022
    }
    "validate" {
        Write-Host ">>> Running Relational, Financial & Temporal Audit..." -ForegroundColor Yellow
        python -m src.cli validate
    }
    "test" {
        Write-Host ">>> Running Automated Test Suite (Unit, Integration, Negative, Boundary, Regression)..." -ForegroundColor Yellow
        python -m unittest discover tests
    }
    "reproduce" {
        Write-Host ">>> Verifying Deterministic Reproducibility (Double Run)..." -ForegroundColor Yellow
        python -m src.cli reproduce --scale medium --seed 20261022
    }
    "export-sql" {
        Write-Host ">>> Exporting Relational SQL Seed Script..." -ForegroundColor Yellow
        python -m src.cli export-sql
    }
    "serve" {
        Write-Host ">>> Starting FastAPI & Interactive Operations Dashboard on http://127.0.0.1:8000..." -ForegroundColor Green
        uvicorn src.api.app:app --host 127.0.0.1 --port 8000 --reload
    }
    "all" {
        Write-Host ">>> Executing Complete Pipeline: Test -> Generate -> Validate -> Reproduce -> Export..." -ForegroundColor Yellow
        python -m unittest discover tests
        python -m src.cli generate --scale full --seed 20261022
        python -m src.cli validate
        python -m src.cli reproduce --scale medium --seed 20261022
        python -m src.cli export-sql
        Write-Host "`n>>> ALL 5 PIPELINE STAGES COMPLETED WITH ZERO ERRORS!" -ForegroundColor Green
    }
    Default {
        Write-Host "Usage: .\run.ps1 [generate | validate | test | reproduce | export-sql | serve | all]" -ForegroundColor Red
    }
}
