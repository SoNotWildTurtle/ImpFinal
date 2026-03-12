$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptDir '..\..')
$RootLauncher = Join-Path $RepoRoot 'imp-start.ps1'

if (-not (Test-Path $RootLauncher)) {
    throw "Root launcher not found at $RootLauncher"
}

& $RootLauncher @args
