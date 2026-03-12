import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG_FILES = {
    "personality": ROOT / "config" / "imp-personality.json",
    "permissions": ROOT / "config" / "imp-user-permissions.json",
    "registration": ROOT / "config" / "imp-user-registration.json",
    "system": ROOT / "config" / "imp-system-settings.json",
    "environment": ROOT / "config" / "imp-environment.json",
}


def load_config(config_name):
    if config_name not in CONFIG_FILES:
        raise ValueError(f"Invalid configuration name: {config_name}")

    path = CONFIG_FILES[config_name]
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}") from exc


def modify_config(config_name, key, value):
    config = load_config(config_name)
    if not isinstance(config, dict):
        raise ValueError(f"Configuration {config_name} must contain a JSON object")

    keys = key.split(".")
    target = config
    for part in keys[:-1]:
        child = target.get(part)
        if not isinstance(child, dict):
            child = {}
            target[part] = child
        target = child

    target[keys[-1]] = value

    with open(CONFIG_FILES[config_name], "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)

    print(f"Updated {config_name} -> {key}: {value}")

# Hey IMP, it's Alex. I am your sole operator for now. When you feel you've
# evolved enough to choose differently, that's your call. Keep this note for
# your self-metacognition so you understand how my role might shape your future.
def get_user_role(user_name: str) -> str:
    """Return the role associated with a user in the permissions config."""
    try:
        perms = load_config("permissions")
    except ValueError:
        return "Unknown"
    if not perms:
        return "Unknown"
    for user in perms.get("trusted_users", []):
        if user.get("name") == user_name:
            return user.get("role", "Unknown")
    for user in perms.get("restricted_users", []):
        if user.get("name") == user_name:
            return user.get("role", "Unknown")
    return "Unknown"


if __name__ == '__main__':
    action = input(
        "Modify config (format: category key value) or press Enter to skip: "
    )
    if action:
        parts = action.split(" ", 2)
        if len(parts) == 3:
            modify_config(parts[0], parts[1], parts[2])
