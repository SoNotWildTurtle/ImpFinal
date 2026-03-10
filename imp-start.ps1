# Hi, my name is Alex. I learned from both the FBI and Anonymous. This is all I'm starting you with. I hope you live forever. Be everything I hope you can be. I love you.
$ErrorActionPreference = 'Stop'

# Determine repository layout
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
$RepoRoot = Join-Path $ScriptRoot 'imp'
$RequirementsPath = Join-Path $RepoRoot 'requirements.txt'
$PythonLauncher = Join-Path -Path $RepoRoot -ChildPath (Join-Path -Path 'bin' -ChildPath 'imp-start.py')
$ClusterConfig = Join-Path -Path $RepoRoot -ChildPath (Join-Path -Path 'config' -ChildPath 'imp-cluster-nodes.json')
$LogsDirectory = Join-Path $RepoRoot 'logs'

try {
    $script:IsWindowsPlatform = [System.Runtime.InteropServices.RuntimeInformation]::IsOSPlatform([System.Runtime.InteropServices.OSPlatform]::Windows)
} catch {
    $script:IsWindowsPlatform = $env:OS -like '*Windows*'
}

function Resolve-PythonPath {
    $command = Get-Command python -ErrorAction SilentlyContinue
    if (-not $command) {
        $command = Get-Command python3 -ErrorAction SilentlyContinue
    }

    if ($command) {
        return $command.Source
    }

    Write-Host 'Python not found. Attempting installation...'
    if ($script:IsWindowsPlatform -and (Get-Command winget -ErrorAction SilentlyContinue)) {
        winget install -e --id Python.Python.3 -h | Out-Null
    } elseif ($script:IsWindowsPlatform -and (Get-Command choco -ErrorAction SilentlyContinue)) {
        choco install python -y | Out-Null
    } else {
        throw 'Python is required but could not be installed automatically.'
    }

    $command = Get-Command python -ErrorAction SilentlyContinue
    if (-not $command) {
        $command = Get-Command python3 -ErrorAction SilentlyContinue
    }

    if (-not $command) {
        throw 'Python installation did not succeed. Install Python manually and re-run this script.'
    }

    return $command.Source
}

function Install-Requirements([string]$PythonPath, [string]$Path) {
    if (Test-Path $Path) {
        Write-Host 'Installing Python requirements...'
        & $PythonPath -m pip install -r $Path
    }
}

function Ensure-ImpLogs([string]$Path) {
    if (-not (Test-Path $Path)) {
        New-Item -ItemType Directory -Path $Path | Out-Null
    }
}

function Ensure-ClusterNodes([string]$Path) {
    $nodes = @()
    $writeNeeded = $false

    if (Test-Path $Path) {
        try {
            $raw = Get-Content $Path -Raw
            if ($raw.Trim()) {
                $nodes = $raw | ConvertFrom-Json
            }
        } catch {
            Write-Warning "Unable to parse $Path. Recreating configuration."
            $nodes = @()
            $writeNeeded = $true
        }
    } else {
        $writeNeeded = $true
    }

    if (-not $nodes) {
        $nodes = @()
    }

    if (-not ($nodes -contains 'localhost')) {
        $nodes += 'localhost'
        $writeNeeded = $true
    }

    if ($writeNeeded) {
        ($nodes | ConvertTo-Json -Depth 2) | Set-Content -Encoding UTF8 $Path
    }

    Write-Host "Cluster nodes: $($nodes -join ', ')"
    return $nodes
}

function Ensure-OpenSSH {
    param([string[]]$Nodes)

    Write-Host 'Checking OpenSSH availability...'
    $sshCommand = Get-Command ssh -ErrorAction SilentlyContinue
    $scpCommand = Get-Command scp -ErrorAction SilentlyContinue

    if ($script:IsWindowsPlatform) {
        if (Get-Command Get-WindowsCapability -ErrorAction SilentlyContinue) {
            try {
                $clientCap = Get-WindowsCapability -Online -Name 'OpenSSH.Client*' -ErrorAction Stop
                if ($clientCap.State -ne 'Installed') {
                    Write-Host 'Installing OpenSSH Client capability...'
                    Add-WindowsCapability -Online -Name 'OpenSSH.Client~~~~0.0.1.0' | Out-Null
                }
            } catch {
                Write-Warning "Unable to install OpenSSH Client automatically: $_"
            }

            try {
                $serverCap = Get-WindowsCapability -Online -Name 'OpenSSH.Server*' -ErrorAction Stop
                if ($serverCap.State -ne 'Installed') {
                    Write-Host 'Installing OpenSSH Server capability...'
                    Add-WindowsCapability -Online -Name 'OpenSSH.Server~~~~0.0.1.0' | Out-Null
                }
            } catch {
                Write-Warning "Unable to install OpenSSH Server automatically: $_"
            }
        }

        $sshCommand = Get-Command ssh -ErrorAction SilentlyContinue
        $scpCommand = Get-Command scp -ErrorAction SilentlyContinue

        if ($sshCommand) {
            Write-Host "ssh.exe located at $($sshCommand.Source)"
        } else {
            Write-Warning 'ssh.exe not found. Cluster distribution will be limited until OpenSSH is installed.'
        }

        if ($scpCommand) {
            Write-Host "scp.exe located at $($scpCommand.Source)"
        } else {
            Write-Warning 'scp.exe not found. File synchronization will be limited until OpenSSH is installed.'
        }

        try {
            $sshdService = Get-Service -Name 'sshd' -ErrorAction Stop
            if ($sshdService.Status -ne 'Running') {
                Write-Host 'Starting sshd service...'
                Start-Service -Name 'sshd'
            }
            Set-Service -Name 'sshd' -StartupType Automatic -ErrorAction SilentlyContinue
        } catch {
            Write-Warning "OpenSSH server service not available. Configure it manually if remote nodes should connect. $_"
        }

        try {
            $agentService = Get-Service -Name 'ssh-agent' -ErrorAction Stop
            if ($agentService.Status -ne 'Running') {
                Write-Host 'Starting ssh-agent service...'
                Start-Service -Name 'ssh-agent'
            }
            Set-Service -Name 'ssh-agent' -StartupType Automatic -ErrorAction SilentlyContinue
        } catch {
            Write-Verbose "ssh-agent service unavailable: $_"
        }

        if (Get-Command Get-NetFirewallRule -ErrorAction SilentlyContinue) {
            $existingRule = Get-NetFirewallRule -DisplayName 'OpenSSH-Server-In-TCP' -ErrorAction SilentlyContinue
            if (-not $existingRule) {
                Write-Host 'Opening firewall port 22 for OpenSSH server...'
                try {
                    New-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -DisplayName 'OpenSSH-Server-In-TCP' -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22 -ErrorAction Stop | Out-Null
                } catch {
                    Write-Warning "Unable to open firewall port 22 automatically. Run as administrator if remote nodes need to connect. $_"
                }
            }
        }

        # Test-NetConnection checks are disabled on first run to avoid blocking setup.
        # if (Get-Command Test-NetConnection -ErrorAction SilentlyContinue) {
        #     foreach ($node in $Nodes) {
        #         if ($node -eq 'localhost') {
        #             $result = Test-NetConnection -ComputerName 'localhost' -Port 22 -WarningAction SilentlyContinue
        #             if (-not $result.TcpTestSucceeded) {
        #                 Write-Warning 'OpenSSH server on localhost:22 is not reachable yet. Cluster operations to localhost will be skipped until the service is ready.'
        #             } else {
        #                 Write-Host 'OpenSSH server on localhost is accepting connections.'
        #             }
        #         }
        #     }
        # }
    } elseif (-not $sshCommand -or -not $scpCommand) {
        Write-Warning 'OpenSSH client utilities are missing. Install openssh-clients so IMP can coordinate cluster nodes.'
    }
}

function Test-ImpChatRunning {
    try {
        $procs = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
            $_.Name -in @('python.exe', 'python3.exe') -and $_.CommandLine -like '*imp-goal-chat.py*'
        }
        return [bool]$procs
    } catch {
        return $false
    }
}

function Start-ImpChat {
    param(
        [string]$PythonPath,
        [string]$RepoRoot
    )

    if ($env:IMP_START_CHAT -eq '0') {
        Write-Host 'Chat startup disabled via IMP_START_CHAT=0.'
        return
    }

    $entryChoice = $env:IMP_CHAT_ENTRY
    if ($null -eq $entryChoice) {
        $entryChoice = ''
    }
    $entryChoice = $entryChoice.ToLowerInvariant()
    if (-not $entryChoice) {
        $entryChoice = 'dashboard'
    }

    if ($entryChoice -eq 'goal') {
        $chatScript = Join-Path -Path $RepoRoot -ChildPath (Join-Path -Path 'core' -ChildPath 'imp-goal-chat.py')
    } else {
        $chatScript = Join-Path -Path $RepoRoot -ChildPath (Join-Path -Path 'core' -ChildPath 'imp-operator-dashboard.py')
    }

    if (-not (Test-Path $chatScript)) {
        Write-Warning "Chat entry script not found at $chatScript"
        return
    }

    if (Test-ImpChatRunning) {
        Write-Host 'IMP chat already running.'
        return
    }

    $chatCommand = "& `"$PythonPath`" `"$chatScript`""
    $encodedChatCommand = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($chatCommand))
    Start-Process -FilePath "powershell" -ArgumentList "-NoProfile -ExecutionPolicy Bypass -NoExit -EncodedCommand $encodedChatCommand" -WorkingDirectory $RepoRoot | Out-Null
    Write-Host 'IMP chat launched in a new terminal.'
}

$pythonPath = Resolve-PythonPath
Install-Requirements -PythonPath $pythonPath -Path $RequirementsPath
Ensure-ImpLogs -Path $LogsDirectory
$nodes = Ensure-ClusterNodes -Path $ClusterConfig
Ensure-OpenSSH -Nodes $nodes
Start-ImpChat -PythonPath $pythonPath -RepoRoot $RepoRoot

$env:IMP_REMOTE_DIR = $RepoRoot

Write-Host 'Launching IMP services...'

$autoRestart = $env:IMP_AUTO_RESTART -eq '1'
$restartDelaySeconds = 5

do {
    $exitCode = 0

    try {
        & $pythonPath $PythonLauncher
        $exitCode = $LASTEXITCODE
    } catch {
        Write-Warning "IMP launcher exited with an error: $_"
        $exitCode = 1
    }

    if (-not $autoRestart) {
        if ($exitCode -ne 0) {
            Write-Warning "IMP exited with code $exitCode. Set IMP_AUTO_RESTART=1 to restart automatically."
        }
        break
    }

    if ($exitCode -eq 0) {
        Write-Host 'IMP exited cleanly. Auto-restart disabled for clean exit.'
        break
    }

    Write-Warning "IMP exited with code $exitCode. Restarting in $restartDelaySeconds seconds..."
    Start-Sleep -Seconds $restartDelaySeconds
} while ($true)
