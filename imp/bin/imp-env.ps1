$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Resolve-Path (Join-Path $ScriptDir '..')

$PythonBin = $env:IMP_PYTHON
if (-not $PythonBin) {
    $python3 = Get-Command python3 -ErrorAction SilentlyContinue
    if ($python3) { $PythonBin = $python3.Path }
}
if (-not $PythonBin) {
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) { $PythonBin = $python.Path }
}
if (-not $PythonBin) {
    throw "Python interpreter not found. Set IMP_PYTHON or install Python."
}
