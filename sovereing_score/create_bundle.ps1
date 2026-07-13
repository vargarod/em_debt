# Manual Deployment Bundle Creator for Posit Connect
# This creates a zip file you can upload directly to Posit Connect

Write-Host "Creating deployment bundle for Posit Connect..." -ForegroundColor Cyan

# Create a temporary staging directory
$stagingDir = "C:\code\em_debt\deploy_bundle"
if (Test-Path $stagingDir) {
    Remove-Item -Recurse -Force $stagingDir
}
New-Item -ItemType Directory -Path $stagingDir | Out-Null

# Copy necessary files
Write-Host "Copying files..." -ForegroundColor Yellow
Copy-Item -Path "C:\code\em_debt\sovereing_score\*" -Destination "$stagingDir\" -Recurse
Copy-Item -Path "C:\code\em_debt\input" -Destination "$stagingDir\" -Recurse
Copy-Item -Path "C:\code\em_debt\requirements.txt" -Destination "$stagingDir\"
Copy-Item -Path "C:\code\em_debt\.python-version" -Destination "$stagingDir\"

# Create a zip file
$zipPath = "C:\code\em_debt\em_sovereign_app.zip"
if (Test-Path $zipPath) {
    Remove-Item $zipPath
}

Write-Host "Creating zip file..." -ForegroundColor Yellow
Compress-Archive -Path "$stagingDir\*" -DestinationPath $zipPath

# Cleanup
Remove-Item -Recurse -Force $stagingDir

Write-Host "`nDeployment bundle created: $zipPath" -ForegroundColor Green
Write-Host "`nTo deploy:" -ForegroundColor Cyan
Write-Host "1. Go to https://positconnect.prod.manulife.com/" -ForegroundColor White
Write-Host "2. Click 'Publish' button" -ForegroundColor White
Write-Host "3. Select 'Import from file'" -ForegroundColor White
Write-Host "4. Upload: $zipPath" -ForegroundColor White
Write-Host "5. Set content type: Streamlit" -ForegroundColor White
Write-Host "6. Set entry point: app.py" -ForegroundColor White
