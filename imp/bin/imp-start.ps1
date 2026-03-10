$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. "$ScriptDir\imp-env.ps1"

Write-Host "Starting IMP AI System..."

$processes = @(
    "core/imp-execute.py",
    "core/imp-learning-memory.py",
    "core/imp-strategy-generator.py",
    "self-improvement/imp-code-updater.py",
    "security/imp-security-optimizer.py",
    "expansion/imp-cluster-manager.py"
)

foreach ($relative in $processes) {
    $path = Join-Path $RootDir $relative
    Start-Process -FilePath $PythonBin -ArgumentList @($path) -WindowStyle Hidden
}

Write-Host "IMP AI is now running."
