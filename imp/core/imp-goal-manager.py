import os

import time

import importlib.util

from pathlib import Path

from typing import Optional, Dict, List



openai = None





def _load(name, path):

    spec = importlib.util.spec_from_file_location(name, path)

    module = importlib.util.module_from_spec(spec)

    spec.loader.exec_module(module)

    return module





ROOT = Path(__file__).resolve().parents[1]

utils = _load("imp_utils", ROOT / "core" / "imp_utils.py")

read_json = utils.read_json

write_json = utils.write_json

GOALS_FILE = ROOT / "logs" / "imp-goals.json"

PRIORITIES = ["low", "medium", "high"]

DEFAULT_CATEGORY = "general"





def decide_mode() -> str:

    """Return 'online' if ChatGPT credentials are available, else 'offline'."""

    if os.getenv("OPENAI_API_KEY"):

        return "online"

    return "offline"





def _load_openai():

    """Import OpenAI lazily to avoid heavy startup costs."""

    global openai

    if openai is None:

        try:

            import openai as _openai

            openai = _openai

        except Exception:

            openai = None

    return openai



# Throttle tracking for OpenAI requests

OPENAI_LAST_REQUEST: Dict[str, float] = {}

OPENAI_RPM: Dict[str, int] = {

    "gpt-3.5-turbo": 60,

    "gpt-4": 40,

}



def _goal_id() -> str:

    """Return a simple unique identifier for a goal."""

    return str(int(time.time() * 1000))





def _timestamp() -> str:

    """Return the current time in ISO format."""

    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())



def _throttle(model: str) -> None:

    """Sleep to obey OpenAI rate limits divided by four."""

    rpm = OPENAI_RPM.get(model, 60)

    interval = 60 / (rpm / 4)

    last = OPENAI_LAST_REQUEST.get(model, 0)

    elapsed = time.time() - last

    if elapsed < interval:

        time.sleep(interval - elapsed)

    OPENAI_LAST_REQUEST[model] = time.time()



def generate_text(prompt: str, mode: str = "auto") -> str:

    """Generate text from ChatGPT when available, otherwise use the local model."""

    if mode == "auto":

        mode = decide_mode()

    if mode == "online" and _load_openai() is not None:

        api_key = os.getenv("OPENAI_API_KEY")

        if api_key:

            openai.api_key = api_key

            try:

                _throttle("gpt-3.5-turbo")

                resp = openai.ChatCompletion.create(

                    model="gpt-3.5-turbo",

                    messages=[{"role": "user", "content": prompt}],

                )

                return resp["choices"][0]["message"]["content"].strip()

            except Exception as exc:

                print(f"[!] ChatGPT request failed: {exc}")

    return prompt.strip()





def _normalize_goals(goals: List[Dict]) -> List[Dict]:

    """Ensure stored goals include a category."""

    normalized: List[Dict] = []

    updated = False

    for goal in goals:

        goal_copy = dict(goal)

        if not goal_copy.get("category"):

            goal_copy["category"] = DEFAULT_CATEGORY

            updated = True

        normalized.append(goal_copy)

    if updated:

        write_json(GOALS_FILE, normalized)

    return normalized





def get_existing_goals(

    term: Optional[str] = None,

    category: Optional[str] = None,

):

    """Return goals filtered by optional term or category."""

    goals = _normalize_goals(read_json(GOALS_FILE, []))

    if term:

        goals = [g for g in goals if g.get("term") == term]

    if category:

        goals = [g for g in goals if g.get("category") == category]

    return goals





def get_goals_by_category(category: str) -> List[Dict]:

    """Return all goals assigned to a category."""

    return get_existing_goals(category=category)





def summarize_categories() -> Dict[str, int]:

    """Return counts of goals per category."""

    summary: Dict[str, int] = {}

    for goal in get_existing_goals():

        cat = goal.get("category", DEFAULT_CATEGORY)

        summary[cat] = summary.get(cat, 0) + 1

    return summary





def update_goal_category(goal_id: str, category: Optional[str]) -> bool:

    """Update a goal's category. Returns True when a record changed."""

    goals = get_existing_goals()

    for goal in goals:

        if goal.get("id") == goal_id:

            goal["category"] = category or DEFAULT_CATEGORY

            write_json(GOALS_FILE, goals)

            return True

    return False





def suggest_improvement_goals() -> List[str]:

    """Derive goal suggestions from the code-map analysis report."""

    analysis_path = ROOT / "logs" / "imp-code-map-analysis.json"

    analysis = read_json(analysis_path, {})

    suggestions: List[str] = []

    for rel, info in analysis.items():

        if info.get("missing_test"):

            suggestions.append(f"Write tests for {rel}")

        if info.get("todos"):

            suggestions.append(f"Address TODOs in {rel}")

    return suggestions





def add_goals_from_code_map(

    term: str = "long-term",

    priority: str = "low",

    category: str = "code-quality",

) -> List[str]:

    """Append suggested goals based on code-map weaknesses."""

    suggestions = suggest_improvement_goals()

    if not suggestions:

        return []

    goals = get_existing_goals()

    for s in suggestions:

        goals.append(

            {

                "id": _goal_id(),

                "goal": s,

                "term": term,

                "priority": priority,

                "status": "pending",

                "created_at": _timestamp(),

                "category": category or DEFAULT_CATEGORY,

            }

        )

    write_json(GOALS_FILE, goals)

    return suggestions



def add_new_goal(

    user_input: str,

    term: str = "long-term",

    priority: str = "low",

    mode: str = "online",

    category: Optional[str] = None,

):

    """Add a new goal with the provided term and priority."""

    existing_goals = get_existing_goals()



    prompt = (

        f"User has provided the following input:\n{user_input}\n"

        "Convert this into a structured, actionable AI goal."

    )



    new_goal = generate_text(prompt, mode)



    if term not in ("short-term", "long-term"):

        term = "long-term"

    if priority not in PRIORITIES:

        priority = "low"



    existing_goals.append(

        {

            "id": _goal_id(),

            "goal": new_goal,

            "term": term,

            "priority": priority,

            "status": "pending",

            "created_at": _timestamp(),

            "category": category or DEFAULT_CATEGORY,

        }

    )



    write_json(GOALS_FILE, existing_goals)



    print(f"[+] New goal added: {new_goal}")





if __name__ == "__main__":

    import argparse



    parser = argparse.ArgumentParser(description="IMP Goal Manager")

    parser.add_argument(

        "--mode",

        choices=["online", "offline", "auto"],

        default="auto",

    )

    args = parser.parse_args()



    user_input = input("You: ")

    term_choice = input("Is this goal short-term or long-term? [s/l]: ").strip().lower()

    term = "short-term" if term_choice.startswith("s") else "long-term"

    pr_choice = input("Priority? [l/m/h]: ").strip().lower()

    priority_map = {"l": "low", "m": "medium", "h": "high"}

    priority = priority_map.get(pr_choice, "low")

    add_new_goal(user_input, term, priority, args.mode)

