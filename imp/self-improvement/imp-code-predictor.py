import os
import json
from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parents[1]
PERFORMANCE_LOG = ROOT / "logs" / "imp-performance.json"
PREDICTIONS_FILE = ROOT / "logs" / "imp-code-predictions.json"

spec_utils = importlib.util.spec_from_file_location("imp_utils", ROOT / "core" / "imp_utils.py")
imp_utils = importlib.util.module_from_spec(spec_utils)
spec_utils.loader.exec_module(imp_utils)

generator = imp_utils.resolve_text_generator("Code improvement forecast")


def get_performance_metrics():

    if not os.path.exists(PERFORMANCE_LOG):

        return None

    with open(PERFORMANCE_LOG, "r") as f:

        return json.load(f)



def predict_future_improvements():

    performance_data = get_performance_metrics()

    if not performance_data:

        print("[+] No performance data available yet.")

        return



    prompt = f"""

    IMP is an AI-driven evolving system that continuously enhances itself.



    Current system performance:

    {json.dumps(performance_data, indent=4)}



    Based on performance trends, predict:

    - What areas of the codebase need optimization

    - How computational efficiency can be improved

    - Where security enhancements may be required

    - Any upcoming challenges in AI self-development



    Provide structured recommendations for the next iteration of code improvements.

    """



    response = generator(prompt, max_length=1500, num_return_sequences=1)
    predictions = response[0]["generated_text"] if response else "No predictions generated."


    with open(PREDICTIONS_FILE, "w") as f:

        f.write(predictions)



    print("[+] IMP has predicted future improvements.")



if __name__ == "__main__":
    predict_future_improvements()
