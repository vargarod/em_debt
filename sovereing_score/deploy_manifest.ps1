# Two-step deployment: Create manifest, then deploy
# Based on rsconnect-python best practices

$RSCONNECT_EXE = "c:/code/em_debt/.venv/Scripts/rsconnect.exe"
$SERVER_NAME = "manulife-posit"
$APP_TITLE = "EM Sovereign Credit Spread Analysis"

Write-Host "Preparing deployment..." -ForegroundColor Cyan

# Prepare deployment: copy input folder into sovereing_score
Write-Host "Copying input files..." -ForegroundColor Yellow
$inputSource = "c:\code\em_debt\input"
$inputDest = "c:\code\em_debt\sovereing_score\input"

if (Test-Path $inputDest) {
    Remove-Item -Recurse -Force $inputDest
}
Copy-Item -Path $inputSource -Destination $inputDest -Recurse

Set-Location "c:\code\em_debt\sovereing_score"

# Remove any existing manifest
if (Test-Path "manifest.json") {
    Write-Host "Removing old manifest.json..." -ForegroundColor Yellow
    Remove-Item "manifest.json"
}

# Step 1: Write manifest
Write-Host "`nStep 1: Creating deployment manifest..." -ForegroundColor Cyan
& $RSCONNECT_EXE write-manifest streamlit . `
    --overwrite `
    --entrypoint app.py `
    --verbose

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to create manifest" -ForegroundColor Red
    exit 1
}

Write-Host "Manifest created successfully!" -ForegroundColor Green

# Step 2: Deploy the manifest
Write-Host "`nStep 2: Deploying manifest to Posit Connect..." -ForegroundColor Cyan
& $RSCONNECT_EXE deploy manifest . `
    --server $SERVER_NAME `
    --title $APP_TITLE `
    --verbose

if ($LASTEXITCODE -eq 0) {
    Write-Host "`nDeployment successful!" -ForegroundColor Green
    Write-Host "Check your Posit Connect dashboard at: https://positconnect.prod.manulife.com/" -ForegroundColor Cyan
} else {
    Write-Host "`nDeployment failed. Exit code: $LASTEXITCODE" -ForegroundColor Red
    Write-Host "`nThe manifest.json file was created. You can try:" -ForegroundColor Yellow
    Write-Host "1. Manually uploading it via Posit Connect UI" -ForegroundColor White
    Write-Host "2. Sharing it with your Posit Connect admin for troubleshooting" -ForegroundColor White
    Write-Host "3. Check if your account has deployment permissions" -ForegroundColor White
}
