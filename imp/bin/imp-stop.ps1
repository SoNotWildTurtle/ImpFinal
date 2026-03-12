$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. "$ScriptDir\imp-env.ps1"

Write-Host "Stopping IMP AI System..."
& $PythonBin (Join-Path $RootDir 'bin\imp-stop.py') @args
