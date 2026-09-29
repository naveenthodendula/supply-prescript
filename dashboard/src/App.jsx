import { useState } from "react";
import Prescribe from "./Prescribe.jsx";
import Roi from "./Roi.jsx";

export default function App() {
  const [tab, setTab] = useState("prescribe");
  return (
    <div style={{ fontFamily: "sans-serif", maxWidth: 900, margin: "20px auto", padding: 10 }}>
      <button onClick={() => setTab("prescribe")} style={{ marginRight: 8, padding: "6px 14px" }}>
        Prescriptions
      </button>
      <button onClick={() => setTab("roi")} style={{ padding: "6px 14px" }}>
        Decision ROI
      </button>
      <hr />
      {tab === "prescribe" ? <Prescribe /> : <Roi />}
    </div>
  );
}