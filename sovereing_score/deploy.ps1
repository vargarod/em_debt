# Deployment script for Posit Connect
# Based on official rsconnect-python documentation

# Configuration
$SERVER_URL = "https://positconnect.prod.manulife.com/"
$SERVER_NAME = "manulife-posit"
$APP_TITLE = "EM Sovereign Credit Spread Analysis"
$RSCONNECT_EXE = "c:/code/em_debt/.venv/Scripts/rsconnect.exe"

Write-Host "Installing rsconnect-python..." -ForegroundColor Cyan
& "c:/code/em_debt/.venv/Scripts/python.exe" -m pip install rsconnect-python --index-url https://artifactory.platform.manulife.io/artifactory/api/pypi/pypi/simple

Write-Host "`nConfiguring Posit Connect server..." -ForegroundColor Cyan
Write-Host "Please enter your Posit Connect API key:"
$API_KEY = Read-Host

# Add server (will update if already exists)
& $RSCONNECT_EXE add --server $SERVER_URL --name $SERVER_NAME --api-key $API_KEY

Write-Host "`nDeploying app to Posit Connect..." -ForegroundColor Cyan

# Prepare deployment: copy input folder into sovereing_score for deployment
Write-Host "Preparing deployment files..." -ForegroundColor Yellow
$inputSource = "c:\code\em_debt\input"
$inputDest = "c:\code\em_debt\sovereing_score\input"

# Copy input folder if it doesn't exist or is outdated
if (Test-Path $inputDest) {
    Remove-Item -Recurse -Force $inputDest
}
Copy-Item -Path $inputSource -Destination $inputDest -Recurse

# Update app.py path temporarily for deployment
Write-Host "Adjusting file paths for deployment..." -ForegroundColor Yellow

# Change to the app directory (where app.py is located)
Set-Location "c:\code\em_debt\sovereing_score"

# Deploy the current directory as a Streamlit app
Write-Host "Deploying Streamlit app..." -ForegroundColor Yellow
& $RSCONNECT_EXE deploy streamlit `
    --server $SERVER_NAME `
    --title $APP_TITLE `
    --entrypoint app.py `
    .

if ($LASTEXITCODE -eq 0) {
    Write-Host "`nDeployment successful!" -ForegroundColor Green
    Write-Host "Check your Posit Connect dashboard at: $SERVER_URL" -ForegroundColor Cyan
    Write-Host "`nNote: Input folder was copied to sovereing_score/input for deployment" -ForegroundColor Yellow
} else {
    Write-Host "`nDeployment failed with exit code: $LASTEXITCODE" -ForegroundColor Red
    Write-Host "`nTroubleshooting:" -ForegroundColor Yellow
    Write-Host "1. Check that requirements.txt exists in the app directory" -ForegroundColor White
    Write-Host "2. Verify .python-version file exists" -ForegroundColor White
    Write-Host "3. Make sure your API key has deployment permissions" -ForegroundColor White
    Write-Host "4. Try running with --verbose flag for more details" -ForegroundColor White
}

Write-Host "`nDeployment complete!" -ForegroundColor Green
Write-Host "Your app should be available at: $SERVER_URL" -ForegroundColor Green
