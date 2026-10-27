$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (-not (Test-Path '.venv\Scripts\python.exe')) { throw 'Kör Installera.ps1 först.' }
& '.\.venv\Scripts\python.exe' app.py --open
