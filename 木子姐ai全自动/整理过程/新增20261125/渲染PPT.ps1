$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$projectRoot = 'D:\codex_work\projects\木子姐ai全自动'
$inputPpt = Join-Path $projectRoot '原始资料\2026-11-25新增\粉之密PPT29.pptx'
$outputDir = Join-Path $projectRoot '素材库\新增20261125\PPT页面'
[System.IO.Directory]::CreateDirectory($outputDir) | Out-Null
$powerpointApp = $null
$deck = $null
try {
    $powerpointApp = New-Object -ComObject PowerPoint.Application
    $deck = $powerpointApp.Presentations.Open($inputPpt, -1, 0, 0)
    $renderWidth = 1440
    $renderHeight = [int]($renderWidth * $deck.PageSetup.SlideHeight / $deck.PageSetup.SlideWidth)
    foreach ($slide in $deck.Slides) {
        $targetPath = Join-Path $outputDir ('P{0:D2}.png' -f $slide.SlideIndex)
        if (Test-Path -LiteralPath $targetPath) { throw "目标页已存在，不覆盖：$targetPath" }
        $slide.Export($targetPath, 'PNG', $renderWidth, $renderHeight)
        Write-Output ('已渲染第{0}页' -f $slide.SlideIndex)
    }
} finally {
    if ($null -ne $deck) { $deck.Close(); [void][Runtime.InteropServices.Marshal]::ReleaseComObject($deck) }
    if ($null -ne $powerpointApp) { $powerpointApp.Quit(); [void][Runtime.InteropServices.Marshal]::ReleaseComObject($powerpointApp) }
}
