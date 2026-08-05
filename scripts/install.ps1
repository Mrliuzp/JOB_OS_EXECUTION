$ErrorActionPreference = "Stop"

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "未找到 Python 启动器，请先安装 Python 3.11 或更高版本。"
}

if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    throw "未找到 Node.js，请先安装 Node.js 22.13 或更高版本。"
}

$nodeVersionText = (& node --version).Trim().TrimStart("v")
try {
    $nodeVersion = [version]$nodeVersionText
} catch {
    throw "无法识别 Node.js 版本：$nodeVersionText"
}

$minimumNodeVersion = [version]"22.13.0"
if ($nodeVersion -lt $minimumNodeVersion) {
    throw "当前 Node.js 版本为 $nodeVersionText，项目要求 22.13.0 或更高版本。请升级后重新运行安装脚本。"
}

py -3.11 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\pip.exe install -e ".[dev]"

Push-Location apps\web
try {
    & npm.cmd ci
} finally {
    Pop-Location
}

Write-Host "安装完成。请运行 .\.venv\Scripts\Activate.ps1，然后执行 jobos init。"
