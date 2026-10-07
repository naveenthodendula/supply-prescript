import json
import numpy as np
import pandas as pd
from sqlalchemy import text
from db import engine
from optimizer import CONFIG

rng = np.random.default_rng()

# The hidden "real world". The optimizer does NOT know these numbers.
TRUE_MULT = {"Air Freight": 1.20, "Secondary Supplier": 1.05, "Delay Launch": 0.95}

with engine.begin() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS actual_outcomes (
            decision_id INTEGER PRIMARY KEY,
            true_delay_days INTEGER,
            actual_cost FLOAT,
            actual_remaining_delay FLOAT,
            recorded_at TIMESTAMP DEFAULT now()
        )
    """))

df = pd.read_sql("""
    SELECT d.id, d.shipment_json, d.mix_json
    FROM decisions d
    LEFT JOIN actual_outcomes o ON o.decision_id = d.id
    WHERE d.evaluated = FALSE AND o.decision_id IS NULL
""", engine)

c = CONFIG
count = 0
with engine.begin() as conn:
    for _, r in df.iterrows():
        ship = json.loads(r["shipment_json"])
        mix = json.loads(r["mix_json"])
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
        conn.execute(text("""
            INSERT INTO actual_outcomes (decision_id, true_delay_days, actual_cost, actual_remaining_delay)
            VALUES (:id, :d, :cost, :left)
        """), {"id": int(r["id"]), "d": d, "cost": round(float(cost), 2), "left": round(float(left), 1)})
        count += 1

print("Recorded", count, "actual outcomes in the database.")