import { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { logout } from "../api";

// One-line addition per future page — Overview, Recommendations, Market,
// PPO Advisors, News, etc. just get appended here as they're built.
const NAV_LINKS = [
  { label: "Dashboard", path: "/" },
  { label: "Settings", path: "/settings" },
];

export default function Navbar({ user, onLogout }) {
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);

  async function handleLogout() {
    await logout();
    onLogout();
    navigate("/login");
  }

  return (
    <header className="navbar">
      <div className="navbar-inner">
        <NavLink to="/" className="navbar-brand">
          AIPRS
        </NavLink>

        <div className={`navbar-menu ${menuOpen ? "open" : ""}`}>
          <nav className="navbar-links">
            {NAV_LINKS.map((link) => (
              <NavLink
                key={link.path}
                to={link.path}
                end={link.path === "/"}
                className={({ isActive }) =>
                  "navbar-link" + (isActive ? " active" : "")
                }
                onClick={() => setMenuOpen(false)}
              >
                {link.label}
              </NavLink>
            ))}
          </nav>

          <div className="navbar-user">
            <span className="navbar-username">{user?.name}</span>
            <button className="navbar-logout" onClick={handleLogout}>
              Log Out
            </button>
          </div>
        </div>

        <button
          className="navbar-hamburger"
          aria-label="Toggle menu"
          onClick={() => setMenuOpen((v) => !v)}
        >
          <span />
          <span />
          <span />
        </button>
      </div>
    </header>
  );
}
