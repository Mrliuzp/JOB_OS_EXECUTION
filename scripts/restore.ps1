param(
    [Parameter(Mandatory = $true)]
    [string]$ArchivePath,
    [string]$DataDir = "$HOME\.jobos"
)

$ErrorActionPreference = "Stop"
if (-not (Test-Path $ArchivePath)) {
    throw "备份文件不存在：$ArchivePath"
}
if (Test-Path $DataDir) {
    $safetyCopy = "$DataDir.before-restore-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
    Move-Item $DataDir $safetyCopy
    Write-Host "原数据已移动到：$safetyCopy"
}
New-Item -ItemType Directory -Force -Path $DataDir | Out-Null
Expand-Archive -Path $ArchivePath -DestinationPath $DataDir -Force
Write-Host "恢复完成：$DataDir"
