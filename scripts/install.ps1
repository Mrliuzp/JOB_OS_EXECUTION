$ErrorActionPreference = "Stop"

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "未找到 Python 启动器，请先安装 Python 3.11 或更高版本。"
}

py -3.11 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\pip.exe install -e ".[dev]"

Push-Location apps\web
try {
    npm ci
} finally {
    Pop-Location
}

Write-Host "安装完成。请运行 .\.venv\Scripts\Activate.ps1，然后执行 jobos init。"
