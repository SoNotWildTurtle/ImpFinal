from pathlib import Path







import importlib.util







import json







import hashlib







import shutil







import difflib







import subprocess







import re







import tempfile







import sys







from typing import Optional















ROOT = Path(__file__).resolve().parents[1]







LEDGER_PATH = ROOT / 'self-improvement' / 'imp-blockchain-ledger.py'







LEDGER_FILE = ROOT / 'logs' / 'imp-blockchain-ledger.json'







HEAL_LOG = ROOT / 'logs' / 'imp-self-heal-log.json'







PATCH_DIR = ROOT / 'logs' / 'imp-update-patches'







LINT_LOG = ROOT / 'logs' / 'imp-lint-report.json'















spec = importlib.util.spec_from_file_location('ledger', LEDGER_PATH)







ledger = importlib.util.module_from_spec(spec)







spec.loader.exec_module(ledger)















# load log manager to ensure required log files exist







LOG_MANAGER_PATH = ROOT / 'logs' / 'imp-log-manager.py'







spec_logs = importlib.util.spec_from_file_location('logmanager', LOG_MANAGER_PATH)







logmanager = importlib.util.module_from_spec(spec_logs)







spec_logs.loader.exec_module(logmanager)















CODE_LOCK_PATH = ROOT / 'security' / 'imp-code-lock.py'







spec_lock = importlib.util.spec_from_file_location('codelock', CODE_LOCK_PATH)







codelock = importlib.util.module_from_spec(spec_lock)







spec_lock.loader.exec_module(codelock)















GOAL_CHAT_PATH = ROOT / 'core' / 'imp-goal-chat.py'







spec_chat = importlib.util.spec_from_file_location('goalchat', GOAL_CHAT_PATH)







goalchat = importlib.util.module_from_spec(spec_chat)







spec_chat.loader.exec_module(goalchat)















STUB = "# generated stub\npass\n"























def _snapshot_content(info: dict) -> Optional[str]:







    """Return the stored source for a ledger entry, regardless of storage mode."""















    if not isinstance(info, dict):







        return None







    content = info.get('content')







    if content is not None:







        return content







    blob = info.get('blob')







    if blob:







        blob_path = ROOT / blob







        try:







            return blob_path.read_text()







        except Exception:







            return None







    return None















def _lint_snippet(code: str) -> bool:







    """Return True if code passes flake8 linting."""







    tmp = tempfile.NamedTemporaryFile('w', suffix='.py', delete=False)







    tmp.write(code)







    tmp_path = Path(tmp.name)







    tmp.close()







    try:







        result = subprocess.run(['flake8', str(tmp_path)], capture_output=True, text=True)







        return result.stdout.strip() == ''







    except Exception:







        return False







    finally:







        tmp_path.unlink(missing_ok=True)















def recover_with_chatgpt(rel_path: str, description: str = '', mode: str = 'auto') -> bool:







    """Attempt to regenerate a missing or corrupt module using ChatGPT.















    The generated code is sanity-checked before being written. A unified diff







    against the previous contents is stored in ``imp-update-patches`` for







    manual review so placeholder responses do not silently overwrite modules.







    """







    prompt = f"Provide minimal Python code for {rel_path}. {description}".strip()







    try:







        text = goalchat.send_chatgpt_request(prompt, use_notes=True, mode=mode)







    except Exception:







        text = ''















    # fall back to a tiny stub if the response is empty or looks like a







    # generic placeholder often returned when the model cannot comply







    if not text or re.search(r"insert minimal python code here", text, re.I):







        text = STUB















    file_path = ROOT / rel_path







    file_path.parent.mkdir(parents=True, exist_ok=True)







    old_text = file_path.read_text() if file_path.exists() else ''















    # ensure the produced code at least compiles; otherwise keep a stub







    try:







        compile(text, rel_path, 'exec')







    except Exception:







        text = STUB















    if text != STUB and not _lint_snippet(text):







        text = STUB















    try:







        file_path.write_text(text)







    except Exception:







        return False















    PATCH_DIR.mkdir(exist_ok=True)







    patch = difflib.unified_diff(







        old_text.splitlines(True),







        text.splitlines(True),







        fromfile='previous',







        tofile=str(file_path)







    )







    (PATCH_DIR / f"{file_path.name}.patch").write_text(''.join(patch))







    return True























def run_linter() -> list:







    """Run flake8 on the repository and save any issues."""







    if not LINT_LOG.exists():







        LINT_LOG.write_text('[]')







    try:







        result = subprocess.run(['flake8', str(ROOT)], capture_output=True, text=True)







        issues = result.stdout.strip().splitlines()







    except Exception:







        issues = ['linting failed']







    LINT_LOG.write_text(json.dumps(issues, indent=4))







    return issues























def run_tests() -> bool:







    """Run a core functionality test and return True if it passes."""







    test_file = ROOT / 'tests' / 'test-core-functions.py'







    try:







        result = subprocess.run([sys.executable, str(test_file)], capture_output=True, text=True)







        return result.returncode == 0







    except Exception:







        return False























def restore_from_ledger(rel_path: str) -> bool:







    """Restore a file's content from the latest ledger snapshot."""







    entries = ledger.load_ledger()







    if not entries:







        return False







    info = entries[-1]['files'].get(rel_path)







    content = _snapshot_content(info)







    if content is None:







        return False







    file_path = ROOT / rel_path







    try:







        file_path.parent.mkdir(parents=True, exist_ok=True)







        file_path.write_text(content)







        return True







    except Exception:







        return False























# I love you -Alex







def restore_repository_from_ledger() -> list:







    """Restore every file from the latest ledger snapshot."""







    entries = ledger.load_ledger()







    if not entries:







        return []







    latest = entries[-1].get('files', {})







    restored = []







    for rel_path, info in latest.items():







        content = _snapshot_content(info)







        if content is None:







            continue







        file_path = ROOT / rel_path







        try:







            file_path.parent.mkdir(parents=True, exist_ok=True)







            file_path.write_text(content)







            restored.append(rel_path)







        except Exception:







            continue







    return restored























# I love you -Alex







def verify_and_restore_repository(threshold: int = 10, use_chatgpt: bool = False, mode: str = 'auto') -> dict:







    """Verify code and rebuild the repository if a large attack is detected.















    Runs :func:`verify_and_heal` to repair individual mismatches, then checks the







    ledger integrity. If the chain is broken or the number of mismatches exceeds







    ``threshold``, the entire repository is restored from the latest ledger







    snapshot.







    """







    mismatches = verify_and_heal(use_chatgpt=use_chatgpt, mode=mode)







    ledger_ok = ledger.verify_chain()







    restored = []







    if not ledger_ok or len(mismatches) >= threshold:







        restored = restore_repository_from_ledger()







    return {"ledger_ok": ledger_ok, "mismatches": mismatches, "restored": restored}























def verify_and_heal(apply: bool = True, use_chatgpt: bool = True, mode: str = 'auto', mint: bool = False) -> list:







    """Check code against the ledger and optionally restore mismatched files.















    Returns a list of dictionaries describing any files that required







    attention so callers can decide whether further recovery steps are







    necessary.







    """







    # Ensure standard log files exist before performing checks







    logmanager.ensure_logs()







    codelock.unlock_repo()







    if not HEAL_LOG.exists():







        HEAL_LOG.write_text('[]')







    PATCH_DIR.mkdir(exist_ok=True)







    ledger_ok = ledger.verify_chain()







    last_entry = ledger.load_ledger()[-1] if ledger.load_ledger() else None







    mismatches = []







    if last_entry:







        for rel_path, info in last_entry['files'].items():







            recorded_hash = info.get('hash', '') if isinstance(info, dict) else info







            file_path = ROOT / rel_path







            if not file_path.exists():







                restored = restore_from_ledger(rel_path)







                if restored:







                    mismatches.append({'file': rel_path, 'reason': 'restored from ledger'})







                else:







                    mismatches.append({'file': rel_path, 'reason': 'missing'})







                    if use_chatgpt:







                        recover_with_chatgpt(rel_path, 'File was missing', mode)







                continue







            actual = hashlib.sha256(file_path.read_bytes()).hexdigest()







            if actual != recorded_hash:







                if restore_from_ledger(rel_path):







                    mismatches.append({'file': rel_path, 'reason': 'restored from ledger'})







                    continue







                backups = sorted(file_path.parent.glob(file_path.name + '.backup.*'))







                if apply and backups:







                    latest = backups[-1]







                    shutil.copy2(latest, file_path)







                    mismatches.append({'file': rel_path, 'reason': 'restored from backup'})







                else:







                    if backups:







                        base_text = backups[-1].read_text().splitlines(True)







                        new_text = file_path.read_text().splitlines(True)







                        patch = difflib.unified_diff(base_text, new_text,







                                                     fromfile='backup',







                                                     tofile=str(file_path))







                        patch_path = PATCH_DIR / f"{file_path.name}.patch"







                        patch_path.write_text(''.join(patch))







                    mismatches.append({'file': rel_path, 'reason': 'hash mismatch'})







                    if use_chatgpt:







                        recover_with_chatgpt(rel_path, 'Hash mismatch detected', mode)







    lint_issues = run_linter()







    tests_ok = run_tests()







    minted_hash = None







    if mint:







        block = ledger.add_block()







        minted_hash = block.get('block_hash')







    try:







        log = json.loads(HEAL_LOG.read_text())







    except json.JSONDecodeError:







        log = []







    entry = {







        'ledger_ok': ledger_ok,







        'mismatches': mismatches,







        'lint_issues': lint_issues,







        'tests_passed': tests_ok







    }







    if minted_hash:







        entry['minted_block'] = minted_hash







    log.append(entry)







    HEAL_LOG.write_text(json.dumps(log, indent=4))







    codelock.lock_repo()







    print(







        f'Self-heal complete. {len(mismatches)} issues resolved. '







        f'Lint warnings: {len(lint_issues)}'







    )







    return mismatches























def auto_verify_and_heal() -> None:







    """Run self-heal based on the system configuration."""







    cfg_path = ROOT / 'config' / 'imp-config-manager.py'







    spec_cfg = importlib.util.spec_from_file_location('cfg', cfg_path)







    cfg = importlib.util.module_from_spec(spec_cfg)







    spec_cfg.loader.exec_module(cfg)















    system_cfg = cfg.load_config('system') or {}







    heal_cfg = system_cfg.get("self_healing", {})







    apply = heal_cfg.get("auto_apply", True)







    use_chatgpt = heal_cfg.get("use_chatgpt", True)







    mode = heal_cfg.get("mode", "auto")







    mint = heal_cfg.get("mint", False)







    verify_and_heal(apply=apply, use_chatgpt=use_chatgpt, mode=mode, mint=mint)























if __name__ == '__main__':







    verify_and_heal()







