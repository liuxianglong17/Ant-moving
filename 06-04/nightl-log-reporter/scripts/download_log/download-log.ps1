# download-log.ps1
# Read config\downloader.config.json + outputs\<MM-DD>\workflow-info.json,
# download each matched run's job logs to outputs\<MM-DD>\<owner>-<repo>-<run_id>\.
# Supports multiple runs (e.g. multiple branches or triggers).
param(
    [string]$InfoPath,    # optional: explicit path to workflow-info.json; default uses today's outputs\<MM-DD>\workflow-info.json
    [string]$OutDir,      # optional: explicit output root; default uses outputs\<MM-DD>\
    [string]$Repo,        # optional: owner/repo override (e.g. "sgl-project/sglang")
    [string]$ConfigPath = ""  # optional: alternate config file path
)

$ErrorActionPreference = "Stop"

# --- 路径定位 (相对脚本绝对路径) ---
$ScriptDir  = $null
if ($MyInvocation.MyCommand.Path) {
    $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
} else {
    $ScriptDir = (Get-Location).Path
}
$RepoRoot   = (Resolve-Path -LiteralPath (Join-Path $ScriptDir "..\..")).Path
if (-not $ConfigPath) {
    $ConfigPath = Join-Path $RepoRoot "config\downloader.config.json"
}

# --- 默认值 ---
if (-not $InfoPath) {
    $InfoPath = Join-Path $RepoRoot ("outputs\{0}\workflow-info.json" -f (Get-Date).ToString("MM-dd"))
}
if (-not $OutDir) {
    $OutDir = Join-Path $RepoRoot ("outputs\{0}" -f (Get-Date).ToString("MM-dd"))
}

# --- 读取配置 ---
if (-not (Test-Path $ConfigPath)) { throw "Config not found: $ConfigPath" }
$cfg = Get-Content -LiteralPath $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json

# -Repo 命令行参数覆盖配置文件 (run_all 多 target 时用)
if ($Repo) {
    $cfg.repo = $Repo
}
$TimeoutSec = if ($cfg.PSObject.Properties['timeout_sec'])  { [int]$cfg.timeout_sec }  else { 300 }
$MaxRetries = if ($cfg.PSObject.Properties['max_retries']) { [int]$cfg.max_retries } else { 3 }

# --- 读 workflow-info.json ---
if (-not (Test-Path $InfoPath)) {
    throw "workflow-info.json not found: $InfoPath`n请先运行 scripts\find_workflow\find-workflow.ps1"
}
$info = Get-Content -LiteralPath $InfoPath -Raw -Encoding UTF8 | ConvertFrom-Json
$runs = @($info.runs)
if ($runs.Count -eq 0) {
    Write-Host "[downloader] workflow-info.json has no runs. exit."
    exit 0
}

# --- 工具函数 ---
function Get-GitHubToken {
    $paths = @(
        (Join-Path $RepoRoot "local_data\github_token.txt"),
        "D:\personal_code\My-agent-assistant\local_data\github_token.txt"
    )
    foreach ($p in $paths) {
        if (Test-Path $p) {
            $tk = (Get-Content $p -Raw).Trim()
            if ($tk) { return $tk }
        }
    }
    throw "GitHub token not found. Please put it in local_data\github_token.txt"
}

function Download-RunLogs {
    param(
        [string]$Owner, [string]$Repo, [string]$RunId,
        [string]$RunUrl, [string]$OutputDir,
        [hashtable]$Headers, [int]$TimeoutSec, [int]$MaxRetries
    )
    $apiBase = "https://api.github.com/repos/$Owner/$Repo"

    Write-Host "[downloader] run=$RunId url=$RunUrl"
    Write-Host "[downloader]   jobs:"

    # 拉取所有 jobs (分页)
    $jobs = @()
    $page = 1
    do {
        $jobsUrl = "$apiBase/actions/runs/$RunId/jobs?per_page=100&page=$page"
        $resp = Invoke-RestMethod -Uri $jobsUrl -Headers $Headers -Method Get
        $jobs += $resp.jobs
        $page++
    } while ($resp.jobs.Count -eq 100)

    Write-Host "[downloader]   total jobs: $($jobs.Count)"
    New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

    $ok = 0; $fail = 0
    foreach ($job in $jobs) {
        $jobName   = $job.name
        $jobFile   = ("$jobName.txt" -replace '[\\/:*?"<>|]', '_')
        $jobPath   = Join-Path $OutputDir $jobFile
        $status    = "$($job.status)/$($job.conclusion)"
        Write-Host "[downloader]   - $jobName ($status)"

        $attempt = 0; $success = $false
        while (-not $success -and $attempt -lt $MaxRetries) {
            $attempt++
            try {
                $logUrl    = "$apiBase/actions/jobs/$($job.id)/logs"
                $logResp   = Invoke-WebRequest -Uri $logUrl -Headers $Headers -Method Get `
                              -ErrorAction Stop -UseBasicParsing -TimeoutSec $TimeoutSec
                [System.IO.File]::WriteAllText($jobPath, $logResp.Content, [System.Text.Encoding]::UTF8)
                $size = [math]::Round((Get-Item $jobPath).Length / 1MB, 2)
                Write-Host "[downloader]     OK ($size MB)"
                $ok++; $success = $true
            } catch {
                $errMsg = $_.Exception.Message
                if ($attempt -ge $MaxRetries) {
                    Write-Host "[downloader]     FAIL: $errMsg"
                    $fail++
                } else {
                    Write-Host "[downloader]     retry ${attempt}/${MaxRetries}: $errMsg"
                    Start-Sleep -Seconds 5
                }
            }
        }
        Start-Sleep -Milliseconds 300
    }

    return @{ total = $jobs.Count; ok = $ok; fail = $fail }
}

# --- 主流程 ---
try {
    $token = Get-GitHubToken
    $headers = @{
        "Authorization" = "token $token"
        "Accept"        = "application/vnd.github.v3+json"
        "User-Agent"    = "nightl-log-reporter"
    }

    New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
    $summaryAll = @()
    $totalDl = 0; $totalFail = 0; $totalRuns = 0

    foreach ($run in $runs) {
        $totalRuns++
        $owner  = $run.owner
        $repo   = $run.repo_name
        $runId  = $run.id
        $runUrl = $run.url
        $runDir = Join-Path $OutDir ("{0}-{1}-{2}" -f $owner, $repo, $runId)

        $r = Download-RunLogs -Owner $owner -Repo $repo -RunId $runId -RunUrl $runUrl `
                              -OutputDir $runDir -Headers $headers `
                              -TimeoutSec $TimeoutSec -MaxRetries $MaxRetries

        $summaryAll += @{
            run_id    = $runId
            run_url   = $runUrl
            branch    = $run.branch
            event     = $run.event
            local_created = $run.local_created
            total_jobs = $r.total
            downloaded = $r.ok
            failed     = $r.fail
            output_dir = $runDir
        }
        $totalDl   += $r.ok
        $totalFail += $r.fail
    }

    $summaryPath = Join-Path $OutDir "download-summary.json"
    $summary = @{
        repo           = "$($cfg.repo)"
        downloaded_at  = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
        total_runs     = $totalRuns
        total_downloaded = $totalDl
        total_failed   = $totalFail
        runs           = $summaryAll
    }
    $json = $summary | ConvertTo-Json -Depth 6
    [System.IO.File]::WriteAllText($summaryPath, $json, (New-Object System.Text.UTF8Encoding $false))

    Write-Host ""
    Write-Host "========================================"
    Write-Host "[downloader] DONE"
    Write-Host "[downloader] runs:     $totalRuns"
    Write-Host "[downloader] downloaded:$totalDl"
    Write-Host "[downloader] failed:   $totalFail"
    Write-Host "[downloader] output:   $OutDir"
    Write-Host "[downloader] summary:  $summaryPath"
    Write-Host "========================================"
}
catch {
    $msg = "[downloader] ERROR: $_"
    Write-Host $msg
    $errPath = Join-Path $RepoRoot "logs\downloader-last-error.txt"
    try { [System.IO.File]::WriteAllText($errPath, $msg, (New-Object System.Text.UTF8Encoding $false)) } catch { }
    return
}
