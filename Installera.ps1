$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw 'Installera Python 3.11 eller senare för Windows från python.org. Välj Python Launcher vid installationen.'
}
py -3 -c "import sys; assert sys.version_info >= (3,11), 'Python 3.11 eller senare behövs'"
if ($LASTEXITCODE -ne 0) { throw 'Python-versionen behöver uppdateras.' }
if (-not (Test-Path '.venv\Scripts\python.exe')) {
    py -3 -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Kunde inte skapa programmets Python-miljö.' }
}
& '.\.venv\Scripts\python.exe' -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Installationen misslyckades. Kontrollera internetanslutningen.' }
& '.\.venv\Scripts\python.exe' -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw 'Kontrolltesterna misslyckades.' }
Write-Host 'Klart. Dubbelklicka nu på Starta.cmd.' -ForegroundColor Green
