import os
import argparse
import time
from pathlib import Path
from typing import List, Dict
import importlib.util
import sys

spec_utils = importlib.util.spec_from_file_location(
    "imp_utils", Path(__file__).resolve().parent / "imp_utils.py"
)
imp_utils = importlib.util.module_from_spec(spec_utils)
spec_utils.loader.exec_module(imp_utils)

try:
    import openai
    try:
        from openai import OpenAI as OpenAIClient
    except Exception:
        OpenAIClient = None
except Exception:
    openai = None
    OpenAIClient = None

# Track last request times for OpenAI models
OPENAI_LAST_REQUEST: Dict[str, float] = {}
# Approximate requests per minute; throttled to one quarter
OPENAI_RPM: Dict[str, int] = {
    "gpt-3.5-turbo": 60,
    "gpt-4": 40,
}

def decide_mode() -> str:
    if (openai is not None or OpenAIClient is not None) and os.getenv("OPENAI_API_KEY"):
        return "online"
    return "offline"

ROOT = Path(__file__).resolve().parents[1]
CHAT_LOG = ROOT / "logs" / "imp-chat-log.txt"
GOALS_FILE = ROOT / "logs" / "imp-goals.json"
NOTES_DIR = ROOT / "notes"

COMMAND_HELP: Dict[str, str] = {
    "/help": "Show this command list.",
    "/mode": "Display the current chat mode (online/offline).",
    "/evaluate": "Ask ChatGPT to evaluate current goals.",
    "/goals": "Show a summary of stored goals.",
    "/plans": "List queued control plans with risk context.",
    "/notes": "List available personal notes.",
    "/history": "Display recent chat history entries.",
    "/newgoal": "Generate and store a goal from ChatGPT.",
    "/autonomy": "Control governance (/autonomy status|history|run|force).",
}

_speech_path = ROOT / "core" / "imp-speech-to-text.py"
spec_speech = importlib.util.spec_from_file_location("imp_speech_to_text", _speech_path)
imp_speech_to_text = importlib.util.module_from_spec(spec_speech)
spec_speech.loader.exec_module(imp_speech_to_text)

_auth_path = ROOT / "security" / "imp-authenticator.py"
spec_auth = importlib.util.spec_from_file_location("imp_authenticator", _auth_path)
imp_authenticator = importlib.util.module_from_spec(spec_auth)
spec_auth.loader.exec_module(imp_authenticator)

AUTONOMY_LOG = ROOT / "logs" / "imp-autonomy-log.json"

try:
    _autonomy_path = ROOT / "core" / "imp-autonomy-controller.py"
    spec_autonomy = importlib.util.spec_from_file_location(
        "imp_autonomy_controller", _autonomy_path
    )
    imp_autonomy_controller = importlib.util.module_from_spec(spec_autonomy)
    sys.modules[spec_autonomy.name] = imp_autonomy_controller
    spec_autonomy.loader.exec_module(imp_autonomy_controller)
    AutonomyController = getattr(
        imp_autonomy_controller, "AutonomyController", None
    )
except Exception:  # pragma: no cover - autonomy controller missing
    imp_autonomy_controller = None
    AutonomyController = None


try:
    _control_path = ROOT / "core" / "imp-control-hub.py"
    spec_control = importlib.util.spec_from_file_location(
        "imp_control_hub", _control_path
    )
    imp_control_hub = importlib.util.module_from_spec(spec_control)
    sys.modules[spec_control.name] = imp_control_hub
    spec_control.loader.exec_module(imp_control_hub)
    ControlHub = getattr(imp_control_hub, "ControlHub", None)
except Exception:  # pragma: no cover - control hub unavailable
    imp_control_hub = None
    ControlHub = None


_goal_manager_path = ROOT / "core" / "imp-goal-manager.py"
spec_goal_manager = importlib.util.spec_from_file_location(
    "imp_goal_manager", _goal_manager_path
)
imp_goal_manager = importlib.util.module_from_spec(spec_goal_manager)
sys.modules[spec_goal_manager.name] = imp_goal_manager
spec_goal_manager.loader.exec_module(imp_goal_manager)


def _load_autonomy_entries() -> List[Dict[str, object]]:
    try:
        entries = imp_utils.read_json(AUTONOMY_LOG, [])
    except Exception:
        return []
    if isinstance(entries, list):
        return entries
    return []


def _format_autonomy_entry(entry: Dict[str, object]) -> List[str]:
    lines: List[str] = []
    timestamp = entry.get("timestamp", "unknown")
    status = entry.get("status", "unknown")
    lines.append(f"Autonomy cycle status: {status} @ {timestamp}")

    summary = entry.get("summary")
    if isinstance(summary, dict) and summary:
        goal_updates = summary.get("goal_updates")
        if isinstance(goal_updates, dict):
            count = goal_updates.get("count", "unknown")
            lines.append(f"  Goal updates: {count}")
            samples = goal_updates.get("samples")
            if isinstance(samples, list) and samples:
                lines.append(f"    sample: {samples[0]}")
        success_plan = summary.get("success_plan")
        if isinstance(success_plan, dict):
            actions = success_plan.get("actions", "unknown")
            lines.append(f"  Success actions: {actions}")
            goals_added = success_plan.get("goals_added")
            if isinstance(goals_added, int) and goals_added:
                lines.append(f"    goals added: {goals_added}")
            samples = success_plan.get("samples")
            if isinstance(samples, list) and samples:
                lines.append(f"    added sample: {samples[0]}")
            sample_action = success_plan.get("sample")
            if isinstance(sample_action, dict):
                goal_text = sample_action.get("goal") or "(goal unavailable)"
                priority = sample_action.get("priority", "?")
                term = sample_action.get("term", "?")
                lines.append(
                    f"    next action: {goal_text} [priority {priority}, {term}]"
                )
    bug_scan = entry.get("bug_scan")
    if isinstance(bug_scan, dict):
        issues = bug_scan.get("issues")
        if issues is not None:
            lines.append(f"  Bug scan issues: {issues}")
    self_heal = entry.get("self_heal")
    if isinstance(self_heal, dict):
        mismatches = self_heal.get("mismatches")
        if mismatches is not None:
            lines.append(f"  Self-heal mismatches: {mismatches}")
        if self_heal.get("repair_attempted"):
            lines.append("  Repair follow-up attempted")
    tests = entry.get("tests")
    if isinstance(tests, dict):
        success = tests.get("success")
        status_text = "passed" if success else "failed"
        duration = tests.get("duration")
        duration_text = f" in {duration:.1f}s" if isinstance(duration, (int, float)) else ""
        lines.append(f"  Test suite: {status_text}{duration_text}")
        if not success and tests.get("error"):
            lines.append(f"    error: {tests['error']}")
    if entry.get("forced"):
        lines.append("  Cycle executed in forced mode")
    git_info = entry.get("git")
    if isinstance(git_info, dict):
        clean = git_info.get("clean")
        changes = git_info.get("changes")
        lines.append(f"  Git clean: {clean} changes={changes}")
    return lines


def _print_autonomy_history(entries: List[Dict[str, object]], limit: int = 3) -> None:
    trimmed = entries[-limit:]
    print(f"Last {len(trimmed)} autonomy entries:")
    for entry in trimmed:
        for line in _format_autonomy_entry(entry):
            print(line)
        print("---")


def _format_plan_entry(entry: Dict[str, object]) -> List[str]:
    lines: List[str] = []
    plan = entry.get("plan", {}) if isinstance(entry, dict) else {}
    metadata = entry.get("metadata", {}) if isinstance(entry, dict) else {}
    plan_id = entry.get("id", "unknown") if isinstance(entry, dict) else "unknown"
    status = entry.get("status", "unknown") if isinstance(entry, dict) else "unknown"
    intent = plan.get("intent", "general") if isinstance(plan, dict) else "general"
    targets_value = plan.get("targets", []) if isinstance(plan, dict) else []
    if isinstance(targets_value, list) and targets_value:
        targets = ", ".join(str(target) for target in targets_value)
    else:
        targets = "(none)"

    confidence = plan.get("confidence") if isinstance(plan, dict) else None
    if isinstance(confidence, (int, float)):
        confidence_text = f"{confidence * 100:.0f}%" if 0 <= confidence <= 1 else f"{confidence:.2f}"
    else:
        confidence_text = "unknown"

    submitted_at = entry.get("submitted_at") if isinstance(entry, dict) else None
    if isinstance(submitted_at, (int, float)):
        submitted_text = time.strftime(
            "%Y-%m-%d %H:%M:%S", time.localtime(submitted_at)
        )
    else:
        submitted_text = "unknown"

    risk_score = metadata.get("risk_score") if isinstance(metadata, dict) else None
    if isinstance(risk_score, (int, float)):
        if risk_score >= 0.75:
            risk_label = "high"
        elif risk_score >= 0.5:
            risk_label = "moderate"
        else:
            risk_label = "low"
        risk_text = f"{risk_score:.2f} ({risk_label})"
    else:
        risk_text = "unknown"

    lines.append(
        f"{plan_id} [{status}] intent={intent} confidence={confidence_text} targets={targets}"
    )
    lines.append(f"  submitted: {submitted_text} | risk: {risk_text}")

    policy = plan.get("policy") if isinstance(plan, dict) else {}
    if isinstance(policy, dict):
        requirements = policy.get("requirements", [])
        if isinstance(requirements, list) and requirements:
            lines.append(
                "  requirements: "
                + ", ".join(str(requirement) for requirement in requirements)
            )
        if policy.get("denied"):
            lines.append("  awaiting manual override (policy denial)")

    requester = metadata.get("requester") if isinstance(metadata, dict) else None
    if requester:
        lines.append(f"  requested by: {requester}")

    notes = metadata.get("notes") if isinstance(metadata, dict) else None
    if notes:
        lines.append(f"  notes: {notes}")

    return lines


def _throttle(model: str) -> None:
    """Pause to respect OpenAI rate limits divided by four."""
    rpm = OPENAI_RPM.get(model, 60)
    interval = 60 / (rpm / 4)
    last = OPENAI_LAST_REQUEST.get(model, 0)
    elapsed = time.time() - last
    if elapsed < interval:
        time.sleep(interval - elapsed)
    OPENAI_LAST_REQUEST[model] = time.time()

SYSTEM_PROMPT = (
    "You are an assistant helping manage and evaluate goals for the IMP AI system."
)

# Offline text generation is skipped if transformers is unavailable

def load_notes() -> str:
    """Return concatenated text from all files in the notes folder."""
    if not NOTES_DIR.exists():
        return ""
    notes: List[str] = []
    for path in NOTES_DIR.glob("*.txt"):
        try:
            notes.append(path.read_text().strip())
        except Exception:
            continue
    return "\n".join(n for n in notes if n)


def list_note_titles() -> List[str]:
    """Return the filenames of personal notes."""
    if not NOTES_DIR.exists():
        return []
    return sorted(path.name for path in NOTES_DIR.glob("*.txt"))


def recent_chat_entries(limit: int = 5) -> List[str]:
    """Return the last ``limit`` conversation pairs from the chat log."""
    if not CHAT_LOG.exists():
        return []
    try:
        content = CHAT_LOG.read_text().strip()
    except Exception:
        return []
    if not content:
        return []
    blocks = [block for block in content.split("\n\n") if block.strip()]
    return blocks[-limit:]


def summarize_goals(limit: int = 5) -> List[str]:
    """Return summaries of the first ``limit`` goals."""
    if not GOALS_FILE.exists():
        return []
    goals = imp_utils.read_json(GOALS_FILE, [])
    summaries: List[str] = []
    for goal in goals[:limit]:
        text = goal.get("goal", "(missing goal text)")
        priority = goal.get("priority", "unknown")
        term = goal.get("term", "unspecified")
        summaries.append(f"- {text} (priority: {priority}, term: {term})")
    return summaries


def send_chatgpt_request(
    message: str,
    use_notes: bool = False,
    mode: str = "auto",
    history: List[Dict[str, str]] | None = None,
) -> str:
    """Return a response generated either with ChatGPT or a local model.

    If ``history`` is provided, it is treated as a list of previous
    conversation turns and will be appended with the latest user/assistant
    messages to maintain context across calls.
    """
    if mode == "auto":
        mode = decide_mode()

    if mode == "online" and (openai is not None or OpenAIClient is not None) and os.getenv("OPENAI_API_KEY"):
        api_key = os.getenv("OPENAI_API_KEY")
        try:
            _throttle("gpt-3.5-turbo")
            if use_notes:
                notes = load_notes()
                if notes:
                    message = f"Personal notes:\n{notes}\n\n{message}"
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            if history:
                messages.extend(history)
            messages.append({"role": "user", "content": message})
            if OpenAIClient is not None:
                client = OpenAIClient(api_key=api_key)
                resp = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=messages,
                )
                text = resp.choices[0].message.content.strip()
            else:
                openai.api_key = api_key
                resp = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=messages,
                )
                text = resp["choices"][0]["message"]["content"].strip()
        except Exception as exc:
            print(f"[!] ChatGPT request failed: {exc}")
            text = ""
    else:
        text = message.strip()

    if text:
        if history is not None:
            history.extend([
                {"role": "user", "content": message},
                {"role": "assistant", "content": text},
            ])
        with open(CHAT_LOG, "a") as log:
            log.write(f"USER: {message}\nASSISTANT: {text}\n\n")
    return text


def evaluate_current_goals(use_notes: bool = False, mode: str = "auto") -> str:
    """Ask ChatGPT to review existing goals and return the feedback."""
    if not GOALS_FILE.exists():
        return "No goals to evaluate."
    goals = imp_utils.read_json(GOALS_FILE, [])
    goal_text = "\n".join(f"- {g['goal']}" for g in goals)
    prompt = f"Please evaluate the following goals and suggest improvements:\n{goal_text}"
    return send_chatgpt_request(prompt, use_notes, mode)


def process_command(
    user_input: str,
    mode: str,
    history: List[Dict[str, str]],
    use_notes: bool,
) -> bool:
    """Handle operator slash commands. Returns True if handled."""

    if not user_input.startswith("/"):
        return False

    command, *rest = user_input.split(" ", 1)
    argument = rest[0].strip() if rest else ""

    if command == "/help":
        print("Available commands:")
        for name, desc in COMMAND_HELP.items():
            print(f"  {name:<10} {desc}")
        return True

    if command == "/mode":
        print(f"Current mode: {mode}")
        return True

    if command == "/evaluate":
        feedback = evaluate_current_goals(use_notes, mode)
        print(feedback if feedback else "No feedback available.")
        return True

    if command == "/goals":
        summaries = summarize_goals()
        if summaries:
            print("Tracked goals:")
            for line in summaries:
                print(line)
        else:
            print("No goals recorded.")
        return True

    if command == "/plans":
        if ControlHub is None:
            print("Control hub unavailable in this environment.")
            return True
        try:
            hub = ControlHub()
            plans = hub.list_plans()
        except Exception as exc:  # pragma: no cover - defensive path
            print(f"Unable to load plan queue: {exc}")
            return True
        if not plans:
            print("No plans queued.")
            return True
        print("Queued control plans:")
        for entry in plans:
            for line in _format_plan_entry(entry):
                print(line)
            print("---")
        return True

    if command == "/notes":
        titles = list_note_titles()
        if titles:
            print("Personal notes:")
            for title in titles:
                print(f"- {title}")
        else:
            print("No personal notes found.")
        return True

    if command == "/history":
        entries = recent_chat_entries()
        if entries:
            print("Recent chat history:")
            for block in entries:
                print(block)
                print("---")
        else:
            print("No chat history available.")
        return True

    if command == "/newgoal":
        if not argument:
            print("Usage: /newgoal <description>")
            return True

        reply = send_chatgpt_request(argument, use_notes, mode, history)
        if reply:
            imp_goal_manager.add_new_goal(
                reply,
                "long-term",
                "low",
                mode,
                category="general",
            )
            print("Goal stored from ChatGPT response.")
        else:
            print("Unable to generate a goal at this time.")
        return True

    if command == "/autonomy":
        arg = argument.strip().lower()
        entries = _load_autonomy_entries()
        if arg == "status":
            if not entries:
                print("No autonomy cycles recorded yet.")
                return True
            for line in _format_autonomy_entry(entries[-1]):
                print(line)
            return True

        if arg == "history":
            if not entries:
                print("No autonomy cycles recorded yet.")
                return True
            _print_autonomy_history(entries)
            return True

        if AutonomyController is None:
            print("Autonomy controller unavailable in this environment.")
            return True

        forced = arg == "force"
        if arg not in ("", "run", "force"):
            print("Unknown autonomy command. Use '/autonomy status', 'history', 'run', or 'force'.")
            return True

        try:
            controller = AutonomyController()
            controller.govern(force=forced)
            entries = _load_autonomy_entries()
            if not entries:
                print("Autonomy cycle executed but no log entry was recorded.")
                return True
            last_entry = entries[-1]
            if last_entry.get("status") == "skipped":
                print("Autonomy cycle skipped (cooldown active). Use '/autonomy force' to override.")
                return True
            print("Autonomy cycle executed.")
            for line in _format_autonomy_entry(last_entry):
                print(line)
        except Exception as exc:  # pragma: no cover - defensive path
            print(f"Autonomy cycle failed: {exc}")
        return True

    print(f"Unknown command: {command}")
    print('Type "/help" for available commands.')
    return True


def chat_loop(use_notes: bool = False, mode: str = "auto", phone: str | None = None, google_email: str | None = None):
    """Interactive chat loop with ChatGPT using conversational context."""
    if not sys.stdin.isatty():
        print("Interactive terminal required.")
        return
    prompt = (
        "Speak your question or type it. Press Enter on an empty line to exit."
    )
    print(prompt)
    history: List[Dict[str, str]] = []
    last_active = time.time()
    while True:
        if not imp_authenticator.idle_relog(last_active, phone, google_email):
            print("Re-authentication required.")
            break
        if chat_loop.use_speech:
            user_input = imp_speech_to_text.transcribe(offline=(mode != "online"))
        else:
            user_input = input("You: ").strip()
        if not user_input:
            break
        if process_command(user_input, mode, history, use_notes):
            last_active = time.time()
            continue
        reply = send_chatgpt_request(user_input, use_notes, mode, history)
        last_active = time.time()
        if reply:
            print(f"GPT: {reply}")
        else:
            print("(No response)")


chat_loop.use_speech = False

def main():
    parser = argparse.ArgumentParser(description="IMP Goal Chatbot")
    parser.add_argument(
        "--mode",
        choices=["online", "offline", "auto"],
        default="auto",
        help="Select online, offline, or auto mode.",
    )
    parser.add_argument(
        "--evaluate",
        action="store_true",
        help="Request ChatGPT to evaluate current goals and exit.",
    )
    parser.add_argument(
        "--use-notes",
        action="store_true",
        help="Include personal notes in ChatGPT requests.",
    )
    parser.add_argument(
        "--new-goal",
        metavar="TEXT",
        help="Send text to ChatGPT and store the resulting goal.",
    )
    parser.add_argument(
        "--term",
        choices=["short-term", "long-term"],
        default="long-term",
        help="Term for the new goal when using --new-goal",
    )
    parser.add_argument(
        "--category",
        default="general",
        help="Category to store alongside a new goal.",
    )
    parser.add_argument(
        "--speech",
        action="store_true",
        help="Capture input using speech-to-text",
    )
    parser.add_argument(
        "--google-email",
        help="Google account email for re-login",
    )
    parser.add_argument(
        "--phone",
        help="Phone number for Twilio verification",
    )
    args = parser.parse_args()

    mode = args.mode
    if mode == "auto":
        mode = decide_mode()

    if args.new_goal:
        reply = send_chatgpt_request(args.new_goal, args.use_notes, mode)
        if reply:
            imp_goal_manager.add_new_goal(
                reply,
                args.term,
                "low",
                mode,
                category=args.category,
            )
    elif args.evaluate:
        feedback = evaluate_current_goals(args.use_notes, mode)
        print(feedback)
    else:
        chat_loop.use_speech = args.speech
        chat_loop(args.use_notes, mode, args.phone, args.google_email)


if __name__ == "__main__":
    main()
