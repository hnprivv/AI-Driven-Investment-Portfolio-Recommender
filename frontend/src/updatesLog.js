// Shared between Updates.jsx (renders the full log) and Navbar.jsx (shows a
// "new" dot until the user has visited /updates since the latest entry).
export const UPDATES_LOG = [
  {
    id: "ppo-advisors",
    date: "July 24, 2026",
    title: "Agents — PPO Advisors",
    desc: "Reinforcement-learning BUY / HOLD / SELL trading signals, ported from the legacy Streamlit app into a redesigned Agents page — one page, two tabs (US and PSX), with a watchlist, confidence meters, market indicators, signal history chart, and hit-rate stats, all adapted to your risk profile.",
  },
  {
    id: "live-in-production",
    date: "July 23, 2026",
    title: "Live in production",
    desc: "AIPRS is now deployed: the React frontend on Vercel, the FastAPI backend on Hugging Face Spaces. Session auth runs on a bearer token rather than a cookie, so it works reliably across the two domains.",
  },
  {
    id: "account-security-fix",
    date: "July 23, 2026",
    title: "Account security fix",
    desc: "Session identity now keys on email instead of display name, closing a bug where two accounts with the same name could see each other's holdings and profile data.",
  },
  {
    id: "account-management-email",
    date: "July 23, 2026",
    title: "Account management & email notifications",
    desc: "Added the Edit Profile and Settings pages (password change, data export, account deletion) plus transactional emails for welcome, credentials changes, holdings updates, and account deletion.",
  },
  {
    id: "legal-pages-footer",
    date: "July 23, 2026",
    title: "Legal pages & footer",
    desc: "Added a site footer with Privacy Policy and Terms & Conditions pages.",
  },
  {
    id: "market-news",
    date: "July 23, 2026",
    title: "Market Overview & News Sentiment",
    desc: "Live/delayed candlestick charts for US and Pakistan Stock Exchange (PSX) markets, plus FinBERT-scored sentiment on financial headlines from both markets.",
  },
  {
    id: "ai-recommendations",
    date: "July 23, 2026",
    title: "AI Recommendations",
    desc: "Modern Portfolio Theory-optimised allocations for your risk cluster, plus a 'Trending with Investors Like You' peer insights panel.",
  },
  {
    id: "dashboard",
    date: "July 22–23, 2026",
    title: "Dashboard",
    desc: "Portfolio metrics, a performance chart, holdings input, an asset allocation breakdown, PDF report export, and 3D AI cluster placement.",
  },
  {
    id: "migration-begins",
    date: "July 22, 2026",
    title: "React + FastAPI migration begins",
    desc: "Started rebuilding AIPRS as a React (Vite) frontend backed by a FastAPI API, moving off the original all-in-one Streamlit app.",
  },
];

// Newest entry first — bump this whenever a new entry is added, so the
// Navbar's "new" indicator lights up again.
export const LATEST_UPDATE_ID = UPDATES_LOG[0].id;
