# Daily Sovereign Ratings Data Update Script
# This script fetches current sovereign ratings from Bloomberg and uploads to PostgreSQL
# Designed to run via Windows Task Scheduler

# Configuration
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonExe = "c:\code\em_debt\.venv\Scripts\python.exe"
$LogDir = Join-Path $ScriptDir "logs"
$LogFile = Join-Path $LogDir "daily_update_$(Get-Date -Format 'yyyyMMdd').log"

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
Write-Log "Starting daily sovereign ratings update"
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
    
    # Step 1: Fetch sovereign ratings data from Bloomberg
    Write-Log "=========================================="
    Write-Log "Step 1: Fetching data from Bloomberg..."
    Write-Log "=========================================="
    
    $FetchOutput = & $PythonExe fetch_sovereign_ratings.py 2>&1 | Out-String
    $FetchExitCode = $LASTEXITCODE
    
    # Log the output
    $FetchOutput -split "`n" | ForEach-Object { 
        if ($_.Trim()) { Write-Log $_ }
    }
    
    # Check for errors in output
    if ($FetchExitCode -ne 0 -or $FetchOutput -match "ERROR|Error occurred|Traceback") {
        throw "Bloomberg data fetch failed - check logs for details"
    }
    Write-Log "Bloomberg data fetch completed successfully"
    
    # Step 2: Upload data to PostgreSQL
    Write-Log "=========================================="
    Write-Log "Step 2: Uploading to PostgreSQL..."
    Write-Log "=========================================="
    
    $UploadOutput = & $PythonExe upload_to_postgres.py 2>&1 | Out-String
    $UploadExitCode = $LASTEXITCODE
    
    # Log the output
    $UploadOutput -split "`n" | ForEach-Object { 
        if ($_.Trim()) { Write-Log $_ }
    }
    
    # Check for errors in output
    if ($UploadExitCode -ne 0 -or $UploadOutput -match "ERROR|Error occurred|Traceback") {
        throw "PostgreSQL upload failed - check logs for details"
    }
    Write-Log "PostgreSQL upload completed successfully"
    
    # Success
    Write-Log "=========================================="
    Write-Log "Daily update completed successfully!"
    Write-Log "=========================================="
    exit 0
    
} catch {
    # Error handling
    Write-Log "=========================================="
    Write-Log "ERROR: $($_.Exception.Message)"
    Write-Log "=========================================="
    
    # Send email notification (optional - configure if needed)
    # Send-MailMessage -To "your-email@example.com" -From "scheduler@example.com" `
    #     -Subject "Sovereign Ratings Update Failed" -Body "Error: $($_.Exception.Message)" `
    #     -SmtpServer "your-smtp-server.com"
    
    exit 1
} finally {
    Write-Log "Script execution completed at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
}
