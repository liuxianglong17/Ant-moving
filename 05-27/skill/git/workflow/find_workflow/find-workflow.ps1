param(
    [Parameter(Mandatory=$true)]
    [string]$WorkflowUrl,

    [string]$Branch,

    [string]$Event,

    [string]$Date,

    [string]$StartDate,

    [string]$EndDate,

    [int]$MaxPages = 10
)

$ErrorActionPreference = "Stop"

. "$PSScriptRoot\utils\time-utils.ps1"

function Get-GitHubToken {
    $paths = @(
        "D:\personal_code\My-agent-assistant\local_data\github_token.txt",
        "$PSScriptRoot\..\..\..\local_data\github_token.txt"
    )
    foreach ($path in $paths) {
        if (Test-Path $path) {
            return (Get-Content $path -Raw).Trim()
        }
    }
    throw "GitHub token not found. Please create local_data/github_token.txt"
}

function Parse-WorkflowUrl {
    param(
        [string]$Url
    )
    $pattern = "https://github\.com/([^/]+)/([^/]+)/actions/workflows/([^/]+)"
    if ($Url -match $pattern) {
        return @{
            Owner = $matches[1]
            Repo = $matches[2]
            WorkflowId = $matches[3]
        }
    }
    throw "Invalid workflow URL format"
}

function Find-Workflows {
    param(
        [string]$Owner,
        [string]$Repo,
        [string]$WorkflowId,
        [string]$Branch,
        [string]$Event,
        [DateTime]$UtcStart,
        [DateTime]$UtcEnd,
        [int]$MaxPages
    )

    $token = Get-GitHubToken
    $headers = @{
        "Authorization" = "token $token"
        "Accept" = "application/vnd.github.v3+json"
    }

    $results = @()
    $page = 1

    while ($page -le $MaxPages) {
        $url = "https://api.github.com/repos/$Owner/$Repo/actions/workflows/$WorkflowId/runs?per_page=100&page=$page"
        $response = Invoke-WebRequest -Uri $url -Headers $headers -UseBasicParsing -TimeoutSec 60
        $data = $response.Content | ConvertFrom-Json

        if (-not $data.workflow_runs -or $data.workflow_runs.Count -eq 0) {
            break
        }

        foreach ($run in $data.workflow_runs) {
            $runCreated = [DateTime]$run.created_at

            if ($runCreated -lt $UtcStart) {
                continue
            }

            if ($runCreated -ge $UtcEnd) {
                continue
            }

            if ($Branch -and $run.head_branch -ne $Branch) {
                continue
            }

            if ($Event -and $run.event -ne $Event) {
                continue
            }

            $localCreated = $runCreated.ToLocalTime()
            $results += [PSCustomObject]@{
                URL = $run.html_url
                ID = $run.id
                Event = $run.event
                Branch = $run.head_branch
                Status = $run.status
                Conclusion = $run.conclusion
                UtcCreated = $run.created_at
                LocalCreated = $localCreated.ToString("yyyy-MM-dd HH:mm:ss")
                LocalDate = $localCreated.Date.ToString("yyyy-MM-dd")
            }
        }

        if ($data.workflow_runs.Count -lt 100) {
            break
        }
        $page++
        Start-Sleep -Milliseconds 100
    }

    return $results
}

try {
    $parsed = Parse-WorkflowUrl $WorkflowUrl
    Write-Host "=== Workflow Query ==="
    Write-Host "Repository: $($parsed.Owner)/$($parsed.Repo)"
    Write-Host "Workflow: $($parsed.WorkflowId)"
    Write-Host ""

    $filters = @()
    if ($Branch) { $filters += "Branch=$Branch" }
    if ($Event) { $filters += "Event=$Event" }

    if ($Date) {
        $range = Get-DateRangeUtc $Date
        $filters += "Date=$Date"
        Write-Host "Filters: $($filters -join ', ')"
        Write-Host "UTC Range: $($range.Start.ToString('yyyy-MM-ddTHH:mm:ssZ')) ~ $($range.End.ToString('yyyy-MM-ddTHH:mm:ssZ'))"
        Write-Host ""

        $runs = Find-Workflows -Owner $parsed.Owner -Repo $parsed.Repo -WorkflowId $parsed.WorkflowId -Branch $Branch -Event $Event -UtcStart $range.Start -UtcEnd $range.End -MaxPages $MaxPages
    } elseif ($StartDate -and $EndDate) {
        $range = Get-DateRangeUtcFromStartEnd $StartDate $EndDate
        $filters += "DateRange=$StartDate~$EndDate"
        Write-Host "Filters: $($filters -join ', ')"
        Write-Host "UTC Range: $($range.Start.ToString('yyyy-MM-ddTHH:mm:ssZ')) ~ $($range.End.ToString('yyyy-MM-ddTHH:mm:ssZ'))"
        Write-Host ""

        $runs = Find-Workflows -Owner $parsed.Owner -Repo $parsed.Repo -WorkflowId $parsed.WorkflowId -Branch $Branch -Event $Event -UtcStart $range.Start -UtcEnd $range.End -MaxPages $MaxPages
    } else {
        throw "Please specify Date or StartDate/EndDate parameter"
    }

    Write-Host "=== Query Results ==="
    Write-Host "Found $($runs.Count) matching workflow(s)"
    Write-Host ""

    if ($runs) {
        foreach ($run in $runs) {
            Write-Host "URL: $($run.URL)"
            Write-Host "ID: $($run.ID)"
            Write-Host "Branch: $($run.Branch)"
            Write-Host "Event: $($run.Event)"
            Write-Host "Status: $($run.Status)"
            Write-Host "Conclusion: $($run.Conclusion)"
            Write-Host "Local Time: $($run.LocalCreated)"
            Write-Host "UTC Time: $($run.UtcCreated)"
            Write-Host ""
        }
    } else {
        Write-Host "No matching workflows found"
        Write-Host ""
        Write-Host "Possible reasons:"
        Write-Host "1. No workflow triggered on the specified date"
        Write-Host "2. Filter criteria too strict"
        Write-Host "3. Workflow not yet triggered (e.g., nightly tasks usually trigger in early morning)"
    }
    Write-Host "=== Query End ==="
} catch {
    Write-Host "Error: $_"
    exit 1
}
