import json
import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import text

from db import engine
from optimizer import prescribe, CONFIG

FEATURES = ["supplier_reliability", "distance_km", "port_congestion",
            "weather_risk", "order_qty", "month", "planned_lead_days"]

clf = joblib.load("delay_classifier.pkl")
reg = joblib.load("delay_regressor.pkl")

# Create the write-back table if it does not exist
with engine.begin() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS decisions (
            id SERIAL PRIMARY KEY,
            created_at TIMESTAMP DEFAULT now(),
            shipment_json TEXT,
            delay_probability FLOAT,
            predicted_delay_days FLOAT,
            option CHAR(1),
            option_name TEXT,
            mix_json TEXT,
            predicted_cost FLOAT,
            remaining_delay_days FLOAT,
            actual_cost FLOAT,
            actual_delay_days FLOAT,
            evaluated BOOLEAN DEFAULT FALSE
        )
    """))

app = FastAPI(title="SupplyPrescript")
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])


class Shipment(BaseModel):
    supplier_reliability: float
    distance_km: int
    port_congestion: float
    weather_risk: float
    order_qty: int
    month: int
    planned_lead_days: int


class Decision(BaseModel):
    shipment: Shipment
    delay_probability: float
    predicted_delay_days: float
    option: str
    option_name: str
    mix: dict
    predicted_cost: float
    remaining_delay_days: float


def run_prediction(s: Shipment):
    X = pd.DataFrame([s.model_dump()])[FEATURES]
    prob = float(clf.predict_proba(X)[0][1])
    days = max(float(reg.predict(X)[0]), 0.0)
    return round(prob, 3), round(days, 1)


@app.post("/predict")
def predict(s: Shipment):
    prob, days = run_prediction(s)
    return {"delay_probability": prob, "predicted_delay_days": days}


@app.post("/prescribe")
def prescribe_endpoint(s: Shipment):
    prob, days = run_prediction(s)
    return {
        "delay_probability": prob,
        "predicted_delay_days": days,
        "budget": CONFIG["budget"],
        "options": prescribe(days),
    }


@app.post("/execute")
def execute(d: Decision):
    # Safety check: never write a decision that breaks the hard budget
    if d.predicted_cost > CONFIG["budget"]:
        raise HTTPException(400, "Decision exceeds the budget limit")
    with engine.begin() as conn:
        row = conn.execute(text("""
            INSERT INTO decisions
              (shipment_json, delay_probability, predicted_delay_days, option,
               option_name, mix_json, predicted_cost, remaining_delay_days)
            VALUES
              (:ship, :prob, :days, :opt, :name, :mix, :cost, :rem)
            RETURNING id
        """), {
            "ship": json.dumps(d.shipment.model_dump()),
            "prob": d.delay_probability,
            "days": d.predicted_delay_days,
            "opt": d.option,
            "name": d.option_name,
            "mix": json.dumps(d.mix),
            "cost": d.predicted_cost,
            "rem": d.remaining_delay_days,
        }).fetchone()
    return {"status": "saved", "decision_id": row[0]}


@app.get("/decisions")
def list_decisions():
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT id, created_at, option, option_name, predicted_cost, "
            "actual_cost, evaluated FROM decisions ORDER BY id DESC LIMIT 50"
        )).mappings().all()
    return [dict(r) for r in rows]



@app.get("/roi")
def roi():
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT id, option, predicted_cost, actual_cost, actual_delay_days "
            "FROM decisions WHERE evaluated = TRUE ORDER BY id")).mappings().all()
    if not rows:
        return {"total": 0}

    budget = CONFIG["budget"]
    max_delay = CONFIG["max_delay_days"]

    def ok(r):
        return r["actual_cost"] <= budget and r["actual_delay_days"] <= max_delay

    by_option = []
    for letter in "ABC":
        part = [r for r in rows if r["option"] == letter]
        if part:
            by_option.append({
                "option": letter,
                "count": len(part),
                "success_rate": round(100 * sum(ok(r) for r in part) / len(part), 1),
                "avg_predicted_cost": round(sum(r["predicted_cost"] for r in part) / len(part), 2),
                "avg_actual_cost": round(sum(r["actual_cost"] for r in part) / len(part), 2),
            })

    trend = []
    for i in range(0, len(rows), 20):
        chunk = rows[i:i + 20]
        trend.append({
            "batch": f"{i + 1}-{i + len(chunk)}",
            "success_rate": round(100 * sum(ok(r) for r in chunk) / len(chunk), 1),
        })

    return {
        "total": len(rows),
        "success_rate": round(100 * sum(ok(r) for r in rows) / len(rows), 1),
        "avg_predicted_cost": round(sum(r["predicted_cost"] for r in rows) / len(rows), 2),
        "avg_actual_cost": round(sum(r["actual_cost"] for r in rows) / len(rows), 2),
        "by_option": by_option,
        "trend": trend,
    }


@app.post("/evaluate")
def evaluate_now():
    global clf, reg
    from evaluate import run_evaluation
    result = run_evaluation()
    if result is None:
        return {"message": "No new decisions to evaluate."}
    # reload models in case they were retrained
    clf = joblib.load("delay_classifier.pkl")
    reg = joblib.load("delay_regressor.pkl")
    return result