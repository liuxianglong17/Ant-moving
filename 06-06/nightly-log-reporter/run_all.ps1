<#
run_all.ps1
一键流程: 找 workflow -> 下载日志 -> 分析 -> 错误分类.
所有路径相对脚本所在目录, 可整体复制到任意位置后直接执行.

可接受参数:
  -Date MM-DD   指定 outputs 子目录 (默认今日)
  -SkipFind    跳过 find-workflow, 直接用已有 workflow-info.json
  -SkipDownload 跳过 download
  -SkipAnalyze 跳过 analyze + classify
  -SkipSummary 跳过合并简报
  -PythonPath  指定 python 解释器 (默认自动找系统 python)

执行方式 (任选其一):
  1) 双击或命令行:  .\run_all.bat
     (推荐: 内部用 -ExecutionPolicy Bypass 调此脚本, 避开 RemoteSigned 拦截)
  2) 绕过 policy:   powershell -NoProfile -ExecutionPolicy Bypass -File .\run_all.ps1
  3) 直接:          .\run_all.ps1
     (仅在当前 session 的 ExecutionPolicy = Bypass / Unrestricted 时可用)

多 target 模式:
  -Target <name>    只跑 config\targets.config.json 里指定 name 的那个 target.
                    不传 = 跑所有 targets (顺序执行).
  -TargetsConfig <path>
                    指定 targets 配置文件 (默认 config\targets.config.json).
  outputs 子目录: outputs\<MM-DD>\<target_name>\...
#>
param(
    [string]$Date = "",
    [switch]$SkipFind = $false,
    [switch]$SkipDownload = $false,
    [switch]$SkipAnalyze = $false,
    [switch]$SkipSummary = $false,
    [string]$PythonPath = "",
    [string]$Target = "",
    [string]$TargetsConfig = ""
)

$ErrorActionPreference = "Stop"
$ProgressPreference    = "SilentlyContinue"

# --- 路径定位 (相对脚本) ---
$ScriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot   = (Resolve-Path $ScriptDir).Path
$LogDir     = Join-Path $RepoRoot "logs"
$LogFile    = Join-Path $LogDir ("run-{0}.log" -f (Get-Date).ToString("yyyyMMdd-HHmmss"))
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

# 所有输出同时落到屏幕和日志文件 (屏幕给交互, 文件给事后查看)
function Write-Both {
    param([string]$Line)
    Write-Host $Line
    Add-Content -LiteralPath $LogFile -Value $Line -Encoding UTF8
}
$FinderPs1  = Join-Path $RepoRoot "scripts\find_workflow\find-workflow.ps1"
$DownloaderPs1 = Join-Path $RepoRoot "scripts\download_log\download-log.ps1"
$AnalyzerPy   = Join-Path $RepoRoot "scripts\analyze\analyze-log.py"
$ClassifierPy = Join-Path $RepoRoot "scripts\analyze\classify-errors.py"
$SummaryPy    = Join-Path $RepoRoot "scripts\summary\build_summary.py"

# --- UTF-8 BOM workaround ---
# PowerShell 5.1 默认以本地代码页(中文 Windows = GBK) 解析 .ps1, 文件若含中文且无 BOM 会失败.
# 给所有 .ps1 加上 UTF-8 BOM (幂等: 已存在则跳过).
function Ensure-Utf8Bom {
    param([string]$Path)
    if (-not (Test-Path $Path)) { return }
    $bytes = [System.IO.File]::ReadAllBytes($Path)
    if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
        return
    }
    $new = New-Object byte[] ($bytes.Length + 3)
    $new[0] = 0xEF; $new[1] = 0xBB; $new[2] = 0xBF
    [Array]::Copy($bytes, 0, $new, 3, $bytes.Length)
    [System.IO.File]::WriteAllBytes($Path, $new)
}

foreach ($p in @($FinderPs1, $DownloaderPs1, (Join-Path $RepoRoot "scripts\find_workflow\utils\time-utils.ps1"))) {
    Ensure-Utf8Bom -Path $p
}

# --- python 解释器 ---
function Resolve-Python {
    param([string]$Provided)
    if ($Provided -and (Test-Path $Provided)) { return $Provided }
    $candidates = @(
        "python", "python3", "py",
        "$env:LOCALAPPDATA\Programs\Python\Python314\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "C:\Python314\python.exe", "C:\Python313\python.exe", "C:\Python312\python.exe"
    )
    foreach ($c in $candidates) {
        try {
            $r = & $c -c "import sys; print(sys.executable)" 2>$null
            if ($r) { return $c }
        } catch { }
    }
    throw "Python not found. 请安装 Python 或通过 -PythonPath 指定"
}

$python = Resolve-Python -Provided $PythonPath
Write-Both "[run_all] repo_root: $RepoRoot"
Write-Both "[run_all] python:    $python"
Write-Both "[run_all] date:      $(if ($Date) { $Date } else { (Get-Date).ToString('MM-dd') })"
Write-Both "[run_all] log:       $LogFile"
Write-Both "[run_all] =========================================="

$stepNo = 0
function Step($name) {
    $script:stepNo++
    Write-Both ""
    Write-Both "[run_all] ---- Step $stepNo : $name ----"
}

# --- 决定本次跑哪些 target ---
# 优先: -Target 指定的单个
# 否则: -TargetsConfig 文件中的所有 (顺序)
# 都没有: 退化为单 target 模式, 从 config\finder.config.json 读, target name 固定为 "default"
$runDate = if ($Date) { $Date } else { (Get-Date).ToString('MM-dd') }

$TargetsList = @()  # array of hashtables: {name, finder_cfg_path, downloader_cfg_path, out_dir, finder_args, downloader_args}

if ($Target -or $TargetsConfig) {
    # 显式传了 -Target / -TargetsConfig, 走多 target 模式
    $targetsCfgPath = if ($TargetsConfig) { $TargetsConfig } else { Join-Path $RepoRoot "config\targets.config.json" }
} elseif (Test-Path (Join-Path $RepoRoot "config\targets.config.json")) {
    # 默认: 若 config\targets.config.json 存在, 自动按多 target 跑
    $targetsCfgPath = Join-Path $RepoRoot "config\targets.config.json"
} else {
    # 没有多 target 配置才回退到单 target 模式
    $targetsCfgPath = ""
}

if ($targetsCfgPath) {
    # 多 target 模式
    if (-not (Test-Path $targetsCfgPath)) {
        throw "targets config not found: $targetsCfgPath"
    }
    $targetsCfg = Get-Content -LiteralPath $targetsCfgPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $allTargets = @($targetsCfg.targets)
    if ($allTargets.Count -eq 0) { throw "targets config has no targets" }

    $chosen = $allTargets
    if ($Target) {
        $chosen = @($allTargets | Where-Object { $_.name -eq $Target })
        if ($chosen.Count -eq 0) {
            $names = ($allTargets | ForEach-Object { $_.name }) -join ", "
            throw "Target '$Target' not found in $targetsCfgPath. Available: $names"
        }
    }

    # 为每个 target 准备临时 finder / downloader config (含注入 MM-dd 等)
    $runTmpDir = Join-Path $RepoRoot ("logs\.tmp\{0}" -f (Get-Date).ToString("yyyyMMdd-HHmmss"))
    New-Item -ItemType Directory -Force -Path $runTmpDir | Out-Null

    foreach ($t in $chosen) {
        $tName    = $t.name
        $tOutDir  = Join-Path $RepoRoot ("outputs\{0}\{1}" -f $runDate, $tName)
        $tFinder  = Join-Path $runTmpDir ("finder.{0}.json" -f $tName)
        $tDowner  = Join-Path $runTmpDir ("downloader.{0}.json" -f $tName)

        # 复制 finder 字段
        $tFinderObj = $t.finder | ConvertTo-Json -Depth 6 | ConvertFrom-Json
        # (date 字段在 finder config 中已存在, 不用 Add-Member)
        $tFinderObj | ConvertTo-Json -Depth 6 |
            ForEach-Object { [System.IO.File]::WriteAllText($tFinder, $_, (New-Object System.Text.UTF8Encoding $false)) }

        # downloader
        $t.finder | Out-Null  # ensure exists
        $tDownerObj = $t.downloader
        $tDownerObj | ConvertTo-Json -Depth 6 |
            ForEach-Object { [System.IO.File]::WriteAllText($tDowner, $_, (New-Object System.Text.UTF8Encoding $false)) }

        # analyzer mode (默认 case)
        $tAnalyzerMode = "case"
        if ($t.PSObject.Properties['analyzer'] -and $t.analyzer.PSObject.Properties['mode']) {
            $tAnalyzerMode = [string]$t.analyzer.mode
        }

        $TargetsList += @{
            name              = $tName
            finder_cfg_path   = $tFinder
            downloader_cfg_path = $tDowner
            workflow_url      = $t.finder.workflow_url
            repo              = $t.downloader.repo
            out_dir           = $tOutDir
            analyzer_mode     = $tAnalyzerMode
        }
    }
} else {
    # 单 target 模式 (沿用旧行为: outputs\<MM-DD>)
    $legacyOutDir = Join-Path $RepoRoot ("outputs\{0}" -f $runDate)
    $TargetsList += @{
        name              = "default"
        finder_cfg_path   = Join-Path $RepoRoot "config\finder.config.json"
        downloader_cfg_path = Join-Path $RepoRoot "config\downloader.config.json"
        workflow_url      = ""
        repo              = ""
        out_dir           = $legacyOutDir
        analyzer_mode     = "case"
    }
}

Write-Both "[run_all] targets:    $(($TargetsList | ForEach-Object { $_.name }) -join ', ')"
foreach ($t in $TargetsList) {
    Write-Both "[run_all]   - $($t.name)  out=$($t.out_dir)"
}

# --- Step 1+2: find + download (per target, sequential) ---
if (-not $SkipFind -or -not $SkipDownload) {
    foreach ($t in $TargetsList) {
        Step ("target: " + $t.name)

        if (-not $SkipFind) {
            Write-Both "[run_all]   -> find workflow"
            $errMarker = Join-Path $RepoRoot "logs\finder-last-error.txt"
            Remove-Item -LiteralPath $errMarker -ErrorAction SilentlyContinue
            $args = @{
                ConfigPath = $t.finder_cfg_path
                OutDir     = $t.out_dir
            }
            if ($Date) { $args.Date = $Date }
            if ($t.workflow_url) { $args.WorkflowUrl = $t.workflow_url }
            & $FinderPs1 @args
            if (Test-Path $errMarker) {
                $errTxt = Get-Content -LiteralPath $errMarker -Raw
                throw "[$($t.name)] find-workflow failed: $errTxt"
            }
            $expectedInfo = Join-Path $t.out_dir "workflow-info.json"
            if (-not (Test-Path $expectedInfo)) {
                throw "[$($t.name)] find-workflow did not produce workflow-info.json (expected: $expectedInfo)"
            }
            Write-Both "[run_all]   [$($t.name)] finder OK"
        }

        if (-not $SkipDownload) {
            Write-Both "[run_all]   -> download logs"
            $errMarker = Join-Path $RepoRoot "logs\downloader-last-error.txt"
            Remove-Item -LiteralPath $errMarker -ErrorAction SilentlyContinue
            $args = @{
                ConfigPath = $t.downloader_cfg_path
                InfoPath   = Join-Path $t.out_dir "workflow-info.json"
                OutDir     = $t.out_dir
            }
            if ($t.repo) { $args.Repo = $t.repo }
            & $DownloaderPs1 @args
            if (Test-Path $errMarker) {
                $errTxt = Get-Content -LiteralPath $errMarker -Raw
                throw "[$($t.name)] download-log failed: $errTxt"
            }
            Write-Both "[run_all]   [$($t.name)] downloader OK"
        }
    }
} else {
    Write-Both "[run_all] Step find+download skipped (all targets)"
}

# --- Step 3: analyze (per target, sequential) ---
if (-not $SkipAnalyze) {
    foreach ($t in $TargetsList) {
        # Analyzer 期望 layout 形如 <out_dir>/<run-dir>, 这里直接传 out_dir
        # (单 target 模式: out_dir = outputs\MM-DD; 多 target: outputs\MM-DD\<target_name>)
        Step ("analyze: " + $t.name)

        $args = @($AnalyzerPy)
        $args += @("--out-dir", $t.out_dir)
        $args += @("--mode", $t.analyzer_mode)
        & $python @args
        if ($LASTEXITCODE -ne 0) { throw "[$($t.name)] analyze-log failed (exit=$LASTEXITCODE)" }
        Write-Both "[run_all]   [$($t.name)] analyzer (mode=$($t.analyzer_mode)) exit = $LASTEXITCODE"

        Step ("classify: " + $t.name)
        $args = @($ClassifierPy)
        $args += @("--out-dir", $t.out_dir)
        $args += @("--mode", $t.analyzer_mode)
        & $python @args
        if ($LASTEXITCODE -ne 0) { throw "[$($t.name)] classify-errors failed (exit=$LASTEXITCODE)" }
        Write-Both "[run_all]   [$($t.name)] classifier (mode=$($t.analyzer_mode)) exit = $LASTEXITCODE"
    }
} else {
    Write-Both "[run_all] Step analyze+classify skipped"
}

# --- Step 4: build summary (合并简报) ---
if (-not $SkipSummary) {
    Step ("summary")
    $summaryRoot = Join-Path $RepoRoot ("outputs\{0}" -f $runDate)
    $args = @($SummaryPy)
    $args += @("--out-dir", $summaryRoot)
    if ($TargetsConfig) { $args += @("--targets-config", $TargetsConfig) }
    & $python @args
    if ($LASTEXITCODE -ne 0) { throw "build-summary failed (exit=$LASTEXITCODE)" }
    Write-Both "[run_all]   summary exit = $LASTEXITCODE"
} else {
    Write-Both "[run_all] Step summary skipped"
}

Write-Both ""
Write-Both "[run_all] =========================================="
Write-Both "[run_all] ALL DONE"
Write-Both "[run_all] Outputs:"
foreach ($t in $TargetsList) {
    Write-Both "[run_all]   - $($t.out_dir)"
}
