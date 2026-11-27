[Console]::OutputEncoding=[Text.UTF8Encoding]::new()
$OutputEncoding=[Console]::OutputEncoding
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null=[Windows.Storage.StorageFile,Windows.Storage,ContentType=WindowsRuntime]
$null=[Windows.Graphics.Imaging.BitmapDecoder,Windows.Foundation,ContentType=WindowsRuntime]
$null=[Windows.Media.Ocr.OcrEngine,Windows.Foundation,ContentType=WindowsRuntime]
$null=[Windows.Globalization.Language,Windows.Foundation,ContentType=WindowsRuntime]
$asTask=([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {$_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.IsGenericMethod})[0]
function Await($op,$type){$t=$asTask.MakeGenericMethod($type).Invoke($null,@($op));$t.Wait();$t.Result}
$base='D:\codex_work\projects\刘总艾灸机器人自动化\整理成果\素材库\官网素材\2026-11-27'
$engine=[Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage([Windows.Globalization.Language]::new('zh-Hans-CN'))
$rows=@()
foreach($p in (Get-ChildItem -LiteralPath "$base\OCR输入" -Filter '*.png' | Sort-Object Name)){
$file=Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync($p.FullName)) ([Windows.Storage.StorageFile])
$stream=Await ($file.OpenReadAsync()) ([Windows.Storage.Streams.IRandomAccessStreamWithContentType])
$decoder=Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
$bitmap=Await ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
$result=Await ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
$text=(@($result.Lines | ForEach-Object {$_.Text}) -join "`n")
[IO.File]::WriteAllText("$base\OCR\$($p.BaseName).txt",$text,[Text.UTF8Encoding]::new($false))
$rows+=@{id=$p.BaseName;text=$text;status='机器OCR，未逐字校对';engine='Windows.Media.Ocr zh-Hans-CN'}
$bitmap.Dispose();$stream.Dispose()
Write-Output "$($p.BaseName): $($text.Length)"
}
[IO.File]::WriteAllText("$base\OCR\图片OCR.json",(ConvertTo-Json -InputObject @($rows) -Depth 5),[Text.UTF8Encoding]::new($false))
