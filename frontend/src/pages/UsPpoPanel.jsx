import { useEffect, useState } from "react";
import { getUsPpoBatch, getUsPpoDetail } from "../api";
import PpoDetail from "../components/PpoDetail";
import PpoWatchlist from "../components/PpoWatchlist";

export default function UsPpoPanel({ refreshKey }) {
  const [batch, setBatch] = useState(null);
  const [batchError, setBatchError] = useState("");
  const [loadingBatch, setLoadingBatch] = useState(true);

  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState(null);
  const [detailError, setDetailError] = useState("");
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [searchInput, setSearchInput] = useState("");

  useEffect(() => {
    setLoadingBatch(true);
    setBatchError("");
    getUsPpoBatch()
      .then(setBatch)
      .catch((err) => setBatchError(err.message))
      .finally(() => setLoadingBatch(false));
  }, [refreshKey]);

  useEffect(() => {
    if (!selected) return;
    setLoadingDetail(true);
    setDetailError("");
    setDetail(null);
    getUsPpoDetail(selected)
      .then(setDetail)
      .catch((err) => setDetailError(err.message))
      .finally(() => setLoadingDetail(false));
  }, [selected, refreshKey]);

  function handleSearch(e) {
    e.preventDefault();
    const sym = searchInput.trim().toUpperCase();
    if (sym) setSelected(sym);
  }

  return (
    <div className="ppo-panel">
      <form className="ppo-search" onSubmit={handleSearch}>
        <input
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          placeholder="Enter a US ticker, e.g. AAPL, TSLA, NVDA"
        />
        <button type="submit" className="btn-primary">Analyze</button>
      </form>

      {selected && (
        <PpoDetail
          detail={detail}
          loading={loadingDetail}
          error={detailError}
          onClose={() => setSelected(null)}
          currencyPrefix="$"
        />
      )}

      <div className="dash-section">
        <h2 className="dash-section-title">Watchlist</h2>
        {batchError && <p className="error">{batchError}</p>}
        {loadingBatch ? (
          <p className="subtitle">Analysing US stocks…</p>
        ) : (
          <PpoWatchlist items={batch} onSelect={setSelected} selected={selected} currencyPrefix="$" />
        )}
      </div>
    </div>
  );
}
