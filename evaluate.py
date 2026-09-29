import json
import subprocess
import sys
import numpy as np
import pandas as pd
from sqlalchemy import text
from db import engine
from optimizer import CONFIG, load_weights, WEIGHTS_FILE

rng = np.random.default_rng()

# The hidden "real world" (stands in for invoices and tracking data).
# The optimizer does NOT know these numbers. It must learn them.
TRUE_MULT = {"Air Freight": 1.20, "Secondary Supplier": 1.05, "Delay Launch": 0.95}

OPTION_TO_WEIGHT = {"A": "air", "B": "secondary", "C": "delay"}
LEARNING_RATE = 0.5
COST_BIAS_LIMIT = 0.05      # retrain if actual cost is off by more than 5% overall
DELAY_ERROR_LIMIT = 1.8     # or average delay error is above 1.8 days


def real_world_outcome(ship, mix):
    c = CONFIG
    extra = (10 * ship["port_congestion"] + 8 * ship["weather_risk"]
             + 15 * (1 - ship["supplier_reliability"]) + rng.normal(0, 1.5))
    d = max(int(round(extra)), 1)
    base = {
        "Air Freight": c["air_cost_per_delay_day"] * d,
        "Secondary Supplier": c["order_value"] * c["sec_premium"],
        "Delay Launch": c["launch_penalty_per_day"] * d,
    }
    remain = {
        "Air Freight": max(d - c["air_recovers_days"], 0),
        "Secondary Supplier": max(d - c["sec_recovers_days"], 0),
        "Delay Launch": d,
    }
    cost = sum(base[k] * TRUE_MULT[k] * rng.normal(1, 0.03) * mix.get(k, 0) for k in base)
    left = sum(remain[k] * mix.get(k, 0) for k in base)
    return d, round(float(cost), 2), round(float(left), 1)


def run_evaluation():
    df = pd.read_sql("SELECT * FROM decisions WHERE evaluated = FALSE", engine)
    if df.empty:
        print("No new decisions to evaluate.")
        return None

    records = []
    new_shipments = []
    for _, r in df.iterrows():
        ship = json.loads(r["shipment_json"])
        mix = json.loads(r["mix_json"])
        d_true, actual_cost, actual_left = real_world_outcome(ship, mix)
        records.append({
            "id": int(r["id"]), "option": r["option"],
            "pred_cost": float(r["predicted_cost"]), "actual_cost": actual_cost,
            "pred_delay": float(r["predicted_delay_days"]), "true_delay": d_true,
            "actual_left": actual_left,
        })
        new_shipments.append({**ship, "delay_days": d_true})

    res = pd.DataFrame(records)

    # 1) Write the real outcomes back to the database
    with engine.begin() as conn:
        for _, r in res.iterrows():
            conn.execute(text(
                "UPDATE decisions SET actual_cost=:ac, actual_delay_days=:ad, evaluated=TRUE WHERE id=:id"),
                {"ac": r["actual_cost"], "ad": r["actual_left"], "id": int(r["id"])})

    # 2) Measure the discrepancies
    cost_error = float((abs(res["actual_cost"] - res["pred_cost"]) / res["pred_cost"]).mean())
    cost_bias = abs(float(res["actual_cost"].sum() / res["pred_cost"].sum()) - 1)
    delay_error = float(abs(res["pred_delay"] - res["true_delay"]).mean())
    print(f"Evaluated {len(res)} decisions")
    print(f"  Average cost error : {cost_error*100:.1f}%")
    print(f"  Overall cost bias  : {cost_bias*100:.1f}%")
    print(f"  Average delay error: {delay_error:.2f} days")

    # 3) Adjust the optimizer's cost weights
    weights = load_weights()
    for letter, key in OPTION_TO_WEIGHT.items():
        part = res[res["option"] == letter]
        if part.empty:
            continue
        ratio = part["actual_cost"].sum() / part["pred_cost"].sum()
        old = weights[key]
        weights[key] = round(min(max(old * (1 + LEARNING_RATE * (ratio - 1)), 0.5), 2.0), 4)
        print(f"  Weight '{key}': {old} -> {weights[key]}  (actual/predicted = {ratio:.2f})")
    with open(WEIGHTS_FILE, "w") as f:
        json.dump(weights, f)

    # 4) Real observed delays become extra training data for the regressor
    pd.DataFrame(new_shipments).to_sql("observed_delays", engine, if_exists="append", index=False)

    # 5) Continuous learning: big discrepancy -> retrain XGBoost automatically
    retrained = cost_bias > COST_BIAS_LIMIT or delay_error > DELAY_ERROR_LIMIT
    if retrained:
        print("Discrepancy above limit -> retraining XGBoost...")
        subprocess.run([sys.executable, "train_model.py"], check=True)
    else:
        print("Discrepancy within limits -> no retraining needed.")

    return {"evaluated": len(res), "cost_error": cost_error, "cost_bias": cost_bias,
            "delay_error": delay_error, "retrained": retrained, "weights": weights}


if __name__ == "__main__":
    run_evaluation()