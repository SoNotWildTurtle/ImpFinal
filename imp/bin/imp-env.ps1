$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Resolve-Path (Join-Path $ScriptDir '..')

$LogsDir = Join-Path $RootDir 'logs'
$ConfigDir = Join-Path $RootDir 'config'
$ModelsDir = Join-Path $RootDir 'models'
foreach ($dir in @($LogsDir, $ConfigDir, $ModelsDir)) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir | Out-Null
    }
}

$venvWindows = Join-Path $RootDir '.venv\Scripts\python.exe'
$venvPosix = Join-Path $RootDir '.venv\bin\python'
$PythonBin = $env:IMP_PYTHON
if (-not $PythonBin -and (Test-Path $venvWindows)) {
    $PythonBin = $venvWindows
}
if (-not $PythonBin -and (Test-Path $venvPosix)) {
    $PythonBin = $venvPosix
}
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

$env:IMP_ROOT = "$RootDir"
$env:IMP_REPO_ROOT = [string](Resolve-Path (Join-Path $RootDir '..'))
$env:IMP_LOG_DIR = $LogsDir
$env:IMP_CONFIG_DIR = $ConfigDir
$env:IMP_MODELS_DIR = $ModelsDir
$env:PYTHONIOENCODING = 'utf-8'
