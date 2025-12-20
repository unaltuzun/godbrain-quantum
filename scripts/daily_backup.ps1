# GODBRAIN Daily Backup Script
# Runs daily to push all changes to GitHub

$ErrorActionPreference = "Continue"
$LogFile = "C:\Users\zzkid\godbrain-quantum\logs\daily_backup.log"

function Write-Log {
    param($Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$timestamp - $Message" | Out-File -Append -FilePath $LogFile
    Write-Host "$timestamp - $Message"
}

Set-Location "C:\Users\zzkid\godbrain-quantum"

Write-Log "=== GODBRAIN Daily Backup Started ==="

# Stage all changes
git add -A
$status = git status --porcelain

if ($status) {
    Write-Log "Changes detected, committing..."
    
    # Create commit message with timestamp
    $date = Get-Date -Format "yyyy-MM-dd HH:mm"
    $commitMsg = "Auto-backup: $date - Wisdom + Anomalies"
    
    git commit -m $commitMsg 2>&1 | Out-Null
    
    # Push to GitHub
    Write-Log "Pushing to GitHub..."
    $pushResult = git push origin main 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Log "SUCCESS: Changes pushed to GitHub"
    }
    else {
        Write-Log "ERROR: Push failed - $pushResult"
    }
}
else {
    Write-Log "No changes to commit"
}

Write-Log "=== Backup Complete ==="
