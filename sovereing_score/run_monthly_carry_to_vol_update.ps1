# Monthly Carry-to-Volatility Data Update Script
# This script computes carry-to-vol metrics from historical sovereign data and uploads to PostgreSQL
# Designed to run monthly via Windows Task Scheduler (e.g., first day of each month)

# Configuration
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonExe = "c:\code\em_debt\.venv\Scripts\python.exe"
$LogDir = Join-Path $ScriptDir "logs"
$LogFile = Join-Path $LogDir "monthly_carry_to_vol_$(Get-Date -Format 'yyyyMMdd').log"

# Create logs directory if it doesn't exist
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir | Out-Null
}

# Function to write log messages
function Write-Log {
    param([string]$Message)
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogMessage = "[$Timestamp] $Message"
    Write-Host $LogMessage
    Add-Content -Path $LogFile -Value $LogMessage
}

# Start logging
Write-Log "=========================================="
Write-Log "Starting monthly carry-to-vol update"
Write-Log "=========================================="

# Set console encoding to UTF-8 to handle Python script output
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"
Write-Log "Console encoding set to UTF-8"

# Set database password environment variable
$env:DB_PASSWORD = "K8#TqL5Z!sA9"
Write-Log "Database password environment variable set"

# Change to script directory
Set-Location $ScriptDir
Write-Log "Working directory: $ScriptDir"

try {
    # Check virtual environment Python exists
    if (-not (Test-Path $PythonExe)) {
        throw "Python executable not found at: $PythonExe"
    }
    Write-Log "Using Python: $PythonExe"
    
    # ===========================================================
    # STEP 1: Compute carry-to-volatility metrics
    # ===========================================================
    Write-Log ""
    Write-Log "STEP 1: Computing carry-to-volatility metrics..."
    Write-Log "Script: compute_carry_to_vol_v2.py"
    
    $ComputeScript = Join-Path $ScriptDir "compute_carry_to_vol_v2.py"
    if (-not (Test-Path $ComputeScript)) {
        throw "Compute script not found: $ComputeScript"
    }
    
    Write-Log "Executing: $PythonExe $ComputeScript"
    & $PythonExe $ComputeScript 2>&1 | ForEach-Object {
        Write-Log "  $_"
    }
    
    if ($LASTEXITCODE -ne 0) {
        throw "Compute script failed with exit code: $LASTEXITCODE"
    }
    
    Write-Log "✓ Carry-to-vol computation completed successfully"
    
    # ===========================================================
    # STEP 2: Upload metrics to PostgreSQL
    # ===========================================================
    Write-Log ""
    Write-Log "STEP 2: Uploading carry-to-vol metrics to database..."
    Write-Log "Script: upload_carry_to_vol.py"
    
    $UploadScript = Join-Path $ScriptDir "upload_carry_to_vol.py"
    if (-not (Test-Path $UploadScript)) {
        throw "Upload script not found: $UploadScript"
    }
    
    Write-Log "Executing: $PythonExe $UploadScript"
    & $PythonExe $UploadScript 2>&1 | ForEach-Object {
        Write-Log "  $_"
    }
    
    if ($LASTEXITCODE -ne 0) {
        throw "Upload script failed with exit code: $LASTEXITCODE"
    }
    
    Write-Log "✓ Database upload completed successfully"
    
    # ===========================================================
    # SUCCESS
    # ===========================================================
    Write-Log ""
    Write-Log "=========================================="
    Write-Log "Monthly carry-to-vol update completed successfully!"
    Write-Log "=========================================="
    exit 0
    
} catch {
    Write-Log ""
    Write-Log "=========================================="
    Write-Log "ERROR: Monthly carry-to-vol update failed!"
    Write-Log "Error message: $($_.Exception.Message)"
    Write-Log "=========================================="
    exit 1
}
