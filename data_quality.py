import pandas as pd
from sqlalchemy import inspect
from db import engine

RANGES = {
    "supplier_reliability": (0, 1),
    "distance_km": (1, 25000),
    "port_congestion": (0, 1),
    "weather_risk": (0, 1),
    "order_qty": (1, 100000),
    "month": (1, 12),
    "planned_lead_days": (1, 200),
    "delay_days": (0, 60),
}


def check_table(name, min_rows):
    df = pd.read_sql(f"SELECT * FROM {name}", engine)
    problems = []
    if len(df) < min_rows:
        problems.append(f"{name}: only {len(df)} rows (need {min_rows})")
    if df.isnull().any().any():
        problems.append(f"{name}: contains missing values")
    for col, (lo, hi) in RANGES.items():
        if col in df.columns:
            bad = int(((df[col] < lo) | (df[col] > hi)).sum())
            if bad:
                problems.append(f"{name}.{col}: {bad} values outside {lo}..{hi}")
    if name == "shipments":
        rate = df["delayed"].mean()
        if not 0.05 <= rate <= 0.95:
            problems.append(f"shipments: delay rate {rate:.2f} looks wrong")
    return problems


def check_or_halt():
    problems = check_table("shipments", 1000)
    if inspect(engine).has_table("observed_delays"):
        problems += check_table("observed_delays", 1)
    if problems:
        print("DATA QUALITY FAILED - training halted:")
        for p in problems:
            print("  -", p)
        raise SystemExit(1)
    print("Data quality: PASSED")


if __name__ == "__main__":
    check_or_halt()