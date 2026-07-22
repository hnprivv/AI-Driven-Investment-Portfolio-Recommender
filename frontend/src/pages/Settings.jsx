import { useEffect, useState } from "react";
import { useNavigate, useOutletContext } from "react-router-dom";
import { changePassword, deleteAccount, getFullProfile } from "../api";
import "./Settings.css";

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

export default function Settings() {
  const { onLogout } = useOutletContext();
  const navigate = useNavigate();
  const [profile, setProfile] = useState(null);

  // Change password form
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [pwError, setPwError] = useState("");
  const [pwSuccess, setPwSuccess] = useState("");
  const [pwSubmitting, setPwSubmitting] = useState(false);

  // Delete account
  const [deletePassword, setDeletePassword] = useState("");
  const [deleteError, setDeleteError] = useState("");
  const [deleteSubmitting, setDeleteSubmitting] = useState(false);

  useEffect(() => {
    getFullProfile().then(setProfile).catch(() => {});
  }, []);

  async function handlePasswordSubmit(e) {
    e.preventDefault();
    setPwError("");
    setPwSuccess("");

    if (!currentPassword || !newPassword || !confirmPassword) {
      setPwError("Please fill in all password fields.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setPwError("New passwords do not match.");
      return;
    }
    if (newPassword.length < 8) {
      setPwError("New password must be at least 8 characters.");
      return;
    }

    setPwSubmitting(true);
    try {
      await changePassword(currentPassword, newPassword);
      setPwSuccess("Password updated successfully.");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (err) {
      setPwError(err.message);
    } finally {
      setPwSubmitting(false);
    }
  }

  function handleExport() {
    if (!profile) return;
    const blob = new Blob([JSON.stringify(profile, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `aiprs_profile_${(profile.name || "user").toLowerCase().replace(/\s+/g, "_")}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  async function handleDelete(e) {
    e.preventDefault();
    setDeleteError("");
    if (!deletePassword) {
      setDeleteError("Please enter your password.");
      return;
    }
    setDeleteSubmitting(true);
    try {
      await deleteAccount(deletePassword);
      onLogout();
      navigate("/login");
    } catch (err) {
      setDeleteError(err.message);
    } finally {
      setDeleteSubmitting(false);
    }
  }

  const riskProfile = profile ? CLUSTER_LABELS[profile.cluster] || "Moderate" : null;
  const badgeColor = riskProfile ? BADGE_COLORS[riskProfile] : "#F59E0B";

  return (
    <div className="page-shell">
      <div className="page-shell-inner">
        <h1>Settings</h1>
        <p className="subtitle">Manage your account, notifications, and data.</p>

        {/* ── Account Overview ──────────────────────────────────────────── */}
        <section className="dash-section">
          <h2 className="dash-section-title">Account Overview</h2>
          {profile ? (
            <div className="chart-card">
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

        {/* ── Change Password ───────────────────────────────────────────── */}
        <section className="dash-section">
          <h2 className="dash-section-title">🔑 Change Password</h2>
          <form onSubmit={handlePasswordSubmit} className="chart-card settings-form">
            <label className="field-label" htmlFor="current-pw">Current Password</label>
            <input
              id="current-pw"
              type="password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
            />
            <label className="field-label" htmlFor="new-pw" style={{ marginTop: 14 }}>New Password</label>
            <input
              id="new-pw"
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder="Min. 8 characters"
            />
            <label className="field-label" htmlFor="confirm-pw" style={{ marginTop: 14 }}>Confirm New Password</label>
            <input
              id="confirm-pw"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
            />
            {pwError && <div className="error" style={{ marginTop: 10 }}>{pwError}</div>}
            {pwSuccess && <div className="success" style={{ marginTop: 10 }}>{pwSuccess}</div>}
            <button type="submit" disabled={pwSubmitting} style={{ width: "100%", marginTop: 16 }}>
              {pwSubmitting ? "Updating…" : "Update Password"}
            </button>
          </form>
        </section>

        <div className="dash-divider"><span>◆</span></div>

        {/* ── Export Profile Data ───────────────────────────────────────── */}
        <section className="dash-section">
          <h2 className="dash-section-title">📤 Export Profile Data</h2>
          <div className="chart-card settings-form">
            <p className="dash-caption" style={{ margin: "0 0 14px" }}>
              Download a copy of your AIPRS profile as a JSON file. Your password is excluded from
              the export.
            </p>
            <button onClick={handleExport} disabled={!profile} style={{ width: "100%" }}>
              ⬇️ Download My Data
            </button>
          </div>
        </section>

        <div className="dash-divider"><span>◆</span></div>

        {/* ── Danger Zone ────────────────────────────────────────────────── */}
        <section className="dash-section">
          <h2 className="dash-section-title danger-title">⚠️ Danger Zone</h2>
          <div className="danger-card">
            <p className="dash-caption" style={{ margin: "0 0 14px", color: "#f1a3a3" }}>
              Deleting your account is <b>permanent and cannot be undone</b>. All your profile data,
              risk assessments, and preferences will be removed.
            </p>
            <form onSubmit={handleDelete} className="settings-form">
              <label className="field-label" htmlFor="delete-pw">Password</label>
              <input
                id="delete-pw"
                type="password"
                value={deletePassword}
                onChange={(e) => setDeletePassword(e.target.value)}
              />
              {deleteError && <div className="error" style={{ marginTop: 10 }}>{deleteError}</div>}
              <button
                type="submit"
                className="danger-button"
                disabled={deleteSubmitting}
                style={{ width: "100%", marginTop: 16 }}
              >
                {deleteSubmitting ? "Deleting…" : "🗑️ Permanently Delete Account"}
              </button>
            </form>
          </div>
        </section>
      </div>
    </div>
  );
}
