param(
    [string]$DataDir = "$HOME\.jobos",
    [string]$BackupDir = ".\backups"
)

$ErrorActionPreference = "Stop"
if (-not (Test-Path $DataDir)) {
    throw "JobOS 数据目录不存在：$DataDir"
}
New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$archive = Join-Path $BackupDir "jobos-backup-$timestamp.zip"
Compress-Archive -Path (Join-Path $DataDir "*") -DestinationPath $archive -CompressionLevel Optimal
Write-Host "备份完成：$archive"
