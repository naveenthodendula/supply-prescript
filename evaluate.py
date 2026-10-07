import json
import subprocess
import sys
import pandas as pd
from sqlalchemy import text, inspect
from db import engine
from optimizer import load_weights, WEIGHTS_FILE

OPTION_TO_WEIGHT = {"A": "air", "B": "secondary", "C": "delay"}
LEARNING_RATE = 0.5
COST_BIAS_LIMIT = 0.05      # retrain if actual cost is off by more than 5% overall
DELAY_ERROR_LIMIT = 1.8     # or average delay error is above 1.8 days


def run_evaluation():
    if not inspect(engine).has_table("actual_outcomes"):
        print("No actual outcomes recorded yet.")
        return None

    # Decisions that have an actual outcome stored in the database
    df = pd.read_sql("""
        SELECT d.id, d.option, d.shipment_json, d.predicted_cost,
               d.predicted_delay_days,
               o.true_delay_days, o.actual_cost AS outcome_cost,
               o.actual_remaining_delay
        FROM decisions d
        JOIN actual_outcomes o ON o.decision_id = d.id
        WHERE d.evaluated = FALSE
    """, engine)
    if df.empty:
        print("No new decisions to evaluate.")
        return None

    records = []
    new_shipments = []
    for _, r in df.iterrows():
        ship = json.loads(r["shipment_json"])
        records.append({
            "id": int(r["id"]), "option": r["option"],
            "pred_cost": float(r["predicted_cost"]),
            "actual_cost": float(r["outcome_cost"]),
            "pred_delay": float(r["predicted_delay_days"]),
            "true_delay": float(r["true_delay_days"]),
            "actual_left": float(r["actual_remaining_delay"]),
        })
        new_shipments.append({**ship, "delay_days": int(r["true_delay_days"])})

    res = pd.DataFrame(records)

    # 1) Write the evaluation result back onto the decisions
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