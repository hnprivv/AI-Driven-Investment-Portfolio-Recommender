const ACTION_COLORS = { BUY: "#22C55E", HOLD: "#F59E0B", SELL: "#EF4444" };
const ACTION_ICONS = { BUY: "▲", HOLD: "◆", SELL: "▼" };
const ORDER = { BUY: 0, HOLD: 1, SELL: 2 };

export default function PpoWatchlist({ items, onSelect, selected, currencyPrefix = "$" }) {
  if (!items || items.length === 0) {
    return <p className="subtitle">No data available right now.</p>;
  }

  const sorted = [...items].sort(
    (a, b) => ORDER[a.action] - ORDER[b.action] || b.confidence - a.confidence
  );

  const total = items.length;
  const buyPct = (items.filter((i) => i.action === "BUY").length / total) * 100;
  const holdPct = (items.filter((i) => i.action === "HOLD").length / total) * 100;
  const sellPct = (items.filter((i) => i.action === "SELL").length / total) * 100;

  return (
    <div>
      <div className="ppo-sentiment">
        <span className="dash-section-sub">Overall Market Sentiment</span>
        <div className="ppo-sentiment-bar">
          <div style={{ width: `${buyPct}%`, background: ACTION_COLORS.BUY }} />
          <div style={{ width: `${holdPct}%`, background: ACTION_COLORS.HOLD }} />
          <div style={{ width: `${sellPct}%`, background: ACTION_COLORS.SELL }} />
        </div>
        <div className="ppo-sentiment-legend">
          <span style={{ color: ACTION_COLORS.BUY }}>▲ BUY {buyPct.toFixed(0)}%</span>
          <span style={{ color: ACTION_COLORS.HOLD }}>◆ HOLD {holdPct.toFixed(0)}%</span>
          <span style={{ color: ACTION_COLORS.SELL }}>▼ SELL {sellPct.toFixed(0)}%</span>
        </div>
      </div>

      <div className="ppo-card-grid">
        {sorted.map((item) => (
          <button
            key={item.symbol}
            type="button"
            className={`ppo-card ${item.symbol === selected ? "active" : ""}`}
            style={{ "--action-color": ACTION_COLORS[item.action] }}
            onClick={() => onSelect(item.symbol)}
          >
            <div className="ppo-card-top">
              <span className="ppo-card-symbol">{item.symbol}</span>
              <span className="ppo-card-action">
                {ACTION_ICONS[item.action]} {item.action}
              </span>
            </div>
            <div className="ppo-card-price-row">
              <span className="ppo-card-price">
                {currencyPrefix}
                {item.price?.toFixed(2)}
              </span>
              <span className={`ppo-card-chg ${item.chg_pct >= 0 ? "up" : "down"}`}>
                {item.chg_pct >= 0 ? "▲" : "▼"} {Math.abs(item.chg_pct).toFixed(2)}%
              </span>
            </div>
            <div className="ppo-card-conf">Confidence {(item.confidence * 100).toFixed(0)}%</div>
            <div className="ppo-prob-bar">
              <div style={{ width: `${item.probabilities.BUY * 100}%`, background: ACTION_COLORS.BUY }} />
              <div style={{ width: `${item.probabilities.HOLD * 100}%`, background: ACTION_COLORS.HOLD }} />
              <div style={{ width: `${item.probabilities.SELL * 100}%`, background: ACTION_COLORS.SELL }} />
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
