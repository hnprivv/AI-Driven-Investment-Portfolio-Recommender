import PpoSignalChart from "./PpoSignalChart";

const ACTION_COLORS = { BUY: "#22C55E", HOLD: "#F59E0B", SELL: "#EF4444" };
const ACTION_ICONS = { BUY: "▲", HOLD: "◆", SELL: "▼" };
const TONE_COLORS = { buy: "#22C55E", sell: "#EF4444", neutral: "#F59E0B" };

export default function PpoDetail({ detail, loading, error, onClose, currencyPrefix = "$" }) {
  return (
    <div className="chart-card ppo-detail">
      <div className="ppo-detail-header">
        <button type="button" className="ppo-detail-close" onClick={onClose}>
          ✕ Close
        </button>
      </div>

      {loading && <p className="subtitle">Running PPO inference…</p>}
      {error && <p className="error">{error}</p>}

      {detail && !loading && !error && (
        <>
          <div className="ppo-banner" style={{ "--action-color": ACTION_COLORS[detail.action] }}>
            <div>
              <div className="ppo-banner-label">Advisory Recommendation for {detail.symbol}</div>
              <div className="ppo-banner-action">
                {ACTION_ICONS[detail.action]} {detail.action}
              </div>
              <div className="ppo-banner-price">
                {currencyPrefix}
                {detail.price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                <span className={detail.chg_pct >= 0 ? "up" : "down"}>
                  {detail.chg_pct >= 0 ? "▲" : "▼"} {Math.abs(detail.chg_pct).toFixed(2)}%
                </span>
              </div>
              {detail.risk_note && <div className="ppo-banner-note">{detail.risk_note}</div>}
            </div>
            <div className="ppo-banner-confidence">
              <div className="dash-section-sub">Confidence</div>
              <div className="ppo-banner-confidence-value">{(detail.confidence * 100).toFixed(1)}%</div>
              <div className="ppo-confidence-meter">
                <div style={{ width: `${detail.confidence * 100}%` }} />
              </div>
            </div>
          </div>

          <div className="ppo-prob-section">
            <span className="dash-section-sub">Action probability distribution</span>
            <div className="ppo-prob-bar large">
              {["SELL", "HOLD", "BUY"].map(
                (a) =>
                  detail.probabilities[a] > 0.01 && (
                    <div key={a} style={{ width: `${detail.probabilities[a] * 100}%`, background: ACTION_COLORS[a] }}>
                      {(detail.probabilities[a] * 100).toFixed(0)}%
                    </div>
                  )
              )}
            </div>
          </div>

          <h3 className="dash-section-title">Key Market Signals</h3>
          <div className="ppo-indicator-grid">
            {detail.indicators.map((ind) => (
              <div key={ind.name} className="metric-card">
                <span className="metric-label">{ind.name}</span>
                <span className="metric-value">{ind.value}</span>
                <span className="metric-sub" style={{ color: TONE_COLORS[ind.tone] }}>
                  {ind.signal}
                </span>
              </div>
            ))}
          </div>

          <h3 className="dash-section-title">Price &amp; Signal History</h3>
          <PpoSignalChart chart={detail.chart} currencyPrefix={currencyPrefix} />

          {detail.hit_rate.directional_signals > 0 && (
            <div className="ppo-hitrate-grid">
              <div className="metric-card">
                <span className="metric-label">Directional Signals</span>
                <span className="metric-value">{detail.hit_rate.directional_signals}</span>
              </div>
              <div className="metric-card">
                <span className="metric-label">Correct Direction</span>
                <span className="metric-value">{detail.hit_rate.correct}</span>
              </div>
              <div className="metric-card">
                <span className="metric-label">Hit Rate</span>
                <span className="metric-value">{detail.hit_rate.hit_rate_pct.toFixed(1)}%</span>
                <span
                  className="metric-sub"
                  style={{ color: detail.hit_rate.hit_rate_pct > 50 ? "#22C55E" : "#EF4444" }}
                >
                  {detail.hit_rate.hit_rate_pct > 50 ? "above 50%" : "below 50%"}
                </span>
              </div>
              <div className="metric-card">
                <span className="metric-label">BUY / SELL / HOLD</span>
                <span className="metric-value">
                  {detail.hit_rate.buy_count} / {detail.hit_rate.sell_count} / {detail.hit_rate.hold_count}
                </span>
              </div>
            </div>
          )}

          <details className="ppo-explainer">
            <summary>How this recommendation was generated</summary>
            <p>
              <b>Agent type:</b> Proximal Policy Optimisation (PPO) Actor-Critic, trained on a 24-feature
              state — 16 market signals (returns, RSI, MACD, Bollinger position, EMA ratios, volatility,
              volume, ATR, Stochastic %K, day-of-week) plus 8 features encoding your risk profile.
            </p>
            <p>
              <b>Confidence threshold:</b> <code>0.50 + 0.10 × (1 − risk tolerance / 10)</code> — more
              conservative profiles require higher model confidence before a BUY/SELL signal is issued,
              falling back to HOLD otherwise.
            </p>
            <p>
              This is an AI-generated advisory signal for educational and research purposes only. It does
              not constitute financial advice, and AIPRS does not execute any real trades.
            </p>
          </details>
        </>
      )}
    </div>
  );
}
