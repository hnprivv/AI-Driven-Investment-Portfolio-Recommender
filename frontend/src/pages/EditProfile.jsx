import { useEffect, useState } from "react";
import { getFullProfile, updateProfile } from "../api";
import MultiSelect from "../components/MultiSelect";
import NumberInput from "../components/NumberInput";
import Select from "../components/Select";
import "./EditProfile.css";

const INCOME_RANGES = ["< 25,000", "25,000 - 50,000", "50,000 - 100,000", "100,000+"];
const HORIZONS = ["1 Year", "3-5 Years", "5-10 Years", "10+ Years"];
const EXPERIENCES = ["Beginner", "Intermediate", "Advanced"];
const GOALS = ["Stable income", "Long-term stability", "Short-term trading", "Retirement"];
const PREFERENCES = ["Stocks", "Bonds", "Real Estate", "Crypto", "ETFs", "Commodities"];

const CLUSTER_LABELS = { 0: "Conservative", 1: "Moderate", 2: "Aggressive", 3: "Very Aggressive" };
const BADGE_COLORS = {
  Conservative: "#16a34a", Moderate: "#FFE600",
  Aggressive: "#ff8400", "Very Aggressive": "#b71212",
};

function fmtDate(iso) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" });
  } catch {
    return "—";
  }
}

export default function EditProfile() {
  const [profile, setProfile] = useState(null);
  const [error, setError] = useState("");

  const [age, setAge] = useState(25);
  const [incomeRange, setIncomeRange] = useState(INCOME_RANGES[0]);
  const [horizon, setHorizon] = useState(HORIZONS[0]);
  const [experience, setExperience] = useState(EXPERIENCES[0]);
  const [goals, setGoals] = useState(GOALS[0]);
  const [preferences, setPreferences] = useState([]);
  const [riskTolerance, setRiskTolerance] = useState(5);

  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState("");
  const [saveSuccess, setSaveSuccess] = useState("");

  useEffect(() => {
    getFullProfile()
      .then((p) => {
        setProfile(p);
        setAge(p.age ?? 25);
        setIncomeRange(p.income_range || INCOME_RANGES[0]);
        setHorizon(p.investment_horizon || HORIZONS[0]);
        setExperience(p.experience || EXPERIENCES[0]);
        setGoals(p.goals || GOALS[0]);
        setPreferences(p.preferences || []);
        setRiskTolerance(p.risk_tolerance ?? 5);
      })
      .catch((e) => setError(e.message));
  }, []);

  function handleExport() {
    if (!profile) return;
    const blob = new Blob([JSON.stringify(profile, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `aiprs_profile_${(profile.name || "user").toLowerCase().replace(/\s+/g, "_")}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  async function handleSave(e) {
    e.preventDefault();
    setSaveError("");
    setSaveSuccess("");
    setSaving(true);
    try {
      const updated = await updateProfile({
        age: Number(age),
        income_range: incomeRange,
        investment_horizon: horizon,
        experience,
        goals,
        preferences,
        risk_tolerance: Number(riskTolerance),
      });
      setProfile(updated);
      setSaveSuccess("Profile updated successfully.");
    } catch (err) {
      setSaveError(err.message);
    } finally {
      setSaving(false);
    }
  }

  if (error) {
    return (
      <div className="page-shell">
        <div className="page-shell-inner">
          <p className="error">{error}</p>
        </div>
      </div>
    );
  }

  const riskProfile = profile ? CLUSTER_LABELS[profile.cluster] ?? "Moderate" : null;
  const badgeColor = riskProfile ? BADGE_COLORS[riskProfile] : "#F59E0B";

  return (
    <div className="page-shell">
      <div className="page-shell-inner">
        <h1>Edit Profile</h1>
        <p className="subtitle">Update your financial profile so AIPRS can keep tailoring recommendations to you.</p>

        <section className="dash-section">
          <h2 className="dash-section-title">Account Overview</h2>
          {profile ? (
            <div className="chart-card account-card">
              <div className="account-grid">
                <div>
                  <span className="metric-label">Name</span>
                  <span className="account-value">{profile.name}</span>
                </div>
                <div>
                  <span className="metric-label">Email</span>
                  <span className="account-value">{profile.email || "—"}</span>
                </div>
                <div>
                  <span className="metric-label">Member Since</span>
                  <span className="account-value">{fmtDate(profile.created_at)}</span>
                </div>
                <div>
                  <span className="metric-label">Risk Profile</span>
                  <span className="risk-badge" style={{ "--badge-color": badgeColor }}>
                    ● {riskProfile}
                  </span>
                </div>
              </div>
            </div>
          ) : (
            <p className="dash-caption">Loading your profile…</p>
          )}
        </section>

        <div className="dash-divider"><span>◆</span></div>

        <section className="dash-section">
          <h2 className="dash-section-title">Financial Profile</h2>
          <form onSubmit={handleSave} className="chart-card edit-profile-form">
            <div className="edit-profile-grid">
              <div className="edit-profile-field">
                <label>Age</label>
                <NumberInput value={age} onChange={setAge} min={18} max={100} />
              </div>
              <div className="edit-profile-field">
                <label>Investment Experience</label>
                <Select value={experience} onChange={setExperience} options={EXPERIENCES} />
              </div>

              <div className="edit-profile-field">
                <label>Annual Income Range</label>
                <Select value={incomeRange} onChange={setIncomeRange} options={INCOME_RANGES} />
              </div>
              <div className="edit-profile-field">
                <label>Primary Goal</label>
                <Select value={goals} onChange={setGoals} options={GOALS} />
              </div>

              <div className="edit-profile-field">
                <label>Investment Horizon</label>
                <Select value={horizon} onChange={setHorizon} options={HORIZONS} />
              </div>
              <div className="edit-profile-field">
                <label>Preferred Assets</label>
                <MultiSelect
                  value={preferences}
                  onChange={setPreferences}
                  options={PREFERENCES}
                  placeholder="Select preferred assets…"
                />
              </div>

              <div className="edit-profile-full-row">
                <label>Risk Tolerance: {riskTolerance} / 10</label>
                <input
                  type="range"
                  min={1}
                  max={10}
                  value={riskTolerance}
                  onChange={(e) => setRiskTolerance(e.target.value)}
                />
              </div>
            </div>

            {saveError && <div className="error" style={{ marginTop: 10 }}>{saveError}</div>}
            {saveSuccess && <div className="success" style={{ marginTop: 10 }}>{saveSuccess}</div>}

            <button type="submit" disabled={saving || !profile} style={{ width: "100%", marginTop: 18 }}>
              {saving ? "Saving…" : "Save Changes"}
            </button>
          </form>
          <p className="dash-caption">
            Saving re-runs AIPRS's clustering model, so your Risk Profile badge above may change.
          </p>
        </section>

        <div className="dash-divider"><span>◆</span></div>

        <section className="dash-section">
          <h2 className="dash-section-title">📤 Export Profile Data</h2>
          <div className="chart-card edit-profile-form">
            <p className="dash-caption" style={{ margin: "0 0 14px" }}>
              Download a copy of your AIPRS profile as a JSON file. Your password is excluded from
              the export.
            </p>
            <button onClick={handleExport} disabled={!profile} style={{ width: "100%" }}>
              ⬇️ Download My Data
            </button>
          </div>
        </section>
      </div>
    </div>
  );
}
