from pathlib import Path
import importlib.util
import time


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CORE_DIR = Path(__file__).resolve().parent
utils = _load("imp_utils", CORE_DIR / "imp_utils.py")
read_json = utils.read_json
write_json = utils.write_json

ROOT = CORE_DIR.parent
QUEUE_FILE = ROOT / "logs" / "imp-message-queue.json"
MAX_QUEUE_SIZE = 1000


def send_message(channel: str, text: str, priority: str = "normal") -> None:
    """Append a message to the queue with an optional priority."""
    queue = read_json(QUEUE_FILE, [])
    queue.append({
        "channel": channel,
        "text": text,
        "priority": priority,
        "time": int(time.time()),
    })
    if len(queue) > MAX_QUEUE_SIZE:
        queue = queue[-MAX_QUEUE_SIZE:]
    write_json(QUEUE_FILE, queue)


def receive_messages(channel: str):
    """Retrieve and remove all messages for the given channel, sorted by priority."""
    queue = read_json(QUEUE_FILE, [])
    messages = [m for m in queue if m.get("channel") == channel]
    messages.sort(key=lambda m: (m.get("priority") != "high", m.get("time")))
    queue = [m for m in queue if m.get("channel") != channel]
    write_json(QUEUE_FILE, queue)
    return messages


def broadcast_message(channels, text: str, priority: str = "normal") -> None:
    """Send the same message to multiple channels."""
    for channel in channels:
        send_message(channel, text, priority)


if __name__ == "__main__":
    send_message("test", "Hello world")
    broadcast_message(["a", "b"], "Hi all", priority="high")
    print(receive_messages("test"))
