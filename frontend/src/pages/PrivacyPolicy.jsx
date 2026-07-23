import { Link, useLocation } from "react-router-dom";
import Navbar from "../components/Navbar";
import Footer from "../components/Footer";
import "./Legal.css";

const LAST_UPDATED = "July 23, 2026";

export default function PrivacyPolicy({ user, onLogout }) {
  const location = useLocation();
  const fromSignup = location.state?.from === "signup";

  return (
    <div className="legal-page">
      <Navbar minimal />
      <div className="legal-shell">
        <div className="legal-inner">
          <div className="legal-title-row">
            <h1>Privacy Policy</h1>
            {fromSignup && (
              <Link to="/signup" className="legal-back-link">← Back to Signup</Link>
            )}
          </div>
          <p className="subtitle">Last updated: {LAST_UPDATED}</p>

          <div className="legal-card">
            <p>
              This Privacy Policy explains what information AIPRS (AI-Powered Portfolio
              Recommendation System) collects, how it's used, and the choices you have. AIPRS is
              an independent personal project providing AI-assisted investment research and
              education — it is not a licensed financial institution, broker, or advisor.
            </p>
          </div>

          <section className="legal-section">
            <h2>1. Information We Collect</h2>
            <p>When you create an account, we collect:</p>
            <ul>
              <li>Your name, email address, and a securely hashed password (we never store your password in plain text).</li>
              <li>Financial profile details you provide: age, income range, investment horizon, experience level, primary goals, preferred asset types, and a self-reported risk tolerance score.</li>
              <li>Portfolio holdings you choose to enter (ticker symbols, weights, and market).</li>
              <li>Feedback, survey responses, and support messages you submit, along with optional contact info.</li>
            </ul>
            <p>
              We do not collect payment information, government ID, or brokerage account
              credentials — AIPRS does not connect to or execute trades in any real brokerage
              account.
            </p>
          </section>

          <section className="legal-section">
            <h2>2. How We Use Your Information</h2>
            <ul>
              <li><b>Risk profiling:</b> your financial profile is passed through a K-Means clustering model to assign a risk category (e.g. Conservative, Moderate, Aggressive), which drives the portfolio allocations and metrics shown to you.</li>
              <li><b>Portfolio insights:</b> your entered holdings are matched against live/delayed market data to compute performance metrics and allocation breakdowns, shown only to you.</li>
              <li><b>Community insights:</b> your stated asset preferences are aggregated with other users in the same risk cluster to power the "Trending with Investors Like You" feature. This only ever surfaces aggregate counts (e.g. "held by 4 of your peers") — your individual preferences are never shown to other users.</li>
              <li><b>Account & security emails:</b> we send a one-time welcome email on signup and a confirmation email if you delete your account. If you opt in from your Profile page, we also send emails when your holdings, password, or email address change.</li>
            </ul>
          </section>

          <section className="legal-section">
            <h2>3. Third-Party Data Sources</h2>
            <p>
              To generate market data, news, and sentiment analysis, AIPRS queries third-party
              services on your behalf when you use those features:
            </p>
            <ul>
              <li><b>Alpaca Markets</b> — U.S. equity/crypto price data and financial news (15-minute delayed, IEX feed).</li>
              <li><b>Yahoo Finance</b> and <b>psxterminal.com</b> — Pakistan Stock Exchange (PSX) price data.</li>
              <li><b>Google News RSS</b> — PSX-related news headlines.</li>
            </ul>
            <p>
              Sentiment analysis is performed locally using an open-source FinBERT model — your
              data is not sent to a third party for this step. We don't share your personal
              profile data with any of the above services; we only send the ticker symbols or
              search terms needed to fetch public market data.
            </p>
          </section>

          <section className="legal-section">
            <h2>4. Sessions</h2>
            <p>
              AIPRS keeps you signed in using a session token stored in your browser, sent with
              each request to identify your account. It contains no tracking or advertising
              identifiers, and we don't use third-party analytics or ad-tracking cookies.
            </p>
          </section>

          <section className="legal-section">
            <h2>5. Data Retention & Deletion</h2>
            <p>
              Your data is retained for as long as your account exists. You can export a copy of
              your profile as JSON at any time from the Edit Profile page. You can permanently
              delete your account and all associated data (profile, holdings, risk assessment)
              from the Settings page — this action is immediate and irreversible.
            </p>
          </section>

          <section className="legal-section">
            <h2>6. Data Storage</h2>
            <p>
              Your data is stored in a MongoDB database. Reasonable technical safeguards
              (password hashing, HTTP-only session cookies) are in place, but as with any online
              service, no method of storage or transmission is 100% secure.
            </p>
          </section>

          <section className="legal-section">
            <h2>7. Eligibility</h2>
            <p>
              AIPRS is intended for users aged 18 and over. We don't knowingly collect
              information from anyone under 18.
            </p>
          </section>

          <section className="legal-section">
            <h2>8. Changes to This Policy</h2>
            <p>
              We may update this Privacy Policy from time to time as AIPRS evolves. Continued use
              of AIPRS after changes are posted constitutes acceptance of the updated policy.
            </p>
          </section>

          <section className="legal-section">
            <h2>9. Contact</h2>
            <p>
              Questions about this policy or your data can be sent via the Feedback page, or to{" "}
              <a href="mailto:aiprs.support@gmail.com">aiprs.support@gmail.com</a>.
            </p>
          </section>
        </div>
      </div>
      <Footer />
    </div>
  );
}
