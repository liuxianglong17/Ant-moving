function Convert-LocalToUtc {
    param(
        [DateTime]$LocalTime
    )
    return $LocalTime.ToUniversalTime()
}

function Convert-UtcToLocal {
    param(
        [DateTime]$UtcTime
    )
    return $UtcTime.ToLocalTime()
}

function Get-DateRangeUtc {
    param(
        [string]$DateStr
    )
    $localDate = [DateTime]::ParseExact($DateStr, "yyyy-MM-dd", $null)
    $startLocal = $localDate.Date
    $endLocal = $startLocal.AddDays(1)
    return @{
        Start = $startLocal.ToUniversalTime()
        End = $endLocal.ToUniversalTime()
    }
}

function Get-DateRangeUtcFromStartEnd {
    param(
        [string]$StartDateStr,
        [string]$EndDateStr
    )
    $startLocal = [DateTime]::ParseExact($StartDateStr, "yyyy-MM-dd", $null).Date
    $endLocal = [DateTime]::ParseExact($EndDateStr, "yyyy-MM-dd", $null).Date.AddDays(1)
    return @{
        Start = $startLocal.ToUniversalTime()
        End = $endLocal.ToUniversalTime()
    }
}
