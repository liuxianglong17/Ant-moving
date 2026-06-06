@echo off
REM One-click runner for nightly-log-reporter.
REM Uses Bypass policy to call powershell, avoiding ExecutionPolicy block.
REM Also ensures run_all.ps1 has a UTF-8 BOM (on Chinese Windows, PS5.1 reads
REM no-BOM ps1 files in GBK by default, which breaks scripts with Chinese comments).
setlocal
cd /d "%~dp0"

REM --- BOM self-heal: if run_all.ps1 lacks UTF-8 BOM, add it before invoking ---
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$p = Join-Path (Get-Location).Path 'run_all.ps1';" ^
    "$b = [System.IO.File]::ReadAllBytes($p);" ^
    "$hasBom = $b.Length -ge 3 -and $b[0] -eq 0xEF -and $b[1] -eq 0xBB -and $b[2] -eq 0xBF;" ^
    "if (-not $hasBom) { $n = New-Object byte[] ($b.Length + 3); $n[0]=0xEF; $n[1]=0xBB; $n[2]=0xBF; [Array]::Copy($b, 0, $n, 3, $b.Length); [System.IO.File]::WriteAllBytes($p, $n); Write-Host '[run_all.bat] added UTF-8 BOM to run_all.ps1' }" >nul 2>&1

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_all.ps1" %*
set RC=%ERRORLEVEL%
echo.
echo [run_all.bat] exit code = %RC%
endlocal & exit /b %RC%
