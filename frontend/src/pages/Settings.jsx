import { useState } from "react";
import { Link, useNavigate, useOutletContext } from "react-router-dom";
import { changePassword, deleteAccount } from "../api";
import "./Settings.css";

export default function Settings() {
  const { onLogout } = useOutletContext();
  const navigate = useNavigate();

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

  return (
    <div className="page-shell">
      <div className="page-shell-inner">
        <h1>Settings</h1>
        <p className="subtitle">
          Manage your account and password.{" "}
          <Link to="/profile" className="settings-profile-link">
            Edit your profile & preferences →
          </Link>
        </p>

        {/* ── Change Password ───────────────────────────────────────────── */}
        <section className="dash-section">
          <h2 className="dash-section-title">🔑 Change Password</h2>
          <form onSubmit={handlePasswordSubmit} className="chart-card settings-form centered">
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

        {/* ── Danger Zone ────────────────────────────────────────────────── */}
        <section className="dash-section">
          <h2 className="dash-section-title danger-title centered-title">⚠️ Danger Zone</h2>
          <div className="danger-card centered">
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
