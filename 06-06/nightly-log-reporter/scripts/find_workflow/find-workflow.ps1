# find-workflow.ps1
# Read parameters from config\finder.config.json, call GitHub API to find matching workflow Runs,
# output result to:
#   - console (human readable)
#   - <repo_root>\outputs\<MM-DD>\workflow-info.json (machine readable, for downstream steps)
#
# Relative path design: script is under scripts\find_workflow\, repo_root is 2 levels up.
param(
    [string]$Date,
    [string]$WorkflowUrl = "",
    [string]$ConfigPath = "",
    [string]$OutDir = ""
)

$ErrorActionPreference = "Stop"

# --- 路径定位 (相对脚本绝对路径) ---
$ScriptDir   = $null
if ($MyInvocation.MyCommand.Path) {
    $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
} else {
    $ScriptDir = (Get-Location).Path
}
$RepoRoot    = (Resolve-Path -LiteralPath (Join-Path $ScriptDir "..\..")).Path
if (-not $ConfigPath) {
    $ConfigPath = Join-Path $RepoRoot "config\finder.config.json"
}

# --- 读取配置 ---
if (-not (Test-Path $ConfigPath)) {
    throw "Config not found: $ConfigPath"
}
$cfg = Get-Content -LiteralPath $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json

# -WorkflowUrl 命令行参数覆盖配置文件 (run_all 调用多 target 时用)
if ($WorkflowUrl) {
    $cfg.workflow_url = $WorkflowUrl
}
$WorkflowUrl = $cfg.workflow_url
$Branch      = if ($cfg.PSObject.Properties['branch'])      { $cfg.branch }      else { "" }
$Event       = if ($cfg.PSObject.Properties['event'])       { $cfg.event }       else { "" }
$DateCfg     = if ($cfg.PSObject.Properties['date'])        { $cfg.date }        else { "" }
$StartDate   = if ($cfg.PSObject.Properties['start_date'])  { $cfg.start_date }  else { "" }
$EndDate     = if ($cfg.PSObject.Properties['end_date'])    { $cfg.end_date }    else { "" }
$MaxPages    = if ($cfg.PSObject.Properties['max_pages'])   { [int]$cfg.max_pages } else { 5 }

# 命令行 -Date 覆盖配置文件
if ($Date) { $DateCfg = $Date }

# 默认值: 今日
if (-not $DateCfg -and -not ($StartDate -and $EndDate)) {
    $DateCfg = (Get-Date).ToString("yyyy-MM-dd")
}

# 把 DateCfg (yyyy-MM-dd) 转成输出子目录用的 MM-dd
$MonthDay = if ($DateCfg) {
    $parsed = [DateTime]::ParseExact($DateCfg, "yyyy-MM-dd", $null)
    $parsed.ToString("MM-dd")
} else {
    (Get-Date).ToString("MM-dd")
}

# --- 工具函数 ---
. "$ScriptDir\utils\time-utils.ps1"

function Get-GitHubToken {
    # 相对路径优先: <repo_root>\local_data\github_token.txt
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

function Parse-WorkflowUrl {
    param([string]$Url)
    $pat = "https://github\.com/([^/]+)/([^/]+)/actions/workflows/([^/]+)"
    if ($Url -match $pat) {
        return @{ Owner = $matches[1]; Repo = $matches[2]; WorkflowId = $matches[3] }
    }
    throw "Invalid workflow URL: $Url"
}

function Find-Workflows {
    param(
        [string]$Owner, [string]$Repo, [string]$WorkflowId,
        [string]$Branch, [string]$Event,
        [DateTime]$UtcStart, [DateTime]$UtcEnd,
        [int]$MaxPages
    )
    $token = Get-GitHubToken
    $headers = @{
        "Authorization" = "token $token"
        "Accept"        = "application/vnd.github.v3+json"
        "User-Agent"    = "nightly-log-reporter"
    }
    $results = @()
    $page = 1
    while ($page -le $MaxPages) {
        $url = "https://api.github.com/repos/$Owner/$Repo/actions/workflows/$WorkflowId/runs?per_page=100&page=$page"
        try {
            $resp = Invoke-WebRequest -Uri $url -Headers $headers -UseBasicParsing -TimeoutSec 60
        } catch {
            throw "GitHub API call failed: $($_.Exception.Message)"
        }
        $data = $resp.Content | ConvertFrom-Json
        if (-not $data.workflow_runs -or $data.workflow_runs.Count -eq 0) { break }
        foreach ($run in $data.workflow_runs) {
            $created = [DateTime]$run.created_at
            if ($created -lt $UtcStart) { continue }
            if ($created -ge $UtcEnd)   { continue }
            if ($Branch -and $run.head_branch -ne $Branch) { continue }
            if ($Event  -and $run.event -ne $Event)        { continue }
            $local = $created.ToLocalTime()
            $results += [PSCustomObject]@{
                id           = [int64]$run.id
                url          = $run.html_url
                repo         = "$Owner/$Repo"
                owner        = $Owner
                repo_name    = $Repo
                workflow_id  = $WorkflowId
                branch       = $run.head_branch
                event        = $run.event
                status       = $run.status
                conclusion   = $run.conclusion
                utc_created  = $run.created_at
                local_created = $local.ToString("yyyy-MM-dd HH:mm:ss")
                local_date   = $local.Date.ToString("yyyy-MM-dd")
            }
        }
        if ($data.workflow_runs.Count -lt 100) { break }
        $page++
        Start-Sleep -Milliseconds 100
    }
    return $results
}

# --- 执行 ---
try {
    $parsed = Parse-WorkflowUrl $WorkflowUrl
    Write-Host "[finder] repo:    $($parsed.Owner)/$($parsed.Repo)"
    Write-Host "[finder] workflow:$($parsed.WorkflowId)"
    Write-Host "[finder] branch:  $Branch"
    Write-Host "[finder] event:   $Event"

    if ($DateCfg) {
        $range = Get-DateRangeUtc $DateCfg
        Write-Host "[finder] date:    $DateCfg"
        Write-Host "[finder] UTC:     $($range.Start.ToString('yyyy-MM-ddTHH:mm:ssZ')) ~ $($range.End.ToString('yyyy-MM-ddTHH:mm:ssZ'))"
        $runs = Find-Workflows -Owner $parsed.Owner -Repo $parsed.Repo -WorkflowId $parsed.WorkflowId `
                               -Branch $Branch -Event $Event -UtcStart $range.Start -UtcEnd $range.End -MaxPages $MaxPages
    } elseif ($StartDate -and $EndDate) {
        $range = Get-DateRangeUtcFromStartEnd $StartDate $EndDate
        Write-Host "[finder] range:   $StartDate ~ $EndDate"
        $runs = Find-Workflows -Owner $parsed.Owner -Repo $parsed.Repo -WorkflowId $parsed.WorkflowId `
                               -Branch $Branch -Event $Event -UtcStart $range.Start -UtcEnd $range.End -MaxPages $MaxPages
    } else {
        throw "Config must specify either date or start_date+end_date"
    }

    Write-Host "[finder] found:   $($runs.Count) run(s)"

    # 准备输出目录
    # -OutDir 指定时用调用方传的 (run_all 多 target 模式)
    # 否则用 outputs/<MM-DD> (单 target 模式)
    if (-not $outDir) {
        $outDir = Join-Path $RepoRoot "outputs\$MonthDay"
    }
    New-Item -ItemType Directory -Force -Path $outDir | Out-Null
    $infoPath = Join-Path $outDir "workflow-info.json"

    # JSON 输出 (用 @() 包裹确保空列表也是合法 JSON)
    $runsArray = @($runs)
    $payload = @{
        generated_at = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
        config       = @{
            workflow_url = $WorkflowUrl
            branch       = $Branch
            event        = $Event
            date         = $DateCfg
            start_date   = $StartDate
            end_date     = $EndDate
        }
        runs         = $runsArray
    }
    # Use [System.IO.File]::WriteAllText to avoid PowerShell 5.1 BOM on Out-File
    $json = $payload | ConvertTo-Json -Depth 6
    [System.IO.File]::WriteAllText($infoPath, $json, (New-Object System.Text.UTF8Encoding $false))
    Write-Host "[finder] saved:   $infoPath"

    if ($runsArray.Count -gt 0) {
        Write-Host ""
        Write-Host "=== Matching Runs ==="
        foreach ($r in $runsArray) {
            Write-Host ("  ID={0}  branch={1}  event={2}  conclusion={3}  local={4}" -f `
                $r.id, $r.branch, $r.event, $r.conclusion, $r.local_created)
        }
    } else {
        Write-Host "[finder] no runs matched the filter"
    }
}
catch {
    $msg = "[finder] ERROR: $_"
    Write-Host $msg
    # Write error to a marker file so the caller can detect failure
    $errPath = Join-Path $RepoRoot "logs\finder-last-error.txt"
    try { [System.IO.File]::WriteAllText($errPath, $msg, (New-Object System.Text.UTF8Encoding $false)) } catch { }
    return
}
