# Picture of a databook sheet as Excel draws it, for the README (Windows with Excel).
#   powershell -NoProfile -File scripts\databook_image.ps1 docs\examples\tap\databook.xlsx "Net Debt" A1:G26 docs\images\databook-net-debt.png
param([string]$Book, [string]$Sheet, [string]$Range, [string]$Png)
$ErrorActionPreference = "Stop"
$xl = New-Object -ComObject Excel.Application
$xl.Visible = $false
$xl.DisplayAlerts = $false
try {
    $wb = $xl.Workbooks.Open((Resolve-Path $Book).Path, 0, $true)   # read-only
    $ws = $wb.Worksheets.Item($Sheet)
    $ws.Activate()
    $rng = $ws.Range($Range)
    $rng.CopyPicture(1, 2) | Out-Null                                 # as on screen, bitmap
    $scratch = $xl.Workbooks.Add()                                   # the databook's sheets are protected
    $chart = $scratch.Worksheets.Item(1).ChartObjects().Add(0, 0, $rng.Width, $rng.Height)
    $chart.Activate()
    $chart.Chart.ChartArea.Format.Line.Visible = 0
    Start-Sleep -Milliseconds 500
    $chart.Chart.Paste()
    $out = Join-Path (Get-Location) $Png
    $chart.Chart.Export($out, "PNG") | Out-Null
    $scratch.Close($false)
    $wb.Close($false)
    Write-Output "saved $out"
}
finally {
    $xl.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($xl) | Out-Null
}
