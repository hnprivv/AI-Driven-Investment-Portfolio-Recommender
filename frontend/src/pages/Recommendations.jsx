import { useEffect, useState } from "react";
import Plot from "react-plotly.js";
import { getRecommendations } from "../api";
import "./Recommendations.css";

const ALLOCATION_COLORS = ["#B45309", "#D97706", "#F59E0B", "#FCD34D"];

const PLOTLY_MODEBAR_CONFIG = {
  displaylogo: false,
  modeBarButtonsToRemove: [
    "lasso2d", "select2d", "toggleSpikelines",
    "hoverCompareCartesian", "hoverClosestCartesian",
  ],
};

export default function Recommendations() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    getRecommendations()
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);

  if (error) {
    return (
      <div className="page-shell">
        <div className="page-shell-inner">
          <p className="error">{error}</p>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="page-shell">
        <div className="page-shell-inner">
          <p className="subtitle">Optimizing your portfolio allocation…</p>
        </div>
      </div>
    );
  }

  const assets = Object.keys(data.allocation);
  const percentages = Object.values(data.allocation);

  return (
    <div className="page-shell">
      <div className="page-shell-inner">
        <h1>AI Recommendations</h1>
        <p className="subtitle">Your personalized portfolio strategy, powered by Modern Portfolio Theory</p>

        {/* ── Optimized Portfolio ────────────────────────────────────────── */}
        <section className="dash-section">
          <h2 className="dash-section-title">Your Optimized Portfolio</h2>
          <p className="dash-caption" style={{ margin: "0 0 16px" }}>
            Based on your risk profile and Modern Portfolio Theory, our engine suggests this allocation:
          </p>

          <div className="recs-grid">
            <div className="chart-card">
              <Plot
                data={[
                  {
                    type: "bar",
                    x: assets,
                    y: percentages,
                    marker: { color: ALLOCATION_COLORS },
                  },
                ]}
                layout={{
                  autosize: true,
                  height: 300,
                  margin: { l: 40, r: 10, t: 10, b: 40 },
                  paper_bgcolor: "rgba(0,0,0,0)",
                  plot_bgcolor: "rgba(0,0,0,0)",
                  font: { family: "Inter, system-ui, sans-serif", size: 12, color: "#E4E4E7" },
                  showlegend: false,
                  yaxis: { gridcolor: "rgba(255,255,255,0.06)", ticksuffix: "%" },
                  xaxis: { gridcolor: "rgba(255,255,255,0.04)" },
                  transition: { duration: 500, easing: "cubic-in-out" },
                }}
                config={PLOTLY_MODEBAR_CONFIG}
                style={{ width: "100%" }}
                useResizeHandler
              />
              {!data.mpt_available && (
                <p className="dash-caption">
                  ⚠️ Live data unavailable — showing illustrative allocation for your risk profile.
                </p>
              )}
            </div>

            <div className="strategy-card">
              <span className="strategy-label">Strategy</span>
              <h3 className="strategy-title">{data.strategy_title}</h3>
              <p className="strategy-desc">{data.strategy_desc}</p>
              <div className="strategy-metrics">
                <div className="strategy-stat">
                  <span className="metric-label">Expected Annual Return</span>
                  <span className="metric-value">
                    {data.exp_return !== null ? `${(data.exp_return * 100).toFixed(1)}%` : "N/A"}
                  </span>
                </div>
                <div className="strategy-stat">
                  <span className="metric-label">Volatility Risk</span>
                  <span className="metric-value">{data.vol_label}</span>
                  {data.exp_vol !== null && (
                    <span className="strategy-sub">{(data.exp_vol * 100).toFixed(1)}% annualised</span>
                  )}
                </div>
              </div>
            </div>
          </div>

          <p className="dash-caption">
            This is an <i>optimized</i> allocation computed with Modern Portfolio Theory for your risk
            profile — it may differ from the realized performance shown on the Overview page, which
            reflects your actual holdings (or the static cluster benchmark) rather than this optimized mix.
          </p>
        </section>

        <div className="dash-divider"><span>◆</span></div>

        {/* ── Community Insights ────────────────────────────────────────── */}
        <section className="dash-section">
          <h2 className="dash-section-title">💡 Trending with Investors Like You</h2>
          <p className="dash-caption" style={{ margin: "0 0 16px" }}>
            These assets are popular among other investors who share your risk profile and financial goals.
          </p>

          {data.peer_recs.length > 0 ? (
            <div className="peer-grid">
              {data.peer_recs.map((r) => (
                <div key={r.asset} className="metric-card peer-card">
                  <h3 className="peer-asset">{r.asset}</h3>
                  <p className="peer-count">
                    Held by <b>{r.count}</b> of your peers
                  </p>
                  <div className="peer-bar-track">
                    <div className="peer-bar-fill" style={{ width: `${r.pct}%` }} />
                  </div>
                  <span className="peer-pct">{r.pct}% of peer popularity</span>
                </div>
              ))}
            </div>
          ) : data.peer_status === "all_invested" ? (
            <div className="info-box">
              You are already invested in all the top assets for your profile! You are following the trend.
            </div>
          ) : (
            <div className="info-box">
              {data.peer_status_message || "Could not generate insights."} Start adding preferences to
              your profile to unlock community insights!
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
