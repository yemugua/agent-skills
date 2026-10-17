# wechat-local-reader setup script (Windows PowerShell)
# Usage: cd <skill>/tool ; .\setup.ps1
# NOTE: keep this file ASCII-only so Windows PowerShell 5.1 (ANSI default) can parse it.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "python not found on PATH. Install Python >= 3.10 first."
}

Write-Host "[1/3] Creating isolated venv .venv ..."
python -m venv .venv
$venvPy = Join-Path $root ".venv\Scripts\python.exe"

Write-Host "[2/3] Installing dependencies (China mirror first, PyPI as fallback) ..."
& $venvPy -m pip install -r (Join-Path $root "requirements.txt") `
    -i https://mirrors.aliyun.com/pypi/simple/ --timeout 60 --retries 3 `
    --trusted-host mirrors.aliyun.com
if ($LASTEXITCODE -ne 0) {
    Write-Host "Mirror failed, falling back to PyPI ..."
    & $venvPy -m pip install -r (Join-Path $root "requirements.txt") --timeout 60 --retries 3
}

Write-Host "[3/3] Creating launcher wechat-cli.bat ..."
$launcher = "@echo off`r`nset PYTHONPATH=$root`r`n`"$root\.venv\Scripts\python.exe`" -c `"import sys; from wechat_cli.main import cli; sys.exit(cli())`" %*"
Set-Content -Path (Join-Path $root "wechat-cli.bat") -Value $launcher -Encoding ASCII

Write-Host ""
Write-Host "Done. Add $root to PATH, then run:  wechat-cli --help"
Write-Host "Or run inside this folder:  wechat-cli.bat --help"
Write-Host "Next: make sure WeChat PC is running and logged in, then run:  wechat-cli.bat init"
