# Luftprotokoll

Lokal Windows-pilot för luftmätningsprotokoll: ritningar, granskning, enhetsomvandling och redigerbar Excel-export i stående A4.

## Hämta och starta i PowerShell

Förutsätter Git och Python 3.11 eller senare. Logga in på GitHub vid kloning av detta privata repository.

```powershell
git clone https://github.com/linusalmeida1/luftprotokoll.git
cd luftprotokoll
powershell -NoProfile -ExecutionPolicy Bypass -File .\Installera.ps1
.\Starta.cmd
```

Läs [installations- och användarguiden](START_HAR.md) för AI-inställningar, säkerhetskopiering och arbetsflöde.

## Status

Manuell registrering, lokal lagring, granskning och Excel-export är implementerade. AI-anslutningen är valbar och kräver ett eget API-konto och modellval. Liveavläsning och installation på den avsedda Windows-datorn behöver verifieras innan skarp drift.

Ritningar, uppdragsdata och hemligheter ska inte checkas in. De undantas av `.gitignore`.

## Tester

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```
