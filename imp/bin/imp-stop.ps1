$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. "$ScriptDir\imp-env.ps1"

Write-Host "Stopping IMP AI System..."

$targets = @(
    "imp-execute.py",
    "imp-learning-memory.py",
    "imp-strategy-generator.py",
    "imp-code-updater.py",
    "imp-security-optimizer.py",
    "imp-cluster-manager.py"
)

$processes = Get-CimInstance Win32_Process | Where-Object {
    $cmd = $_.CommandLine
    $cmd -and ($targets | Where-Object { $cmd -like "*$_*" })
}

foreach ($proc in $processes) {
    try {
        Stop-Process -Id $proc.ProcessId -Force -ErrorAction Stop
    } catch {
        Write-Warning "Failed to stop process $($proc.ProcessId): $($_.Exception.Message)"
    }
}

Write-Host "IMP AI has been stopped."
