param(
    [string]$LogPath,
    [int]$IdleTimeoutSeconds = 30
)

# Launch imp-start.ps1 in a new terminal and stream its output here.
$ErrorActionPreference = 'Stop'

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
$ImpStart = Join-Path $ScriptRoot 'imp-start.ps1'
$LogsDir = Join-Path $ScriptRoot 'logs'

if (-not (Test-Path $LogsDir)) {
    New-Item -ItemType Directory -Path $LogsDir | Out-Null
}

if (-not $LogPath) {
    $timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $LogPath = Join-Path $LogsDir "imp-start-wrapper-$timestamp.log"
}

New-Item -ItemType File -Path $LogPath -Force | Out-Null

$command = "& `"$ImpStart`" *>&1 | Tee-Object -FilePath `"$LogPath`" -Append"
$encodedCommand = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($command))

$proc = Start-Process -FilePath "powershell" -ArgumentList "-NoProfile -ExecutionPolicy Bypass -EncodedCommand $encodedCommand" -WorkingDirectory $ScriptRoot -PassThru

Write-Host "IMP start launched in a new terminal (PID $($proc.Id)). Streaming log: $LogPath"

$lastActivity = Get-Date
$stream = $null
$reader = $null

try {
    $stream = [System.IO.File]::Open($LogPath, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
    $reader = New-Object System.IO.StreamReader($stream)
    $null = $reader.BaseStream.Seek(0, [System.IO.SeekOrigin]::End)

    while ($true) {
        if (-not $reader.EndOfStream) {
            $line = $reader.ReadLine()
            if ($line -ne $null) {
                Write-Host $line
                $lastActivity = Get-Date
            }
            continue
        }

        if ((Get-Date) - $lastActivity -ge (New-TimeSpan -Seconds $IdleTimeoutSeconds)) {
            Write-Warning "No log activity for $IdleTimeoutSeconds seconds. Stopping launched process."
            break
        }

        Start-Sleep -Milliseconds 500
    }
} finally {
    if ($reader) { $reader.Dispose() }
    if ($stream) { $stream.Dispose() }
}

if ($proc -and -not $proc.HasExited) {
    try {
        Stop-Process -Id $proc.Id -Force -ErrorAction Stop
    } catch {
        Write-Warning "Unable to stop process $($proc.Id): $_"
    }
}
