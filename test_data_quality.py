from pydantic import ValidationError
from api import Shipment

good = dict(supplier_reliability=0.85, distance_km=7000, port_congestion=0.6,
            weather_risk=0.5, order_qty=5000, month=7, planned_lead_days=20)

bad_cases = {
    "negative distance": {**good, "distance_km": -100},
    "reliability above 1": {**good, "supplier_reliability": 1.5},
    "month 13": {**good, "month": 13},
    "zero order quantity": {**good, "order_qty": 0},
}

Shipment(**good)
print("PASS: valid shipment accepted")
for name, payload in bad_cases.items():
    try:
        Shipment(**payload)
        print("FAIL:", name, "was accepted")
    except ValidationError:
        print("PASS:", name, "rejected")