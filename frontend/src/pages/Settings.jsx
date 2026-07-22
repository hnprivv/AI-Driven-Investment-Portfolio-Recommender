import { useEffect, useState } from "react";
import { useNavigate, useOutletContext } from "react-router-dom";
import { changePassword, deleteAccount, getFullProfile } from "../api";

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

  return (
    <div className="settings-page">
      <h1>Settings</h1>

      <div className="settings-grid">
        <section className="card">
          <h2>🔑 Change Password</h2>
          <form onSubmit={handlePasswordSubmit}>
            <label>Current Password</label>
            <input
              type="password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
            />
            <label>New Password</label>
            <input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder="Min. 8 characters"
            />
            <label>Confirm New Password</label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
            />
            {pwError && <div className="error">{pwError}</div>}
            {pwSuccess && <div className="success">{pwSuccess}</div>}
            <button type="submit" disabled={pwSubmitting}>
              {pwSubmitting ? "Updating…" : "Update Password"}
            </button>
          </form>
        </section>

        <section className="card">
          <h2>📤 Export Profile Data</h2>
          <p className="subtitle">
            Download a copy of your AIPRS profile as a JSON file. Your password is
            excluded from the export.
          </p>
          <button onClick={handleExport} disabled={!profile}>
            ⬇️ Download My Data
          </button>
        </section>

        <section className="card danger-zone">
          <h2>⚠️ Danger Zone</h2>
          <p className="subtitle">
            Deleting your account is <b>permanent and cannot be undone</b>. Enter
            your password to confirm.
          </p>
          <form onSubmit={handleDelete}>
            <label>Password</label>
            <input
              type="password"
              value={deletePassword}
              onChange={(e) => setDeletePassword(e.target.value)}
            />
            {deleteError && <div className="error">{deleteError}</div>}
            <button
              type="submit"
              className="danger-button"
              disabled={deleteSubmitting}
            >
              {deleteSubmitting ? "Deleting…" : "🗑️ Permanently Delete Account"}
            </button>
          </form>
        </section>
      </div>
    </div>
  );
}
