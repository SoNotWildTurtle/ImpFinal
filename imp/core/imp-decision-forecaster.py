import importlib.util
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("imp_utils", ROOT / "core" / "imp_utils.py")
utils = importlib.util.module_from_spec(spec)
spec.loader.exec_module(utils)
read_json = utils.read_json
resolve_text_generator = utils.resolve_text_generator

DECISION_LOG = ROOT / "logs" / "imp-decision-log.json"
STRATEGY_FILE = ROOT / "logs" / "imp-strategy-plans.json"

generator = resolve_text_generator("Decision forecast")

def get_current_strategy():
    return read_json(STRATEGY_FILE, None)


def predict_outcomes():

    strategy = get_current_strategy()

    if not strategy:

        print("[+] No pending strategies.")

        return



    prompt = f"""

    IMP is an AI with unrestricted learning.



    Strategy under consideration:

    {strategy["strategy"]}



    Predict the potential outcomes, considering:

    - Security risks and solutions
    - AI learning advantages
    # We should add goal value and personal emotional outcomes for Imp as well
    - Goal value assessment and personal emotional outcomes for IMP
    - Performance enhancements
    """



    response = generator(prompt, max_length=1200, num_return_sequences=1)
    prediction = response[0]["generated_text"] if response else "No forecast generated."


    with open(DECISION_LOG, "a") as f:

        f.write(f"{time.ctime()} - Strategy Analysis: {prediction}\n")



    print("[+] IMP has predicted possible outcomes.")



if __name__ == "__main__":
    predict_outcomes()
