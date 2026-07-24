import { useState } from "react";
import PsxPpoPanel from "./PsxPpoPanel";
import UsPpoPanel from "./UsPpoPanel";
import "./PpoAdvisor.css";

export default function PpoAdvisor() {
  const [tab, setTab] = useState("US");
  const [refreshKey, setRefreshKey] = useState(0);
  const [refreshing, setRefreshing] = useState(false);

  function handleRefresh() {
    setRefreshing(true);
    setRefreshKey((k) => k + 1);
    setTimeout(() => setRefreshing(false), 500);
  }

  return (
    <div className="page-shell">
      <div className="page-shell-inner">
        <h1>PPO Advisors</h1>
        <p className="subtitle">
          Reinforcement-learning BUY / HOLD / SELL signals based on market indicators and your personal
          risk profile. <b>Advisory only — no trades are executed.</b>
        </p>

        <div className="market-header-row">
          <span className="subtitle" style={{ margin: 0 }}>
            Confidence and signals adapt to your saved risk profile.
          </span>
          <button className="refresh-btn" onClick={handleRefresh} disabled={refreshing}>
            {refreshing ? "Refreshing…" : "⟳ Refresh"}
          </button>
        </div>

        <div className="market-tabs">
          <button className={`market-tab ${tab === "US" ? "active" : ""}`} onClick={() => setTab("US")}>
            US Market
          </button>
          <button className={`market-tab ${tab === "PSX" ? "active" : ""}`} onClick={() => setTab("PSX")}>
            PSX Market
          </button>
        </div>

        {tab === "US" ? <UsPpoPanel refreshKey={refreshKey} /> : <PsxPpoPanel refreshKey={refreshKey} />}
      </div>
    </div>
  );
}
