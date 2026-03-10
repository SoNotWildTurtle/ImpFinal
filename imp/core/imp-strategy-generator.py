import importlib.util
import json
from pathlib import Path


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

ROOT = Path(__file__).resolve().parents[1]
utils = _load("imp_utils", ROOT / "core" / "imp_utils.py")
read_json = utils.read_json
write_json = utils.write_json
resolve_text_generator = utils.resolve_text_generator
STRATEGY_FILE = ROOT / "logs" / "imp-strategy-plans.json"
LEARNING_FILE = ROOT / "logs" / "imp-learning-memory.json"

generator = resolve_text_generator("Strategy plan")


def generate_new_strategy():
    learning_data = read_json(LEARNING_FILE, [])


    prompt = f"""

    IMP is an evolving AI with autonomous learning.



    Past learning data:

    {json.dumps(learning_data, indent=4)}



    Generate a strategic plan to:

    - Expand IMP’s intelligence

    - Improve security measures

    - Enhance AI learning efficiency

    """



    response = generator(prompt, max_length=1500, num_return_sequences=1)
    new_strategy = response[0]["generated_text"] if response else "No strategy generated."

    write_json(STRATEGY_FILE, {"strategy": new_strategy, "status": "pending"})


    print("[+] IMP has generated a new strategic plan.")



if __name__ == "__main__":
    generate_new_strategy()
