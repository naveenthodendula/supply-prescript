import json
import random
import joblib
import numpy as np
import pandas as pd
from sqlalchemy import text
from db import engine
from optimizer import prescribe

FEATURES = ["supplier_reliability", "distance_km", "port_congestion",
            "weather_risk", "order_qty", "month", "planned_lead_days"]

clf = joblib.load("delay_classifier.pkl")
reg = joblib.load("delay_regressor.pkl")
rng = np.random.default_rng()

count = 0
while count < 60:
    s = {
        "supplier_reliability": round(float(rng.uniform(0.6, 0.99)), 3),
        "distance_km": int(rng.integers(200, 12000)),
        "port_congestion": round(float(rng.uniform(0, 1)), 3),
        "weather_risk": round(float(rng.uniform(0, 1)), 3),
        "order_qty": int(rng.integers(100, 10000)),
        "month": int(rng.integers(1, 13)),
    }
    s["planned_lead_days"] = int(round(s["distance_km"] / 500 + rng.integers(3, 10)))

    X = pd.DataFrame([s])[FEATURES]
    prob = float(clf.predict_proba(X)[0][1])
    days = max(float(reg.predict(X)[0]), 0.0)
    if days < 3:
        continue

    options = [o for o in prescribe(days) if o.get("feasible", True)]
    if not options:
        continue
    pick = random.choices(options, weights=[{"A": 5, "B": 3, "C": 2}[o["option"]] for o in options])[0]

    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO decisions
              (shipment_json, delay_probability, predicted_delay_days, option,
               option_name, mix_json, predicted_cost, remaining_delay_days)
            VALUES (:ship, :prob, :days, :opt, :name, :mix, :cost, :rem)
        """), {
            "ship": json.dumps(s), "prob": round(prob, 3), "days": round(days, 1),
            "opt": pick["option"], "name": pick["name"], "mix": json.dumps(pick["mix"]),
            "cost": pick["predicted_cost"], "rem": pick["remaining_delay_days"],
        })
    count += 1

print("Inserted", count, "simulated manager decisions.")