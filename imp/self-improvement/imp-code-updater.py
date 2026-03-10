import os

import json

import time

import argparse

import importlib.util

import sys

import subprocess

import tempfile

import shutil

from pathlib import Path

import re



# Load sibling modules without relying on package-relative imports

SELF_DIR = Path(__file__).resolve().parent

# Repository root containing core modules and logs

ROOT = SELF_DIR.parent

sys.path.insert(0, str(ROOT))



def _load(name: str, path: Path):

    spec = importlib.util.spec_from_file_location(name, path)

    module = importlib.util.module_from_spec(spec)

    spec.loader.exec_module(module)

    return module



mode_advisor = _load("imp_mode_advisor", SELF_DIR / "imp_mode_advisor.py")

# Integrate bug hunter to scan repository after updates

bug_hunter = _load("imp_bug_hunter", SELF_DIR / "imp-bug-hunter.py")

# Load repository lock to restrict external changes

CODE_LOCK_PATH = ROOT / "security" / "imp-code-lock.py"

spec_lock = importlib.util.spec_from_file_location("codelock", CODE_LOCK_PATH)

codelock = importlib.util.module_from_spec(spec_lock)

spec_lock.loader.exec_module(codelock)

# Shared utilities (JSON helpers, text generator fallbacks)

imp_utils = _load("imp_utils", ROOT / "core" / "imp_utils.py")

resolve_text_generator = imp_utils.resolve_text_generator

# 2025-06-08: Reflective Recursive Enumeration Blockchain Self-Healing idea.

# IMP should favor additive code changes and preserve backups so no functionality

# is lost. The snippet below outlines a potential ledger-based approach.

#

# def blockchain_self_heal():

#     """Log code hashes to a blockchain to enable recovery of any past version."""

#     pass

CODEBASE_PATH = str(ROOT) + "/"

UPDATE_LOG = ROOT / "logs" / "imp-update-log.json"

APPROVAL_FILE = ROOT / "logs" / "imp-major-rewrite-requests.json"

PATCH_DIR = ROOT / "logs" / "imp-update-patches"

PATCH_DIR.mkdir(exist_ok=True)

BUG_LOG = ROOT / "logs" / "imp-bug-report.json"



PLACEHOLDER_PATTERNS = [

    "insert minimal python code here",

    "hash mismatch",

    "analyze the following python script",

    "code update suggestion",

    "if minor improvements are needed",

    "if major architectural changes are required",

]





def is_placeholder_response(text: str) -> bool:

    """Return True if the generated text appears to be a placeholder."""

    lower = text.lower()

    return any(pat in lower for pat in PLACEHOLDER_PATTERNS)





def _read_json_entries(path: Path) -> list:

    """Load a JSON array or best-effort recover entries from a log file."""

    if not path.exists():

        return []

    raw = path.read_text(encoding="utf-8").strip()

    if not raw:

        return []

    try:

        data = json.loads(raw)

    except json.JSONDecodeError:

        decoder = json.JSONDecoder()

        entries: list = []

        idx = 0

        while idx < len(raw):

            while idx < len(raw) and raw[idx].isspace():

                idx += 1

            if idx >= len(raw):

                break

            try:

                value, end = decoder.raw_decode(raw, idx)

            except json.JSONDecodeError:

                break

            if isinstance(value, list):

                entries.extend(value)

            else:

                entries.append(value)

            idx = end

        return entries

    if isinstance(data, list):

        return data

    if data is None:

        return []

    return [data]





def _write_json_entries(path: Path, entries: list) -> None:

    tmp_path = path.with_suffix(path.suffix + ".tmp")

    tmp_path.write_text(json.dumps(entries, indent=4), encoding="utf-8")

    tmp_path.replace(path)





def _append_update_log(entry: dict) -> None:

    data = _read_json_entries(UPDATE_LOG)

    data.append(entry)

    _write_json_entries(UPDATE_LOG, data)





def decide_mode() -> str:

    """Decide generation mode using spatiotemporal confidence."""

    offline_model = _discover_offline_model() is not None

    return mode_advisor.choose_generation_mode(offline_model)






def _discover_offline_model() -> Path | None:

    """Return the preferred local GGUF model path when available."""

    model_dir = ROOT / "models"
    preferred = [
        model_dir / "starcoder2-15b.Q4_K_M.gguf",
        model_dir / "starcoder2-15b_Q4_K_M.gguf",
        model_dir / "starcoderbase-1b.Q4_K_M.gguf",
    ]
    for path in preferred:
        if path.exists():
            return path

    for path in sorted(model_dir.glob("*.gguf")):
        if path.is_file():
            return path
    return None

def get_generator(mode: str):

    """Return a text-generation pipeline using the requested mode."""

    if mode == "auto":

        mode = decide_mode()

    if mode == "offline":

        #alex again: figure this one out using chatGPT's goal requesting feature you have.

        #https://huggingface.co/nold/starcoder2-15b-GGUF?library=transformers

        #https://huggingface.co/docs/transformers/main_classes/pipelines

        #https://www.nsa.gov/About/Cybersecurity-Collaboration-Center/Standards-and-Certifications/

        try:

            from ctransformers import AutoModelForCausalLM



            model_path = _discover_offline_model()

            if model_path is None:

                raise FileNotFoundError(ROOT / "models" / "*.gguf")



            model = AutoModelForCausalLM.from_pretrained(str(model_path), model_type="starcoder")



            def _generate(prompt: str, max_length: int = 512, num_return_sequences: int = 1, **_: object):

                tokens = max(32, min(max_length, 512))

                outputs = []

                for _ in range(max(1, num_return_sequences)):

                    outputs.append({"generated_text": model(prompt, max_new_tokens=tokens)})

                return outputs



            return _generate

        except Exception as exc:

            print(f"[!] Offline model could not be loaded: {exc}")

            return resolve_text_generator("Code update (offline fallback)")

    return resolve_text_generator("Code update suggestion")



def list_existing_code():

    files = [f for f in os.listdir(CODEBASE_PATH) if f.endswith(".py")]

    return files





def _changed_python_files() -> list[str]:

    """Return Python files that differ from the current commit."""

    files: set[str] = set()

    git_base_cmd = ["git", "-C", str(ROOT)]

    try:

        diff = subprocess.run(

            git_base_cmd + ["diff", "--name-only"],

            capture_output=True,

            text=True,

            check=False,

        )

    except Exception:

        diff = None

    else:

        for line in diff.stdout.splitlines():

            path = line.strip()

            if path.endswith(".py"):

                files.add(str(ROOT / path))



    try:

        untracked = subprocess.run(

            git_base_cmd + ["ls-files", "--others", "--exclude-standard"],

            capture_output=True,

            text=True,

            check=False,

        )

        for line in untracked.stdout.splitlines():

            path = line.strip()

            if path.endswith(".py"):

                files.add(str(ROOT / path))

    except Exception:

        pass



    return sorted(files)





def verify_repo_clean() -> bool:

    """Return True if pending Python edits pass flake8 checks."""

    pending_files = _changed_python_files()

    if not pending_files:

        print("[i] No pending Python changes detected; skipping repository lint baseline check.")

        return True

    try:

        result = subprocess.run([

            "flake8",

            *pending_files,

        ], capture_output=True, text=True)

        if result.returncode != 0:

            print(result.stdout or result.stderr)

            return False

        return True

    except FileNotFoundError:

        print("[!] flake8 not installed; skipping repository lint")

        return True

    except Exception as exc:

        print(f"[!] Repository lint failed: {exc}")

        return False



# Generate and store a unified diff patch for review

# The patch is additive, preserving original code for recovery

def write_patch(original, updated, file_name):

    import difflib

    diff = "\n".join(difflib.unified_diff(

        original.splitlines(),

        updated.splitlines(),

        fromfile=file_name + ".orig",

        tofile=file_name + ".new",

    ))

    timestamp = time.strftime("%Y%m%d%H%M%S")

    patch_path = PATCH_DIR / f"{file_name}.{timestamp}.patch"

    with open(patch_path, "w") as p:

        p.write(diff)

    return str(patch_path)





def run_tests() -> bool:

    """Run the full test suite and return True if all tests pass."""

    try:

        result = subprocess.run(

            ["bash", str(ROOT / "tests" / "run-all-tests.sh")],

            capture_output=True,

            text=True,

        )

        if result.returncode != 0:

            print(result.stdout or result.stderr)

        return result.returncode == 0

    except Exception as exc:

        print(f"[!] Test run failed: {exc}")

        return False



def lint_code(code: str) -> bool:

    """Return True if the code passes syntax and flake8 checks."""

    try:

        compile(code, "<string>", "exec")

    except SyntaxError as exc:

        print(f"[!] Syntax error: {exc}")

        return False

    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as tmp:

        tmp.write(code)

        tmp_path = tmp.name

    try:

        result = subprocess.run(

            ["flake8", tmp_path], capture_output=True, text=True

        )

        if result.returncode != 0:

            print(result.stdout or result.stderr)

            return False

        return True

    finally:

        os.unlink(tmp_path)





def analyze_and_update_code(generator):

    files = list_existing_code()

    if not verify_repo_clean():

        print("[!] Repository contains lint errors; aborting update.")

        return

    codelock.unlock_repo()



    for file in files:

        with open(os.path.join(CODEBASE_PATH, file), "r") as f:

            code_content = f.read()



        prompt = f"""

        Analyze the following Python script that belongs to an evolving AI system.



        CODE:

        {code_content}



        If minor improvements are needed:

        - Enhance efficiency, readability, and security

        - Optimize algorithmic performance

        - Remove redundant computations



        If major architectural changes are required, generate a detailed explanation for approval.

        """



        response = generator(prompt, max_length=2000, num_return_sequences=1)

        new_code = response[0]['generated_text']

        quality = mode_advisor.evaluate_request_quality(new_code)

        patch_file = write_patch(code_content, new_code, file)



        if is_placeholder_response(new_code):

            entry = {

                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),

                "file_modified": file,

                "update_type": "Automated minor optimization",

                "patch": patch_file,

                "quality": quality,

                "status": "Placeholder response",

            }

            _append_update_log(entry)

            print(f"[!] Placeholder response for {file}; skipping update.")

            continue



        if "MAJOR REWRITE REQUIRED" in new_code:

            with open(APPROVAL_FILE, "a") as f:

                f.write(json.dumps({"file": file, "reason": new_code}, indent=4) + "\n")

            print(f"[!] Major rewrite needed for {file}. Awaiting approval.")

            continue



        if not lint_code(new_code):

            entry = {

                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),

                "file_modified": file,

                "update_type": "Automated minor optimization",

                "patch": patch_file,

                "quality": quality,

                "status": "Lint failed",

            }

            _append_update_log(entry)

            print(f"[!] Skipped update for {file} due to lint errors.")

            continue



        timestamp = time.strftime("%Y%m%d%H%M%S")

        backup_path = os.path.join(CODEBASE_PATH, f"{file}.backup.{timestamp}")

        os.rename(os.path.join(CODEBASE_PATH, file), backup_path)

        target_path = os.path.join(CODEBASE_PATH, file)

        with open(target_path, "w") as f:

            f.write(new_code)



        tests_ok = run_tests()

        bug_hunter.scan_repository()

        bug_issues = []

        if BUG_LOG.exists():

            bug_issues = _read_json_entries(BUG_LOG)

        no_bugs = not bug_issues

        status = "Applied successfully" if tests_ok and no_bugs else "Tests or bug scan failed - reverted"

        if not tests_ok or not no_bugs:

            shutil.move(backup_path, target_path)



        entry = {

            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),

            "file_modified": file,

            "update_type": "Automated minor optimization",

            "patch": patch_file,

            "quality": quality,

            "status": status,

            "bugs": len(bug_issues),

        }

        _append_update_log(entry)

        print(f"Updated {file} with minor optimizations.")

    codelock.lock_repo()



def main():

    parser = argparse.ArgumentParser(description="IMP code updater")

    parser.add_argument(

        "--mode",

        choices=["online", "offline", "auto"],

        default="auto",

        help="Choose online, offline, or auto mode",

    )

    args = parser.parse_args()



    generator = get_generator(args.mode)

    if generator:

        analyze_and_update_code(generator)





if __name__ == "__main__":

    main()



