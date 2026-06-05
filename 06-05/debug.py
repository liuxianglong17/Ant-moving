cd "d:/personal_code/temp/nightl-log-reporter"

$kernelOut = "outputs/06-05/sgl-kernel-npu"
$token     = (Get-Content "local_data\github_token.txt" -Raw).Trim()
$headers   = @{
    "Authorization" = "token $token"
    "Accept"        = "application/vnd.github.v3+json"
    "User-Agent"    = "nightl-log-reporter"
}

# 扫所有形如 sgl-project-sgl-kernel-npu-<id> 的子目录
Get-ChildItem -Path $kernelOut -Directory |
    Where-Object { $_.Name -match '^(.+)-(\d+)$' } |   # 末尾是 digits 才是 run 目录
    ForEach-Object {
        $runDir = $_.FullName
        $name   = $_.Name
        $runId  = $Matches[2]
        $head   = $Matches[1]
        $parts  = $head -split '-'
        $repo   = $parts[-1]
        $owner  = ($parts[0..($parts.Count-2)] -join '-')

        $cachePath = Join-Path $runDir "jobs.json"
        if (Test-Path $cachePath) {
            Write-Host "[backfill] SKIP (cache exists): $name"
            return
        }

        Write-Host "[backfill] $name  owner=$owner repo=$repo runId=$runId"
        $jobs = @(); $page = 1
        do {
            $url  = "https://api.github.com/repos/$owner/$repo/actions/runs/$runId/jobs?per_page=100&page=$page"
            $resp = Invoke-RestMethod -Uri $url -Headers $headers
            $jobs += $resp.jobs
            $page++
        } while ($resp.jobs.Count -eq 100)

        @{ total=$jobs.Count; jobs=$jobs; cached_at=(Get-Date -Format "yyyy-MM-dd HH:mm:ss") } |
            ConvertTo-Json -Depth 8 |
            Out-File -Encoding utf8 $cachePath
        Write-Host "[backfill]   wrote $cachePath ($($jobs.Count) jobs)"
    }