import { useEffect, useState } from "react";

const API = "http://127.0.0.1:8000";

export default function Roi() {
  const [data, setData] = useState(null);
  const [msg, setMsg] = useState("");

  const load = async () => {
    const r = await fetch(`${API}/roi`);
    setData(await r.json());
  };
  useEffect(() => { load(); }, []);

  const evaluate = async () => {
    setMsg("Evaluating...");
    const r = await fetch(`${API}/evaluate`, { method: "POST" });
    const d = await r.json();
    setMsg(d.message
      ? d.message
      : `Evaluated ${d.evaluated} decisions. Cost bias ${(d.cost_bias * 100).toFixed(1)}%. ` +
        (d.retrained ? "Models were retrained." : "No retraining needed."));
    load();
  };

  const card = { flex: 1, border: "1px solid #ccc", borderRadius: 8, padding: 12 };

  return (
    <div>
      <h3>Decision ROI</h3>
      <button onClick={evaluate} style={{ padding: "8px 16px" }}>
        Run closed-loop evaluation
      </button>
      {msg && <p style={{ color: "green", fontWeight: "bold" }}>{msg}</p>}

      {!data || data.total === 0 ? <p>No evaluated decisions yet.</p> : (
        <>
          <div style={{ display: "flex", gap: 15, margin: "15px 0" }}>
            <div style={card}>Decisions evaluated<h2>{data.total}</h2></div>
            <div style={card}>Positive outcomes<h2>{data.success_rate}%</h2></div>
            <div style={card}>Avg predicted cost<h2>${data.avg_predicted_cost}</h2></div>
            <div style={card}>Avg actual cost<h2>${data.avg_actual_cost}</h2></div>
          </div>

          <h4>By option</h4>
          <table border="1" cellPadding="6" style={{ borderCollapse: "collapse", width: "100%" }}>
            <thead>
              <tr><th>Option</th><th>Times chosen</th><th>Success rate</th>
                  <th>Avg predicted</th><th>Avg actual</th></tr>
            </thead>
            <tbody>
              {data.by_option.map((o) => (
                <tr key={o.option}>
                  <td>{o.option}</td><td>{o.count}</td><td>{o.success_rate}%</td>
                  <td>${o.avg_predicted_cost}</td><td>${o.avg_actual_cost}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <h4>Success rate over time (batches of 20 decisions)</h4>
          {data.trend.map((t) => (
            <div key={t.batch} style={{ display: "flex", alignItems: "center", gap: 8, margin: "4px 0" }}>
              <span style={{ width: 80, fontSize: 13 }}>{t.batch}</span>
              <div style={{ background: "#4c8bf5", height: 18, width: `${t.success_rate * 4}px` }} />
              <span style={{ fontSize: 13 }}>{t.success_rate}%</span>
            </div>
          ))}
        </>
      )}
    </div>
  );
}