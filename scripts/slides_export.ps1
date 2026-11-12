# Export a deck to PDF and to one PNG per slide with the PowerPoint installed on this PC.
#   powershell -NoProfile -File scripts\slides_export.ps1 docs\examples\tap\red_flag_report.pptx <folder for the PNGs>
param([string]$Deck, [string]$PngDir = "")
$ErrorActionPreference = "Stop"
$path = (Resolve-Path $Deck).Path
$pdf = [System.IO.Path]::ChangeExtension($path, ".pdf")
$pp = New-Object -ComObject PowerPoint.Application
try {
    $pres = $pp.Presentations.Open($path, $true, $false, $false)   # read-only, no window
    $pres.SaveAs($pdf, 32)                                          # ppSaveAsPDF
    if ($PngDir -ne "") {
        New-Item -ItemType Directory -Force -Path $PngDir | Out-Null
        $dir = (Resolve-Path $PngDir).Path
        foreach ($slide in $pres.Slides) {
            $slide.Export((Join-Path $dir ("slide-{0:d2}.png" -f $slide.SlideIndex)), "PNG", 1600, 900)
        }
    }
    $pres.Close()
    Write-Output "saved $pdf"
}
finally {
    $pp.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($pp) | Out-Null
}
