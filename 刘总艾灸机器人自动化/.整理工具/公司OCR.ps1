[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$OutputEncoding = [Console]::OutputEncoding
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Storage.StorageFile,Windows.Storage,ContentType=WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapDecoder,Windows.Foundation,ContentType=WindowsRuntime]
$null = [Windows.Media.Ocr.OcrEngine,Windows.Foundation,ContentType=WindowsRuntime]
$null = [Windows.Globalization.Language,Windows.Foundation,ContentType=WindowsRuntime]
$asTask = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.IsGenericMethod })[0]
function Await($op, $type) {
    $task = $asTask.MakeGenericMethod($type).Invoke($null,@($op))
    $task.Wait()
    $task.Result
}
$base = 'D:\codex_work\projects\刘总艾灸机器人自动化\整理成果\知识库\公司OCR'
$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage([Windows.Globalization.Language]::new('zh-Hans-CN'))
$results = @()
foreach ($p in (Get-ChildItem -LiteralPath "$base\页面" -Filter '*.png' | Sort-Object Name)) {
    $file = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync($p.FullName)) ([Windows.Storage.StorageFile])
    $stream = Await ($file.OpenReadAsync()) ([Windows.Storage.Streams.IRandomAccessStreamWithContentType])
    $decoder = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
    $bitmap = Await ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
    $result = Await ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
    $lines = @($result.Lines | ForEach-Object { $_.Text })
    $page = [int]($p.BaseName -replace 'page-','')
    $text = $lines -join "`n"
    [System.IO.File]::WriteAllText("$base\$($p.BaseName).txt",$text,[System.Text.UTF8Encoding]::new($false))
    $results += [ordered]@{page=$page;image=$p.Name;text=$text;lines=$lines.Count;engine='Windows.Media.Ocr zh-Hans-CN';status='机器识别，待逐字校对'}
    $bitmap.Dispose(); $stream.Dispose()
    Write-Output "OCR page $page : $($text.Length) chars"
}
[System.IO.File]::WriteAllText("$base\逐页OCR.json",(ConvertTo-Json -InputObject @($results) -Depth 6),[System.Text.UTF8Encoding]::new($false))
[System.IO.File]::WriteAllText("$base\公司介绍_全量OCR.txt",(($results | ForEach-Object { "【第$($_.page)页】`n$($_.text)" }) -join "`n`n"),[System.Text.UTF8Encoding]::new($false))
