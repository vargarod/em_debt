# Monthly Carry-to-Volatility Data Update Script - PREVIOUS MONTH-END
# This script computes carry-to-vol metrics and uploads for the PREVIOUS MONTH-END
# Designed to run 3-4 days after month-end (e.g., on the 3rd or 4th of the month)
# Automatically calculates previous month-end date (e.g., if run on July 3, uses June 30)

# Configuration
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonExe = "c:\code\em_debt\.venv\Scripts\python.exe"
$LogDir = Join-Path $ScriptDir "logs"
$LogFile = Join-Path $LogDir "monthly_carry_prev_month_$(Get-Date -Format 'yyyyMMdd').log"

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
Write-Log "Monthly carry-to-vol update (PREVIOUS MONTH-END)"
Write-Log "=========================================="

# Calculate previous month-end date for logging
$Today = Get-Date
$FirstOfMonth = Get-Date -Year $Today.Year -Month $Today.Month -Day 1
$PrevMonthEnd = $FirstOfMonth.AddDays(-1)
Write-Log "Today: $($Today.ToString('yyyy-MM-dd'))"
Write-Log "Target as-of date: $($PrevMonthEnd.ToString('yyyy-MM-dd')) (previous month-end)"

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
    # STEP 2: Upload metrics to PostgreSQL (PREVIOUS MONTH-END)
    # ===========================================================
    Write-Log ""
    Write-Log "STEP 2: Uploading carry-to-vol metrics for previous month-end..."
    Write-Log "Script: upload_carry_to_vol_prev_month.py"
    
    $UploadScript = Join-Path $ScriptDir "upload_carry_to_vol_prev_month.py"
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
    Write-Log "Data uploaded for: $($PrevMonthEnd.ToString('yyyy-MM-dd'))"
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
