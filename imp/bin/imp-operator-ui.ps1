$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. "$ScriptDir\imp-env.ps1"

& $PythonBin (Join-Path $RootDir "core/imp-operator-ui.py") @args
