import Plot from "react-plotly.js";

const ACTION_COLORS = { BUY: "#22C55E", HOLD: "#F59E0B", SELL: "#EF4444" };
const ACTION_SYMBOLS = { BUY: "triangle-up", SELL: "triangle-down", HOLD: "circle" };

/** Close-price line with BUY/SELL/HOLD markers from the agent's recent
 * per-bar recommendation history — the RL equivalent of "here's why". */
export default function PpoSignalChart({ chart, currencyPrefix = "$" }) {
  if (!chart || chart.length === 0) return null;

  const dates = chart.map((c) => c.date);
  const closes = chart.map((c) => c.close);

  const traces = [
    {
      type: "scatter",
      mode: "lines",
      x: dates,
      y: closes,
      line: { color: "#F59E0B", width: 2 },
      name: "Close Price",
      hovertemplate: `${currencyPrefix}%{y:,.2f}<extra></extra>`,
    },
  ];

  for (const action of ["BUY", "SELL", "HOLD"]) {
    const pts = chart.filter((c) => c.action === action);
    if (pts.length === 0) continue;
    traces.push({
      type: "scatter",
      mode: "markers",
      x: pts.map((p) => p.date),
      y: pts.map((p) => p.close),
      marker: {
        color: ACTION_COLORS[action],
        size: 8,
        symbol: ACTION_SYMBOLS[action],
        line: { color: "white", width: 1 },
      },
      name: `${action} signal`,
    });
  }

  return (
    <Plot
      data={traces}
      layout={{
        autosize: true,
        height: 340,
        paper_bgcolor: "rgba(0,0,0,0)",
        plot_bgcolor: "rgba(0,0,0,0)",
        margin: { l: 10, r: 10, t: 10, b: 10 },
        xaxis: { color: "#A1A1AA", gridcolor: "rgba(255,255,255,0.04)" },
        yaxis: { color: "#A1A1AA", gridcolor: "rgba(255,255,255,0.06)", tickprefix: currencyPrefix, automargin: true },
        legend: { orientation: "h", yanchor: "bottom", y: 1.02, font: { color: "#A1A1AA" } },
        hovermode: "x unified",
        hoverlabel: { bgcolor: "#1a1a2e", font: { color: "#E4E4E7" } },
        font: { family: "Inter, system-ui, sans-serif", color: "#E4E4E7" },
      }}
      config={{ displaylogo: false, responsive: true }}
      style={{ width: "100%" }}
      useResizeHandler
    />
  );
}
