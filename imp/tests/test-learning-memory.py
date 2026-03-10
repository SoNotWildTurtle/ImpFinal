from pathlib import Path
import json
import importlib.util
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / 'core' / 'imp-learning-memory.py'

spec = importlib.util.spec_from_file_location('lm', MODULE)
lm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lm)

print('Testing Learning Memory...')

with TemporaryDirectory() as tmp:
    tmp_path = Path(tmp)
    decisions_file = tmp_path / 'decisions.json'
    learning_file = tmp_path / 'learning.json'

    decisions = [
        {
            "timestamp": "2025-03-19T18:00:00Z",
            "decision": "Expand AI cluster",
            "reason": "Detected high CPU usage on main node",
            "predicted_outcome": "Increased efficiency, reduced processing lag",
            "plan": ["Provision new node", "Balance tasks"],
            "status": "completed",
        },
        {
            "timestamp": "2025-03-19T19:00:00Z",
            "decision": "Deny execution of unapproved script",
            "reason": "Unknown user attempted unauthorized access",
            "predicted_outcome": "Prevented potential security breach",
        },
    ]

    existing_entry = {
        "timestamp": "2025-03-18T10:00:00Z",
        "decision": "Expand AI cluster",
        "reason": "Detected high CPU usage on main node",
        "predicted_outcome": "Increased efficiency, reduced processing lag",
        "categories": ["performance"],
        "status": "completed",
    }

    decisions_file.write_text(json.dumps(decisions))
    learning_file.write_text(json.dumps([existing_entry]))

    original_decisions = lm.DECISIONS_FILE
    original_learning = lm.LEARNING_FILE

    try:
        lm.DECISIONS_FILE = decisions_file
        lm.LEARNING_FILE = learning_file

        lm.store_learnings()

        stored = json.loads(learning_file.read_text())
        assert len(stored) == 2
        latest = stored[-1]
        assert latest['decision'] == 'Deny execution of unapproved script'
        assert 'security' in latest['categories']
        assert latest['insight'].startswith('Deny execution of unapproved script')

        # running a second time should not duplicate entries
        lm.store_learnings()
        stored_again = json.loads(learning_file.read_text())
        assert len(stored_again) == 2

        recent = lm.get_recent_learnings(limit=2)
        assert len(recent) == 2
        assert recent[0]['decision'] in {entry['decision'] for entry in decisions}

        filtered_security = lm.filter_learnings('security')
        assert len(filtered_security) == 1
        assert filtered_security[0]['decision'] == 'Deny execution of unapproved script'

        filtered_performance = lm.filter_learnings(['performance'], status='completed')
        assert len(filtered_performance) == 1
        assert filtered_performance[0]['decision'] == 'Expand AI cluster'

        limited = lm.filter_learnings(['performance', 'security'], limit=1)
        assert len(limited) == 1
        assert limited[0]['decision'] == 'Deny execution of unapproved script'
    finally:
        lm.DECISIONS_FILE = original_decisions
        lm.LEARNING_FILE = original_learning

print('Learning Memory Test Passed!')
