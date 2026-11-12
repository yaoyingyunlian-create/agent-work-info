$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$toolkit = Join-Path $root 'thinknova-toolkit-v3'
foreach ($command in 'git','py','ffmpeg','ffprobe','node') {
    Get-Command $command -ErrorAction Stop | Out-Null
}
py -3 -c 'import sys; sys.exit(sys.version_info < (3, 11))'
if ($LASTEXITCODE -ne 0) { throw 'Python 3.11 or later is required.' }
if (-not (Test-Path -LiteralPath $toolkit)) {
    git -c core.autocrlf=false clone https://github.com/yaoyingyunlian-create/thinknova-mcp.git $toolkit
    if ($LASTEXITCODE -ne 0) { throw 'Toolkit clone failed.' }
}
if (-not (Test-Path -LiteralPath (Join-Path $toolkit 'bootstrap.py'))) {
    throw 'The existing toolkit directory does not contain bootstrap.py.'
}
Push-Location -LiteralPath $toolkit
try {
    py -3 bootstrap.py setup
    if ($LASTEXITCODE -ne 0) { throw 'Toolkit setup failed. Inspect the bootstrap output.' }
} finally {
    Pop-Location
}
foreach ($directory in '城市图片','剧情视频素材','成片/工作区') {
    New-Item -ItemType Directory -Path (Join-Path $root $directory) -Force | Out-Null
}