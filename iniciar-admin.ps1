$ErrorActionPreference = 'Stop'
try {
    $monitorPython = (Get-Command pythonw.exe -ErrorAction Stop).Source
    $monitorScript = Join-Path $PSScriptRoot 'monitor.py'
    if (-not (Test-Path -LiteralPath $monitorScript -PathType Leaf)) {
        throw 'monitor.py nao encontrado na pasta do iniciador.'
    }
    Start-Process -FilePath $monitorPython -ArgumentList ('"' + $monitorScript + '"') -WorkingDirectory $PSScriptRoot -Verb RunAs -WindowStyle Hidden
} catch {
    Write-Host ('Nao foi possivel abrir o monitor como administrador: ' + $_.Exception.Message)
    exit 1
}
