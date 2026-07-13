# Git-backed deployment setup script
# Based on Posit Connect Git-backed content documentation

Write-Host "Setting up Git-backed deployment..." -ForegroundColor Cyan

# Navigate to the app directory
Set-Location "c:\code\em_debt\sovereing_score"

# Check if git is available
try {
    git --version | Out-Null
} catch {
    Write-Host "ERROR: Git is not installed or not in PATH." -ForegroundColor Red
    Write-Host "Please install Git from: https://git-scm.com/downloads" -ForegroundColor Yellow
    exit 1
}

# Check if already a git repo
if (-not (Test-Path ".git")) {
    Write-Host "Initializing Git repository..." -ForegroundColor Yellow
    git init
    
    # Create .gitignore
    @"
__pycache__/
*.pyc
*.pyo
.DS_Store
*.log
.env
.venv/
venv/
deploy_bundle/
*.zip
"@ | Out-File -FilePath ".gitignore" -Encoding utf8
    
    Write-Host "Git repository initialized!" -ForegroundColor Green
}

# Add all files including manifest.json
Write-Host "`nAdding files to Git..." -ForegroundColor Yellow
git add .
git add manifest.json
git add requirements.txt
git add .python-version
git add input/

# Commit
Write-Host "Committing files..." -ForegroundColor Yellow
git commit -m "Add manifest.json and EM Sovereign App for Posit Connect deployment"

Write-Host "`nGit repository ready!" -ForegroundColor Green
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "NEXT STEPS:" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Push this repository to a Git service:" -ForegroundColor White
Write-Host "   - GitHub: https://github.com" -ForegroundColor Gray
Write-Host "   - GitLab: https://gitlab.com" -ForegroundColor Gray
Write-Host "   - Bitbucket: https://bitbucket.org" -ForegroundColor Gray
Write-Host "   - Or your organization's Git server" -ForegroundColor Gray
Write-Host ""
Write-Host "2. In Posit Connect:" -ForegroundColor White
Write-Host "   a. Go to: https://positconnect.prod.manulife.com/" -ForegroundColor Gray
Write-Host "   b. Click 'Publish' > 'Import from Git'" -ForegroundColor Gray
Write-Host "   c. Enter your Git repository URL (https://...)" -ForegroundColor Gray
Write-Host "   d. Select branch: main (or master)" -ForegroundColor Gray
Write-Host "   e. Select target directory: . (root/current directory)" -ForegroundColor Gray
Write-Host "   f. Content type: will be auto-detected as Streamlit" -ForegroundColor Gray
Write-Host "   g. Click 'Deploy Content'" -ForegroundColor Gray
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Example Git commands to push to GitHub:" -ForegroundColor Yellow
Write-Host "  git remote add origin https://github.com/YOUR_USERNAME/em-sovereign-app.git" -ForegroundColor Gray
Write-Host "  git branch -M main" -ForegroundColor Gray
Write-Host "  git push -u origin main" -ForegroundColor Gray
