# SupplyPrescript: Closed-Loop Prescriptive Analytics

**SupplyPrescript** moves beyond *“what will happen?”* to *“what should we do?”*

It predicts supply chain delays, prescribes the best actions using an optimizer, writes the manager's decision back to the database, and later compares the predicted cost with the actual cost to learn from it.

---

## 🏗️ Architecture

SupplyPrescript follows a closed-loop prescriptive analytics architecture:

* **Predictive Model:** XGBoost classifier for delay probability and regressor for delay days
* **Prescriptive Solver:** SciPy `linprog` with budget, max-delay, and capacity constraints
* **Decision Options:** Returns 3 options:

  * Air Freight
  * Secondary Supplier (10% premium)
  * Delay Launch
* **Write-back:** FastAPI + PostgreSQL. **Execute Decision** INSERTs into the `decisions` table
* **Dashboard:** React (Vite) with option cards and a Decision ROI view
* **Closed Loop:** `evaluate.py` compares predicted and actual cost, updates cost weights, and retrains XGBoost when the discrepancy is above a threshold
* **Governance:** Input validation in the API plus a data-quality circuit breaker that halts training on bad data

---

## ⚙️ Setup

### 1. Install the Required Software

Install:

* Python
* Node.js
* PostgreSQL

Create the database:

```sql
CREATE DATABASE supplyprescript;
```

### 2. Set the Database Password

On Windows:

```cmd
setx SP_DB_PASSWORD "your_password"
```

Then open a new terminal.

### 3. Create the Python Environment

```cmd
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Generate Data and Train the Model

```cmd
python generate_data.py
python train_model.py
```

### 5. Start the API

```cmd
uvicorn api:app --reload
```

### 6. Start the Dashboard

Open another terminal:

```cmd
cd dashboard
npm install
npm run dev
```

Then open:

```text
http://localhost:5173
```

---

## 📂 Key Scripts

| File                    | Purpose                                                 |
| ----------------------- | ------------------------------------------------------- |
| `optimizer.py`          | Linear-programming prescriptions                        |
| `audit_optimizer.py`    | Proves no recommendation breaks the budget              |
| `api.py`                | Predict, prescribe, execute (write-back), ROI, evaluate |
| `simulate_decisions.py` | Simulates manager decisions                             |
| `evaluate.py`           | Closed loop: compare, update weights, retrain           |
| `data_quality.py`       | Data checks and circuit breaker                         |
| `test_data_quality.py`  | Shows bad input is rejected                             |

---

## 🔄 Closed-Loop Workflow

The project follows a continuous decision and learning cycle:

**Predict → Prescribe → Execute → Record → Evaluate → Update → Retrain**

1. The predictive model estimates the probability and number of days of a supply chain delay.
2. The prescriptive optimizer evaluates available actions under budget, delay, and capacity constraints.
3. The system returns three possible decisions:

   * Air Freight
   * Secondary Supplier
   * Delay Launch
4. The manager executes a decision through the dashboard.
5. The selected decision is written back to the PostgreSQL database.
6. `evaluate.py` compares the predicted cost with the actual cost.
7. Cost weights are updated when required.
8. XGBoost is retrained when the discrepancy exceeds the defined threshold.

---

## 🛡️ Governance & Data Quality

SupplyPrescript includes governance mechanisms to prevent poor-quality data from entering the training process.

* Input validation is implemented in the API.
* Data-quality checks validate incoming data.
* A **data-quality circuit breaker** halts training when bad data is detected.
* `test_data_quality.py` demonstrates that bad input is rejected.
* `audit_optimizer.py` verifies that recommendations do not break the budget constraint.

---

## 📊 Decision ROI

The React (Vite) dashboard provides:

* Prescriptive option cards
* Decision execution
* Decision ROI view

The ROI component allows predicted costs to be compared with actual outcomes as part of the closed-loop process.

---

## 📝 Notes

* Data is **mock data**.
* Real outcomes are simulated to stand in for invoices.
* Great Expectations does not install on Python 3.14, so equivalent expectation-style checks are written in pandas.

---

## 🚀 Project Goal

SupplyPrescript demonstrates how **predictive analytics can be combined with optimization, decision execution, governance, and feedback learning** to build a closed-loop prescriptive analytics system for supply chain decision-making.
