[CmdletBinding()]
param(
    [string]$CompletionDirectory = (Join-Path $env:LOCALAPPDATA "FrontierRadar"),
    [string]$ProfilePath = $PROFILE.CurrentUserCurrentHost,
    [string]$FradarCommand = "fradar"
)

$ErrorActionPreference = "Stop"

$completionFile = Join-Path -Path $CompletionDirectory -ChildPath "fradar-completion.ps1"
$profileDirectory = Split-Path -Path $ProfilePath -Parent

New-Item -ItemType Directory -Force -Path $CompletionDirectory | Out-Null
New-Item -ItemType Directory -Force -Path $profileDirectory | Out-Null

$completionContent = & $FradarCommand --show-completion | Out-String
if ($LASTEXITCODE -ne 0) {
    throw "Unable to generate completion using '$FradarCommand'. Ensure fradar is installed and available."
}

Set-Content -LiteralPath $completionFile -Value $completionContent -Encoding utf8

New-Item -ItemType File -Force -Path $ProfilePath | Out-Null
$profileContent = Get-Content -LiteralPath $ProfilePath -Raw
$profileContent = if ($null -eq $profileContent) { "" } else { $profileContent }
$marker = "# Frontier Radar completion"

if ($profileContent -notmatch [regex]::Escape($marker)) {
    $escapedCompletionFile = $completionFile.Replace("'", "''")
    $profileEntry = "$marker`r`n. '$escapedCompletionFile'"
    Add-Content -LiteralPath $ProfilePath -Value $profileEntry -Encoding utf8
}

. $completionFile

Write-Host "Frontier Radar PowerShell completion installed."
Write-Host "Completion script: $completionFile"
Write-Host "Profile loader: $ProfilePath"
