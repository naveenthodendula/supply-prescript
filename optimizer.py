import json
import os
from scipy.optimize import linprog

# ---- Business constraints and cost parameters ----
CONFIG = {
    "budget": 20000,             # HARD limit: no option may cost more than this
    "max_delay_days": 10,        # remaining delay we can tolerate
    "air_capacity": 0.8,         # max share of the order that can go by air
    "sec_capacity": 0.7,         # max share the secondary supplier can cover
    "order_value": 120000,
    "air_cost_per_delay_day": 1071,   # 14-day delay -> about $15k
    "sec_premium": 0.10,              # 10% premium
    "launch_penalty_per_day": 900,
    "air_recovers_days": 12,
    "sec_recovers_days": 9,
}

WEIGHTS_FILE = "cost_weights.json"   # the closed loop will update this later
NAMES = ["Air Freight", "Secondary Supplier", "Delay Launch"]


def load_weights():
    if os.path.exists(WEIGHTS_FILE):
        with open(WEIGHTS_FILE) as f:
            return json.load(f)
    return {"air": 1.0, "secondary": 1.0, "delay": 1.0}


def prescribe(delay_days, budget=None):
    c = CONFIG
    budget = c["budget"] if budget is None else budget
    w = load_weights()
    d = float(delay_days)

    # Cost if 100% of the order used that option (scaled by learned weights)
    cost = [
        c["air_cost_per_delay_day"] * d * w["air"],
        c["order_value"] * c["sec_premium"] * w["secondary"],
        c["launch_penalty_per_day"] * d * w["delay"],
    ]
    # Days of delay left if 100% of the order used that option
    remaining = [
        max(d - c["air_recovers_days"], 0),
        max(d - c["sec_recovers_days"], 0),
        d,
    ]
    caps = [c["air_capacity"], c["sec_capacity"], 1.0]

    options = []
    for k in range(3):
        # Option k must carry at least 60% of the order (or its capacity)
        bounds = [(0, caps[i]) for i in range(3)]
        bounds[k] = (min(0.6, caps[k]), caps[k])

        res = linprog(
            c=cost,                                   # minimize total cost
            A_ub=[cost, remaining],                   # cost <= budget, delay <= max
            b_ub=[budget, c["max_delay_days"]],
            A_eq=[[1, 1, 1]], b_eq=[1],               # the whole order is covered
            bounds=bounds,
            method="highs",
        )
        if res.success:
            x = res.x
            options.append({
                "option": "ABC"[k],
                "name": NAMES[k],
                "mix": {NAMES[i]: round(float(x[i]), 3) for i in range(3)},
               "predicted_cost": round(float(sum(cost[i] * x[i] for i in range(3))), 2),
"remaining_delay_days": round(float(sum(remaining[i] * x[i] for i in range(3))), 1),
            })
        else:
            options.append({"option": "ABC"[k], "name": NAMES[k], "feasible": False})
    return options


if __name__ == "__main__":
    for o in prescribe(14):
        print(o)