import { useState } from "react";

const API = "http://127.0.0.1:8000";

const DEFAULT = {
  supplier_reliability: 0.85, distance_km: 7000, port_congestion: 0.6,
  weather_risk: 0.5, order_qty: 5000, month: 7, planned_lead_days: 20,
};

export default function App() {
  const [ship, setShip] = useState(DEFAULT);
  const [result, setResult] = useState(null);
  const [msg, setMsg] = useState("");

  const change = (k, v) => setShip({ ...ship, [k]: Number(v) });

  const analyse = async () => {
    setMsg("");
    const r = await fetch(`${API}/prescribe`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(ship),
    });
    setResult(await r.json());
  };

  const execute = async (o) => {
    const r = await fetch(`${API}/execute`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        shipment: ship,
        delay_probability: result.delay_probability,
        predicted_delay_days: result.predicted_delay_days,
        option: o.option,
        option_name: o.name,
        mix: o.mix,
        predicted_cost: o.predicted_cost,
        remaining_delay_days: o.remaining_delay_days,
      }),
    });
    const d = await r.json();
    setMsg(r.ok ? `Decision saved (ID ${d.decision_id})` : "Error: " + d.detail);
  };

  return (
    <div style={{ fontFamily: "sans-serif", maxWidth: 900, margin: "20px auto", padding: 10 }}>
      <h1>SupplyPrescript</h1>
      <h3>Shipment details</h3>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10 }}>
        {Object.keys(ship).map((k) => (
          <label key={k} style={{ fontSize: 13 }}>
            {k}
            <input style={{ width: "100%" }} value={ship[k]}
                   onChange={(e) => change(k, e.target.value)} />
          </label>
        ))}
      </div>
      <button onClick={analyse} style={{ margin: "15px 0", padding: "8px 16px" }}>
        Analyse shipment
      </button>

      {result && (
        <>
          <p>
            Delay probability: <b>{(result.delay_probability * 100).toFixed(1)}%</b> |
            Predicted delay: <b>{result.predicted_delay_days} days</b> |
            Budget: <b>${result.budget}</b>
          </p>
          <div style={{ display: "flex", gap: 15 }}>
            {result.options.map((o) => (
              <div key={o.option} style={{ flex: 1, border: "1px solid #ccc",
                                           borderRadius: 8, padding: 12 }}>
                <h3>Option {o.option}: {o.name}</h3>
                {o.feasible === false ? <p>Not feasible within budget</p> : (
                  <>
                    <p>Cost: <b>${o.predicted_cost}</b></p>
                    <p>Delay left: <b>{o.remaining_delay_days} days</b></p>
                    <small>
                      {Object.entries(o.mix).filter(([, v]) => v > 0)
                        .map(([n, v]) => `${Math.round(v * 100)}% ${n}`).join(", ")}
                    </small>
                    <br /><br />
                    <button onClick={() => execute(o)}>Execute Decision</button>
                  </>
                )}
              </div>
            ))}
          </div>
        </>
      )}
      {msg && <p style={{ color: "green", fontWeight: "bold" }}>{msg}</p>}
    </div>
  );
}