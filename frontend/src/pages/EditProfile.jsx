import { useEffect, useState } from "react";
import { useOutletContext } from "react-router-dom";
import { getFullProfile, updateAccount, updateEmailPreference, updateProfile } from "../api";
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
  const { onUserUpdate } = useOutletContext();
  const [profile, setProfile] = useState(null);
  const [error, setError] = useState("");

  const [accountName, setAccountName] = useState("");
  const [accountEmail, setAccountEmail] = useState("");
  const [accountPassword, setAccountPassword] = useState("");
  const [accountSaving, setAccountSaving] = useState(false);
  const [accountError, setAccountError] = useState("");
  const [accountSuccess, setAccountSuccess] = useState("");

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

  const [emailOptIn, setEmailOptIn] = useState(false);
  const [emailPrefSaving, setEmailPrefSaving] = useState(false);
  const [emailPrefError, setEmailPrefError] = useState("");

  useEffect(() => {
    getFullProfile()
      .then((p) => {
        setProfile(p);
        setAccountName(p.name || "");
        setAccountEmail(p.email || "");
        setAge(p.age ?? 25);
        setIncomeRange(p.income_range || INCOME_RANGES[0]);
        setHorizon(p.investment_horizon || HORIZONS[0]);
        setExperience(p.experience || EXPERIENCES[0]);
        setGoals(p.goals || GOALS[0]);
        setPreferences(p.preferences || []);
        setRiskTolerance(p.risk_tolerance ?? 5);
        setEmailOptIn(Boolean(p.email_opt_in));
      })
      .catch((e) => setError(e.message));
  }, []);

  async function handleEmailOptInChange(e) {
    const next = e.target.checked;
    setEmailOptIn(next);
    setEmailPrefError("");
    setEmailPrefSaving(true);
    try {
      await updateEmailPreference(next);
    } catch (err) {
      setEmailOptIn(!next);
      setEmailPrefError(err.message);
    } finally {
      setEmailPrefSaving(false);
    }
  }

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

  const emailChanged = profile && accountEmail.trim().toLowerCase() !== (profile.email || "");

  async function handleAccountSave(e) {
    e.preventDefault();
    setAccountError("");
    setAccountSuccess("");

    if (!accountName.trim() || !accountEmail.trim()) {
      setAccountError("Name and email cannot be empty.");
      return;
    }
    if (emailChanged && !accountPassword) {
      setAccountError("Please enter your password to change your email.");
      return;
    }

    setAccountSaving(true);
    try {
      const updated = await updateAccount({
        name: accountName.trim(),
        email: accountEmail.trim(),
        password: accountPassword,
      });
      setProfile(updated);
      setAccountName(updated.name);
      setAccountEmail(updated.email);
      setAccountPassword("");
      setAccountSuccess("Account details updated successfully.");
      onUserUpdate?.({ name: updated.name, email: updated.email });
    } catch (err) {
      setAccountError(err.message);
    } finally {
      setAccountSaving(false);
    }
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
          <div className="profile-side-grid">
            <div>
              <h2 className="dash-section-title">User Profile</h2>
              <form onSubmit={handleAccountSave} className="chart-card settings-form">
                <label className="field-label" htmlFor="account-name">Full Name</label>
                <input
                  id="account-name"
                  type="text"
                  value={accountName}
                  onChange={(e) => setAccountName(e.target.value)}
                />
                <label className="field-label" htmlFor="account-email" style={{ marginTop: 14 }}>Email Address</label>
                <input
                  id="account-email"
                  type="email"
                  value={accountEmail}
                  onChange={(e) => setAccountEmail(e.target.value)}
                />
                {emailChanged && (
                  <>
                    <label className="field-label" htmlFor="account-password" style={{ marginTop: 14 }}>
                      Password <span className="dash-caption" style={{ margin: 0, display: "inline" }}>(required to change your email)</span>
                    </label>
                    <input
                      id="account-password"
                      type="password"
                      value={accountPassword}
                      onChange={(e) => setAccountPassword(e.target.value)}
                    />
                  </>
                )}
                {accountError && <div className="error" style={{ marginTop: 10 }}>{accountError}</div>}
                {accountSuccess && <div className="success" style={{ marginTop: 10 }}>{accountSuccess}</div>}
                <button type="submit" disabled={accountSaving || !profile} style={{ width: "100%", marginTop: 16 }}>
                  {accountSaving ? "Saving…" : "Save Account Details"}
                </button>
              </form>
            </div>

            <div>
              <h2 className="dash-section-title">Export Profile Data</h2>
              <div className="chart-card settings-form">
                <p className="dash-caption" style={{ margin: "0 0 14px" }}>
                  Download a copy of your AIPRS profile as a JSON file. Your password is excluded
                  from the export.
                </p>
                <button onClick={handleExport} disabled={!profile} style={{ width: "100%" }}>
                  Download My Data
                </button>
              </div>

              <div className="chart-card settings-form email-pref-card">
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={emailOptIn}
                    onChange={handleEmailOptInChange}
                    disabled={!profile || emailPrefSaving}
                  />
                  I want to receive emails about account updates.
                </label>
                {emailPrefError && <div className="error" style={{ marginTop: 8 }}>{emailPrefError}</div>}
              </div>
            </div>
          </div>
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
      </div>
    </div>
  );
}
