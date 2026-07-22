import { useEffect, useState } from "react";
import { useOutletContext } from "react-router-dom";
import Plot from "react-plotly.js";
import { getPortfolioOverview } from "../api";
import "./Dashboard.css";

const BEHAVIORS = {
  Conservative: {
    desc: "Prefers stability and consistent returns. Comfortable with low to moderate volatility.",
    portfolio: "Bonds, dividend-yielding stocks, and stable ETFs.",
  },
  Moderate: {
    desc: "Balanced risk and reward approach. Comfortable with standard market fluctuations.",
    portfolio: "60% equities, 40% bonds and alternative assets.",
  },
  Aggressive: {
    desc: "Seeks high returns and prioritises growth. Can tolerate short-term losses and high volatility.",
    portfolio: "80-90% equities, crypto, and 10-20% fixed income.",
  },
};

const PLOTLY_MODEBAR_CONFIG = {
  displaylogo: false,
  modeBarButtonsToRemove: [
    "lasso2d", "select2d", "toggleSpikelines",
    "hoverCompareCartesian", "hoverClosestCartesian",
  ],
};

export default function Dashboard() {
  const { user } = useOutletContext();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    getPortfolioOverview()
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);

  if (error) {
    return (
      <div className="dashboard">
        <p className="error">{error}</p>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="dashboard">
        <p className="subtitle">Loading your portfolio…</p>
      </div>
    );
  }

  const behavior = BEHAVIORS[data.risk_profile];
  const curveDates = data.curve.map((p) => p.date);
  const curveValues = data.curve.map((p) => p.value);
  const preferences = data.profile.preferences?.length
    ? data.profile.preferences.join(", ")
    : "N/A";

  return (
    <div className="dashboard">
      <h1>Welcome back, {user.name}</h1>
      <p className="subtitle">Your personalized investment snapshot powered by AIPRS</p>

      {/* ── Portfolio Metrics ─────────────────────────────────────────── */}
      <section className="dash-section">
        <h2 className="dash-section-title">
          Portfolio Metrics
          <span className="dash-section-sub"> — {data.metrics_source}</span>
        </h2>
        <div className="metrics-grid">
          <div className="metric-card">
            <span className="metric-label">Total Return (1Y)</span>
            <span className="metric-value">{(data.total_return * 100).toFixed(1)}%</span>
          </div>
          <div className="metric-card">
            <span className="metric-label">Annualised Volatility</span>
            <span className="metric-value">{(data.ann_vol * 100).toFixed(1)}%</span>
          </div>
          <div className="metric-card">
            <span className="metric-label">Sharpe Ratio</span>
            <span className="metric-value">{data.sharpe.toFixed(2)}</span>
          </div>
        </div>
        <p className="dash-caption">
          These figures reflect realized 1-year performance of{" "}
          {data.metrics_available ? "your entered holdings" : "the static cluster benchmark"}.
          They may differ from the <i>optimized</i> allocation and expected return/volatility
          shown on the AI Recommendations page, which uses Modern Portfolio Theory rather than
          fixed cluster weights.
        </p>
      </section>

      {/* ── Portfolio Performance ─────────────────────────────────────── */}
      <section className="dash-section">
        <h2 className="dash-section-title">Portfolio Performance</h2>
        {data.curve.length > 0 ? (
          <Plot
            data={[
              {
                x: curveDates,
                y: curveValues,
                type: "scatter",
                mode: "lines",
                line: { color: "#F59E0B" },
              },
            ]}
            layout={{
              autosize: true,
              height: 400,
              margin: { l: 40, r: 20, t: 20, b: 40 },
              paper_bgcolor: "rgba(0,0,0,0)",
              plot_bgcolor: "rgba(0,0,0,0)",
              font: { family: "Inter", size: 12, color: "#E4E4E7" },
              xaxis: { type: "date", gridcolor: "rgba(255,255,255,0.04)" },
              yaxis: { tickformat: ".3f", gridcolor: "rgba(255,255,255,0.05)" },
              shapes: [
                {
                  type: "line", xref: "paper", x0: 0, x1: 1, y0: 1, y1: 1,
                  line: { color: "rgba(255,255,255,0.18)", dash: "dot" },
                },
              ],
            }}
            config={{ ...PLOTLY_MODEBAR_CONFIG, scrollZoom: true }}
            style={{ width: "100%" }}
            useResizeHandler
          />
        ) : (
          <p className="dash-caption">⚠️ Chart unavailable — market data could not be fetched.</p>
        )}
      </section>

      {/* ── Profile Summary ───────────────────────────────────────────── */}
      <section className="dash-section">
        <h2 className="dash-section-title">Profile Summary</h2>
        <div className="profile-grid">
          <div className="profile-col">
            <p><b>Name:</b> {data.profile.name}</p>
            <p><b>Age:</b> {data.profile.age}</p>
            <p><b>Income Range:</b> {data.profile.income_range}</p>
            <p><b>Risk Tolerance:</b> {data.profile.risk_tolerance}</p>
            <p><b>Investment Horizon:</b> {data.profile.investment_horizon}</p>
          </div>
          <div className="profile-col">
            <p><b>Experience Level:</b> {data.profile.experience}</p>
            <p><b>Primary Goals:</b> {data.profile.goals}</p>
            <p><b>Preferred Assets:</b> {preferences}</p>
            <div className="risk-badge-row">
              <span className="risk-badge-label">Risk Cluster</span>
              <span className="risk-badge" style={{ "--badge-color": data.badge_color }}>
                ● {data.risk_profile}
              </span>
            </div>
          </div>
        </div>
        {behavior && (
          <div className="behavior-box">
            <span className="behavior-label">Investor Behaviour</span>
            <p>{behavior.desc}</p>
            <span className="behavior-label">Ideal Portfolio</span>
            <p>{behavior.portfolio}</p>
          </div>
        )}
      </section>
    </div>
  );
}
