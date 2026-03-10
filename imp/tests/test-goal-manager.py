from pathlib import Path

import json

import importlib.util



ROOT = Path(__file__).resolve().parents[1]

MODULE = ROOT / 'core' / 'imp-goal-manager.py'

GOALS_FILE = ROOT / 'logs' / 'imp-goals.json'



spec = importlib.util.spec_from_file_location('gm', MODULE)

gm = importlib.util.module_from_spec(spec)

spec.loader.exec_module(gm)



print('Testing Goal Manager...')



# backup current goals

if GOALS_FILE.exists():

    with open(GOALS_FILE, 'r') as f:

        backup = json.load(f)

else:

    backup = []

    GOALS_FILE.write_text('[]')



# add new goal with custom priority

gm.add_new_goal(

    'Test offline goal',

    term='short-term',

    priority='high',

    mode='offline',

    category='testing',

)



with open(GOALS_FILE, 'r') as f:

    goals = json.load(f)

new_goal = goals[-1]

assert new_goal['priority'] == 'high'

assert new_goal['term'] == 'short-term'

assert new_goal['category'] == 'testing'

assert 'id' in new_goal and 'created_at' in new_goal



category_goals = gm.get_existing_goals(category='testing')

assert any(goal['id'] == new_goal['id'] for goal in category_goals)



summary = gm.summarize_categories()

assert summary.get('testing', 0) >= 1



# restore original

with open(GOALS_FILE, 'w') as f:

    json.dump(backup, f, indent=4)



print('Goal Manager Test Passed!')

