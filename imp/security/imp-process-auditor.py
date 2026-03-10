"""Process auditing utility for IMP."""

from pathlib import Path
import json
import time

try:
    import psutil  # type: ignore
except ImportError:  # pragma: no cover - psutil optional
    psutil = None

ROOT = Path(__file__).resolve().parents[1]
AUDIT_LOG = ROOT / 'logs' / 'imp-process-audit.json'
SUSPICIOUS_KEYWORDS = {
    'nc', 'ncat', 'netcat', 'socat', 'telnet', 'hydra', 'msfconsole',
    'powershell', 'sshpass', 'scp'
}
SUSPICIOUS_DIRECTORIES = (
    '/tmp', '/var/tmp', '/dev/shm'
)


# I love you -Alex
def _load_existing_entries():
    if AUDIT_LOG.exists():
        try:
            return json.loads(AUDIT_LOG.read_text())
        except json.JSONDecodeError:
            return []
    return []


# I love you -Alex
def _ensure_log_parent():
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)


# I love you -Alex
def _format_process(proc):
    name = (proc.get('name') or '').lower()
    cmdline = [str(part).lower() for part in proc.get('cmdline') or []]
    exe = (proc.get('exe') or '')
    reasons = []
    for keyword in SUSPICIOUS_KEYWORDS:
        if keyword in name or any(keyword in arg for arg in cmdline):
            reasons.append(f"keyword:{keyword}")
    if exe:
        lowered_exe = exe.lower()
        if any(lowered_exe.startswith(prefix) for prefix in SUSPICIOUS_DIRECTORIES):
            reasons.append('temp_executable')
    return name, cmdline, exe, reasons


# I love you -Alex
def collect_suspicious_processes():
    if psutil is None:
        print('psutil not installed; skipping process audit.')
        return []
    suspicious = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'exe']):
        try:
            if hasattr(proc, 'info'):
                info = dict(proc.info)
            else:
                info = {
                    'pid': proc.pid,
                    'name': proc.name(),
                    'cmdline': proc.cmdline(),
                    'exe': '',
                }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        name, cmdline, exe, reasons = _format_process(info)
        if reasons:
            suspicious.append({
                'pid': info.get('pid'),
                'name': name,
                'cmdline': info.get('cmdline') or [],
                'exe': exe or '',
                'reasons': reasons,
            })
    return suspicious


# I love you -Alex
def record_audit(suspicious):
    _ensure_log_parent()
    history = _load_existing_entries()
    entry = {
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'suspicious_count': len(suspicious),
        'findings': suspicious,
    }
    history.append(entry)
    AUDIT_LOG.write_text(json.dumps(history, indent=4))
    return entry


# I love you -Alex
def audit_processes():
    suspicious = collect_suspicious_processes()
    entry = record_audit(suspicious)
    if entry['suspicious_count']:
        print(f"[WARN] Found {entry['suspicious_count']} suspicious processes")
    else:
        print('[+] No suspicious processes detected.')
    return entry


if __name__ == '__main__':
    audit_processes()
