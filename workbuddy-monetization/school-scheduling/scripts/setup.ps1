param([string]$EnvironmentPath = (Join-Path (Split-Path $PSScriptRoot -Parent) '.venv'))
$ErrorActionPreference = 'Stop'
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [Console]::OutputEncoding
$env:PYTHONUTF8 = '1'
try {
    if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
        throw 'Python Launcher not found. Install Python 3.12 x64 with the launcher, then rerun this script.'
    }
    & py -3.12 -c "import sys,struct; assert sys.version_info[:2]==(3,12) and struct.calcsize('P')==8, 'Python 3.12 x64 required'"
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.12 x64 is unavailable.' }
    $EnvironmentPath = [System.IO.Path]::GetFullPath($EnvironmentPath)
    $python = Join-Path $EnvironmentPath 'Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $python)) {
        if (Test-Path -LiteralPath $EnvironmentPath) { throw 'Target exists but is not a Python environment; choose a new -EnvironmentPath.' }
        & py -3.12 -m venv $EnvironmentPath
        if ($LASTEXITCODE -ne 0) { throw 'Failed to create an isolated environment.' }
    }
    & $python -c "import sys; assert sys.version_info[:2]==(3,12), 'Existing environment is not Python 3.12'"
    if ($LASTEXITCODE -ne 0) { throw 'Use a separate Python 3.12 environment.' }
    & $python -m pip install --disable-pip-version-check -r (Join-Path (Split-Path $PSScriptRoot -Parent) 'requirements.txt')
    if ($LASTEXITCODE -ne 0) { throw 'Dependency install failed. Check network/PyPI access, then rerun this script with the same -EnvironmentPath.' }
    & $python -X utf8 -c "import ortools,openpyxl; from zoneinfo import ZoneInfo; ZoneInfo('Asia/Shanghai'); print('Environment OK',ortools.__version__,openpyxl.__version__)"
    if ($LASTEXITCODE -ne 0) { throw 'Dependency import check failed.' }
    Write-Output ('Python: ' + $python)
} catch {
    Write-Error $_
    exit 1
}
