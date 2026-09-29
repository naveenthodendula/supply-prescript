import random
from optimizer import prescribe

random.seed(1)
checked = 0
for _ in range(5000):
    delay = random.uniform(1, 30)
    budget = random.uniform(5000, 30000)
    for o in prescribe(delay, budget):
        if o.get("feasible", True):
            assert o["predicted_cost"] <= budget + 1e-6, f"VIOLATION: {o} budget={budget}"
            checked += 1

print(f"PASSED: {checked} recommendations checked, none exceeded the budget.")