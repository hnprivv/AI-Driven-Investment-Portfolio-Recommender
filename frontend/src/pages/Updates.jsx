import Navbar from "../components/Navbar";
import Footer from "../components/Footer";
import "./Updates.css";

const LOG = [
  {
    date: "July 23, 2026",
    title: "Live in production",
    desc: "AIPRS is now deployed: the React frontend on Vercel, the FastAPI backend on Hugging Face Spaces. Session auth runs on a bearer token rather than a cookie, so it works reliably across the two domains.",
  },
  {
    date: "July 23, 2026",
    title: "Account security fix",
    desc: "Session identity now keys on email instead of display name, closing a bug where two accounts with the same name could see each other's holdings and profile data.",
  },
  {
    date: "July 23, 2026",
    title: "Account management & email notifications",
    desc: "Added the Edit Profile and Settings pages (password change, data export, account deletion) plus transactional emails for welcome, credentials changes, holdings updates, and account deletion.",
  },
  {
    date: "July 23, 2026",
    title: "Legal pages & footer",
    desc: "Added a site footer with Privacy Policy and Terms & Conditions pages.",
  },
  {
    date: "July 23, 2026",
    title: "Market Overview & News Sentiment",
    desc: "Live/delayed candlestick charts for US and Pakistan Stock Exchange (PSX) markets, plus FinBERT-scored sentiment on financial headlines from both markets.",
  },
  {
    date: "July 23, 2026",
    title: "AI Recommendations",
    desc: "Modern Portfolio Theory-optimised allocations for your risk cluster, plus a 'Trending with Investors Like You' peer insights panel.",
  },
  {
    date: "July 22–23, 2026",
    title: "Dashboard",
    desc: "Portfolio metrics, a performance chart, holdings input, an asset allocation breakdown, PDF report export, and 3D AI cluster placement.",
  },
  {
    date: "July 22, 2026",
    title: "React + FastAPI migration begins",
    desc: "Started rebuilding AIPRS as a React (Vite) frontend backed by a FastAPI API, moving off the original all-in-one Streamlit app.",
  },
];

export default function Updates({ user, onLogout }) {
  return (
    <div className="updates-page">
      <Navbar user={user} onLogout={onLogout} />
      <div className="updates-shell">
        <div className="updates-inner">
          <h1>Updates</h1>
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
              {LOG.map((entry) => (
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
