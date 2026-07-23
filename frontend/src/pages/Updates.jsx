import Navbar from "../components/Navbar";
import Footer from "../components/Footer";
import { UPDATES_LOG } from "../updatesLog";
import "./Updates.css";

export default function Updates({ user, onLogout }) {
  return (
    <div className="updates-page">
      <Navbar user={user} onLogout={onLogout} />
      <div className="updates-shell">
        <div className="updates-inner">
          <h1>Update Log</h1>
          <p className="subtitle">What's shipped, and what's coming next.</p>

          <div className="updates-next-card">
            <span className="updates-next-label">Next Up</span>
            <h2>PPO Advisors migration</h2>
            <p>
              The reinforcement-learning trading advisors (PPO agents for US and PSX equities)
              currently only live in the legacy Streamlit app. They're being ported to the React
              frontend next — one page, two tabs — so BUY / HOLD / SELL signals with confidence
              scores are available in the main app.
            </p>
          </div>

          <div className="updates-log">
            <h2>Changelog</h2>
            <div className="updates-timeline">
              {UPDATES_LOG.map((entry) => (
                <div key={entry.title} className="updates-entry">
                  <span className="updates-entry-date">{entry.date}</span>
                  <h3>{entry.title}</h3>
                  <p>{entry.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
      <Footer />
    </div>
  );
}
