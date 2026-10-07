\# SupplyPrescript: Closed-Loop Prescriptive Analytics



Moves from "what will happen?" to "what should we do?". It predicts supply chain delays, prescribes the best actions with an optimizer, writes the manager's decision back to the database, and later compares the predicted cost with the actual cost to learn from it.



\## Architecture

\- \*\*Predictive model:\*\* XGBoost classifier (delay probability) and regressor (delay days)

\- \*\*Prescriptive solver:\*\* SciPy `linprog` with budget, max-delay and capacity constraints. It returns 3 options: Air Freight, Secondary Supplier (10% premium), Delay Launch

\- \*\*Write-back:\*\* FastAPI + PostgreSQL. "Execute Decision" INSERTs into the `decisions` table

\- \*\*Dashboard:\*\* React (Vite) with option cards and a Decision ROI view

\- \*\*Closed loop:\*\* `evaluate.py` compares predicted and actual cost, updates cost weights, and retrains XGBoost when the discrepancy is above a threshold

\- \*\*Governance:\*\* input validation in the API plus a data-quality circuit breaker that halts training on bad data



\## Setup

1\. Install Python, Node.js and PostgreSQL. Create the database: `CREATE DATABASE supplyprescript;`

2\. Set your password: `setx SP\_DB\_PASSWORD "your\_password"` (then open a new terminal)

3\. `python -m venv venv` then `venv\\Scripts\\activate` then `pip install -r requirements.txt`

4\. `python generate\_data.py` then `python train\_model.py`

5\. Start the API: `uvicorn api:app --reload`

6\. Start the dashboard: `cd dashboard`, `npm install`, `npm run dev`, open http://localhost:5173



\## Key scripts

| File | Purpose |

|---|---|

| `optimizer.py` | Linear-programming prescriptions |

| `audit\_optimizer.py` | Proves no recommendation breaks the budget |

| `api.py` | Predict, prescribe, execute (write-back), ROI, evaluate |

| `simulate\_decisions.py` | Simulates manager decisions |

| `evaluate.py` | Closed loop: compare, update weights, retrain |

| `data\_quality.py` | Data checks and circuit breaker |

| `test\_data\_quality.py` | Shows bad input is rejected |



\## Notes

\- Data is mock data. Real outcomes are simulated to stand in for invoices.

\- Great Expectations does not install on Python 3.14, so equivalent expectation-style checks are written in pandas.

