# Deploy via Git to Posit Connect

Write-Host "Setting up Git repository for deployment..." -ForegroundColor Cyan

# Check if git is available
try {
    git --version | Out-Null
} catch {
    Write-Host "Git is not installed or not in PATH. Please install Git first." -ForegroundColor Red
    exit 1
}

# Navigate to em_debt directory
Set-Location "C:\code\em_debt"

# Check if already a git repo
if (-not (Test-Path ".git")) {
    Write-Host "Initializing Git repository..." -ForegroundColor Yellow
    git init
    
    # Create .gitignore if it doesn't exist
    if (-not (Test-Path ".gitignore")) {
        @"
.venv/
__pycache__/
*.pyc
.python-version
.DS_Store
*.log
.env
deploy_bundle/
em_sovereign_app.zip
"@ | Out-File -FilePath ".gitignore" -Encoding utf8
    }
    
    git add .
    git commit -m "Initial commit - EM Sovereign App"
}

Write-Host "`nGit repository ready!" -ForegroundColor Green
Write-Host "`nNext steps:" -ForegroundColor Cyan
Write-Host "1. Push this repo to a Git service (GitHub, GitLab, Bitbucket, etc.)" -ForegroundColor White
Write-Host "2. In Posit Connect, select 'Import from Git'" -ForegroundColor White
Write-Host "3. Enter your Git repository URL" -ForegroundColor White
Write-Host "4. Select branch: main (or master)" -ForegroundColor White
Write-Host "5. Set entry point: sovereing_score/app.py" -ForegroundColor White
Write-Host "6. Content type: Streamlit" -ForegroundColor White
