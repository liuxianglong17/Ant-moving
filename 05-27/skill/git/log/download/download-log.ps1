param(
    [Parameter(Mandatory=$true)]
    [string]$WorkflowUrl,

    [string]$Token
)

$ErrorActionPreference = "Stop"

function Get-GitHubToken {
    param([string]$ProvidedToken)

    if ($ProvidedToken -and $ProvidedToken -ne "") {
        return $ProvidedToken
    }

    $paths = @(
        "D:\personal_code\My-agent-assistant\local_data\github_token.txt",
        "$PSScriptRoot\..\..\..\local_data\github_token.txt",
        "$PSScriptRoot\..\..\local_data\github_token.txt"
    )

    foreach ($path in $paths) {
        if (Test-Path $path) {
            $tk = (Get-Content $path -Raw).Trim()
            if ($tk -and $tk -ne "") {
                Write-Host "Token loaded from: $path"
                return $tk
            }
        }
    }

    throw "GitHub token not found. Please provide -Token parameter or create local_data/github_token.txt"
}

function Parse-WorkflowRunUrl {
    param([string]$Url)

    $pattern = "https://github\.com/([^/]+)/([^/]+)/actions/runs/(\d+)"
    if ($Url -match $pattern) {
        return @{
            Owner = $matches[1]
            Repo  = $matches[2]
            RunId = $matches[3]
        }
    }
    throw "Invalid workflow run URL format. Expected: https://github.com/owner/repo/actions/runs/12345678"
}

function Get-WorkflowRunDate {
    param(
        [string]$Owner,
        [string]$Repo,
        [string]$RunId,
        [hashtable]$Headers
    )

    $url = "https://api.github.com/repos/$Owner/$Repo/actions/runs/$RunId"
    $response = Invoke-RestMethod -Uri $url -Headers $Headers -Method Get
    $createdAt = [DateTime]$response.created_at
    return $createdAt.ToLocalTime().ToString("yyyy-MM-dd")
}

function Download-WorkflowLogs {
    param(
        [string]$Owner,
        [string]$Repo,
        [string]$RunId,
        [string]$OutputDir,
        [hashtable]$Headers,
        [int]$TimeoutSec = 300,
        [int]$MaxRetries = 3
    )

    $apiBase = "https://api.github.com/repos/$Owner/$Repo"

    Write-Host "Fetching jobs for run $RunId..."

    $jobs = @()
    $page = 1
    do {
        $jobsUrl = "$apiBase/actions/runs/$RunId/jobs?per_page=100&page=$page"
        $response = Invoke-RestMethod -Uri $jobsUrl -Headers $Headers -Method Get
        $jobs += $response.jobs
        $page++
    } while ($response.jobs.Count -eq 100)

    Write-Host "Found $($jobs.Count) jobs"

    New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

    $downloadedCount = 0
    $failedCount = 0

    foreach ($job in $jobs) {
        $jobName = $job.name
        $jobFileName = "$jobName.txt" -replace '[\\/:*?"<>|]', '_'
        $jobFilePath = Join-Path $OutputDir $jobFileName

        Write-Host ""
        Write-Host "Processing job: $jobName"
        Write-Host "  Status: $($job.status), Conclusion: $($job.conclusion)"

        $retryCount = 0
        $downloadSuccess = $false

        while (-not $downloadSuccess -and $retryCount -lt $MaxRetries) {
            try {
                $retryCount++
                if ($retryCount -gt 1) {
                    Write-Host "  Retry $retryCount/$MaxRetries..."
                }

                $logUrl = "$apiBase/actions/jobs/$($job.id)/logs"
                $logResponse = Invoke-WebRequest -Uri $logUrl -Headers $Headers -Method Get `
                    -ErrorAction Stop -UseBasicParsing -TimeoutSec $TimeoutSec

                [System.IO.File]::WriteAllText($jobFilePath, $logResponse.Content, [System.Text.Encoding]::UTF8)

                $fileSize = [math]::Round((Get-Item $jobFilePath).Length / 1MB, 2)
                Write-Host "  OK ($fileSize MB)"
                $downloadSuccess = $true
                $downloadedCount++
            }
            catch {
                Write-Host "  Error: $($_.Exception.Message)"
                if ($retryCount -ge $MaxRetries) {
                    $failedCount++
                } else {
                    Start-Sleep -Seconds 5
                }
            }
        }

        Start-Sleep -Milliseconds 300
    }

    $summary = @{
        repo          = "$Owner/$Repo"
        run_id        = $RunId
        run_url       = "https://github.com/$Owner/$Repo/actions/runs/$RunId"
        total_jobs    = $jobs.Count
        downloaded    = $downloadedCount
        failed        = $failedCount
        output_dir    = $OutputDir
        downloaded_at = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    }

    $summary | ConvertTo-Json | Out-File (Join-Path $OutputDir "download-summary.json") -Encoding UTF8

    Write-Host ""
    Write-Host "========================================"
    Write-Host "Download complete!"
    Write-Host "Output directory: $OutputDir"
    Write-Host "Total jobs: $($jobs.Count), Downloaded: $downloadedCount, Failed: $failedCount"
    Write-Host "========================================"
}

try {
    $parsed = Parse-WorkflowRunUrl $WorkflowUrl
    Write-Host "=== GitHub Actions Log Downloader ==="
    Write-Host "Repository: $($parsed.Owner)/$($parsed.Repo)"
    Write-Host "Run ID: $($parsed.RunId)"
    Write-Host ""

    $token = Get-GitHubToken -ProvidedToken $Token
    $headers = @{
        "Authorization" = "token $token"
        "Accept"        = "application/vnd.github.v3+json"
        "User-Agent"    = "PowerShell-GH-Log-Fetcher"
    }

    $runDate = Get-WorkflowRunDate -Owner $parsed.Owner -Repo $parsed.Repo -RunId $parsed.RunId -Headers $headers
    Write-Host "Workflow run date (local): $runDate"

    $repoName = "$($parsed.Owner)-$($parsed.Repo)"
    $outputDir = "D:\personal_code\My-agent-assistant\local_data\logs\$runDate\$repoName-$($parsed.RunId)"

    Write-Host "Output directory: $outputDir"
    Write-Host ""

    Download-WorkflowLogs -Owner $parsed.Owner -Repo $parsed.Repo -RunId $parsed.RunId `
        -OutputDir $outputDir -Headers $headers

    Write-Host "=== Done ==="
}
catch {
    Write-Host "Error: $_"
    exit 1
}
