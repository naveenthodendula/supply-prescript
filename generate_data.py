import numpy as np
import pandas as pd
from db import engine

rng = np.random.default_rng(42)
n = 5000

df = pd.DataFrame({
    "supplier_reliability": rng.uniform(0.6, 0.99, n).round(3),
    "distance_km": rng.integers(200, 12000, n),
    "port_congestion": rng.uniform(0, 1, n).round(3),
    "weather_risk": rng.uniform(0, 1, n).round(3),
    "order_qty": rng.integers(100, 10000, n),
    "month": rng.integers(1, 13, n),
})
df["planned_lead_days"] = (df["distance_km"] / 500 + rng.integers(3, 10, n)).round().astype(int)

# Hidden rule that makes delays depend on the features
z = (-6 + 4 * (1 - df["supplier_reliability"]) * 3
     + 2.5 * df["port_congestion"]
     + 2.0 * df["weather_risk"]
     + 1.5 * df["distance_km"] / 12000)
prob = 1 / (1 + np.exp(-z))
df["delayed"] = (rng.random(n) < prob).astype(int)

extra = (10 * df["port_congestion"] + 8 * df["weather_risk"]
         + 15 * (1 - df["supplier_reliability"]) + rng.normal(0, 1.5, n))
df["delay_days"] = np.where(df["delayed"] == 1, np.clip(extra.round(), 1, None), 0).astype(int)

df.to_sql("shipments", engine, if_exists="replace", index=False)
print("Inserted", len(df), "shipments. Delay rate:", round(df["delayed"].mean(), 2))