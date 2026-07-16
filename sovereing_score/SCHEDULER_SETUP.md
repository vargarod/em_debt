# Daily Sovereign Ratings Update - Scheduling Instructions

## Overview
This folder contains scripts to automatically fetch sovereign ratings from Bloomberg and upload to PostgreSQL database.

## Files Created
- **run_daily_update.ps1** - PowerShell script (recommended)
- **run_daily_update.bat** - Batch file alternative (simpler)
- **SCHEDULER_SETUP.md** - This file

## Option 1: Windows Task Scheduler Setup (Recommended)

### Using PowerShell Script:

1. **Open Task Scheduler**
   - Press `Win + R`, type `taskschd.msc`, press Enter

2. **Create a New Task**
   - Click "Create Task" (not "Create Basic Task")
   - Name: "Sovereign Ratings Daily Update"
   - Description: "Fetch Bloomberg sovereign ratings and upload to PostgreSQL"
   - Select "Run whether user is logged on or not"
   - Check "Run with highest privileges"

3. **Triggers Tab**
   - Click "New..."
   - Begin the task: "On a schedule"
   - Settings: Daily
   - Start: Choose your preferred time (e.g., 6:00 PM daily after market close)
   - Recur every: 1 days
   - Enabled: Checked
   - Click "OK"

4. **Actions Tab**
   - Click "New..."
   - Action: "Start a program"
   - Program/script: `powershell.exe`
   - Add arguments: `-ExecutionPolicy Bypass -File "c:\code\em_debt\sovereing_score\run_daily_update.ps1"`
   - Start in: `c:\code\em_debt\sovereing_score`
   - Click "OK"

5. **Conditions Tab** (Optional)
   - Uncheck "Start the task only if the computer is on AC power" (if laptop)
   - Check "Wake the computer to run this task" (if you want it to run even when sleeping)

6. **Settings Tab**
   - Check "Allow task to be run on demand"
   - Check "Run task as soon as possible after a scheduled start is missed"
   - If the task fails, restart every: 10 minutes
   - Attempt to restart up to: 3 times
   - Click "OK"

7. **Enter Credentials**
   - When prompted, enter your Windows username and password
   - This allows the task to run even when you're not logged in

### Using Batch File (Alternative):

Follow the same steps above, but in step 4 use:
- Program/script: `c:\code\em_debt\sovereing_score\run_daily_update.bat`
- Add arguments: (leave empty)
- Start in: `c:\code\em_debt\sovereing_score`

## Option 2: Manual Testing

Before scheduling, test the scripts manually:

### PowerShell:
```powershell
cd c:\code\em_debt\sovereing_score
.\run_daily_update.ps1
```

### Batch File:
```cmd
cd c:\code\em_debt\sovereing_score
run_daily_update.bat
```

## Logs

The PowerShell script creates daily logs in:
- `c:\code\em_debt\sovereing_score\logs\daily_update_YYYYMMDD.log`

Review these logs to verify successful execution or troubleshoot issues.

## Recommended Schedule

**Daily at 6:00 PM ET** - After market close
- Ensures latest Bloomberg data is captured
- Database updated for next day viewing
- Streamlit app shows current data

**Alternative: Monthly (Month-End)**
If you only want month-end data:
- Schedule on last day of month
- Modify trigger: "Monthly" → "Last day"

## Security Considerations

⚠️ **IMPORTANT**: The scripts contain the database password in plain text.

**To improve security:**

1. **Use Environment Variables (Recommended)**
   - Set `DB_PASSWORD` as a system environment variable
   - Remove password from script
   
2. **Use Windows Credential Manager**
   ```powershell
   # Store password securely
   $cred = Get-Credential
   $cred.Password | ConvertFrom-SecureString | Set-Content "c:\code\em_debt\sovereing_score\.dbpass.txt"
   
   # Then modify script to read:
   $SecurePassword = Get-Content "c:\code\em_debt\sovereing_score\.dbpass.txt" | ConvertTo-SecureString
   $BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecurePassword)
   $env:DB_PASSWORD = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
   ```

3. **Restrict File Permissions**
   - Right-click script files → Properties → Security
   - Remove access for other users
   - Keep only your account with full control

## Troubleshooting

### Script doesn't run
- Check Task Scheduler history (enable if disabled)
- Verify virtual environment path is correct
- Ensure Bloomberg Terminal is running
- Check database connectivity

### Missing data
- Review logs in `sovereing_score\logs\`
- Manually run script to see errors
- Verify Bloomberg Terminal is logged in

### Email Notifications (Optional)

To enable email alerts on failures, uncomment and configure the email section in `run_daily_update.ps1`:

```powershell
Send-MailMessage -To "your-email@example.com" `
    -From "scheduler@example.com" `
    -Subject "Sovereign Ratings Update Failed" `
    -Body "Error: $($_.Exception.Message)" `
    -SmtpServer "your-smtp-server.com"
```

## Monitoring

Check the Streamlit app regularly:
- URL: http://localhost:8501
- Verify "Data as of" date in sidebar matches current date
- Ensure data looks reasonable

## Additional Notes

- Script runs from: `c:\code\em_debt\sovereing_score\`
- Virtual environment: `c:\code\em_debt\.venv`
- Output Excel: `sovereing_score\input\sovereign_ratings_output.xlsx`
- Database: Azure PostgreSQL `securitized_research.emd_sovereign_score`
