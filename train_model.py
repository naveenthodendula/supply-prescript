import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, mean_absolute_error
from sqlalchemy import inspect
from xgboost import XGBClassifier, XGBRegressor
from db import engine

FEATURES = ["supplier_reliability", "distance_km", "port_congestion",
            "weather_risk", "order_qty", "month", "planned_lead_days"]

df = pd.read_sql("SELECT * FROM shipments", engine)

# Model 1: will it be delayed? (probability)
X_train, X_test, y_train, y_test = train_test_split(
    df[FEATURES], df["delayed"], test_size=0.2, random_state=1)
clf = XGBClassifier(n_estimators=200, max_depth=4, learning_rate=0.1)
clf.fit(X_train, y_train)
print("Classifier accuracy:", round(accuracy_score(y_test, clf.predict(X_test)), 3))

# Model 2: how many days? (delayed shipments + real observed outcomes)
d = df[df["delayed"] == 1]
if inspect(engine).has_table("observed_delays"):
    obs = pd.read_sql("SELECT * FROM observed_delays", engine)
    d = pd.concat([d, obs], ignore_index=True)

Xr_train, Xr_test, yr_train, yr_test = train_test_split(
    d[FEATURES], d["delay_days"], test_size=0.2, random_state=1)
reg = XGBRegressor(n_estimators=200, max_depth=4, learning_rate=0.1)
reg.fit(Xr_train, yr_train)
print("Regressor average error (days):", round(mean_absolute_error(yr_test, reg.predict(Xr_test)), 2))

joblib.dump(clf, "delay_classifier.pkl")
joblib.dump(reg, "delay_regressor.pkl")
print("Models saved.")