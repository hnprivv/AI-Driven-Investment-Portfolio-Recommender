import { Link, useLocation } from "react-router-dom";
import Navbar from "../components/Navbar";
import Footer from "../components/Footer";
import "./Legal.css";

const LAST_UPDATED = "July 23, 2026";

export default function TermsConditions({ user, onLogout }) {
  const location = useLocation();
  const fromSignup = location.state?.from === "signup";

  return (
    <div className="legal-page">
      <Navbar minimal />
      <div className="legal-shell">
        <div className="legal-inner">
          <div className="legal-title-row">
            <h1>Terms & Conditions</h1>
            {fromSignup && (
              <Link to="/signup" className="legal-back-link">← Back to Signup</Link>
            )}
          </div>
          <p className="subtitle">Last updated: {LAST_UPDATED}</p>

          <div className="legal-card">
            <p>
              By creating an account or using AIPRS (AI-Powered Portfolio Recommendation System),
              you agree to these Terms & Conditions. If you don't agree, please don't use AIPRS.
            </p>
          </div>

          <section className="legal-section">
            <h2>1. Not Financial Advice</h2>
            <p>
              AIPRS is an independent personal project for AI-assisted investment research and
              education. It is <b>not</b> a licensed financial advisory service, investment
              platform, broker-dealer, or bank, and is not regulated by any financial authority.
              Portfolio allocations, risk profiles, performance metrics, news sentiment, and any
              other output are generated algorithmically and may be inaccurate, delayed, or
              incomplete. Nothing on AIPRS constitutes personalized financial, investment, tax, or
              legal advice, and should not be relied upon as the sole basis for any investment
              decision.
            </p>
          </section>

          <section className="legal-section">
            <h2>2. No Trading or Custody</h2>
            <p>
              AIPRS does not execute trades, hold funds or securities, or connect to any real
              brokerage account. Any "holdings" you enter are self-reported figures used purely
              to compute illustrative metrics — they don't reflect an actual live position
              anywhere.
            </p>
          </section>

          <section className="legal-section">
            <h2>3. Market Data</h2>
            <p>
              Market data is sourced from third-party providers (Alpaca Markets, Yahoo Finance,
              psxterminal.com) and may be delayed — U.S. market data is delayed up to 15 minutes
              via the IEX feed. Data may occasionally be unavailable, in which case AIPRS may fall
              back to a static or illustrative benchmark. We make no guarantee of accuracy,
              completeness, or timeliness of any market data, news, or sentiment analysis shown.
            </p>
          </section>

          <section className="legal-section">
            <h2>4. Your Account</h2>
            <ul>
              <li>You must be at least 18 years old to create an account.</li>
              <li>You're responsible for keeping your password confidential and for all activity under your account.</li>
              <li>You agree to provide accurate information in your profile — the risk-profiling and recommendation features rely on it being truthful.</li>
              <li>You can delete your account at any time from Settings; this permanently removes your data as described in the Privacy Policy.</li>
            </ul>
          </section>

          <section className="legal-section">
            <h2>5. Acceptable Use</h2>
            <p>You agree not to:</p>
            <ul>
              <li>Use AIPRS for any unlawful purpose, or attempt to interfere with, disrupt, or gain unauthorized access to it.</li>
              <li>Scrape, reverse-engineer, or excessively automate requests against AIPRS in a way that degrades the service for others.</li>
              <li>Submit false, misleading, or abusive content through the feedback or survey features.</li>
              <li>Impersonate another person or misrepresent your affiliation with AIPRS.</li>
            </ul>
            <p>We may suspend or delete accounts that violate these terms.</p>
          </section>

          <section className="legal-section">
            <h2>6. No Warranty</h2>
            <p>
              AIPRS is provided "as is" and "as available," without warranties of any kind,
              express or implied, including fitness for a particular purpose, accuracy, or
              uninterrupted availability. As a personal project, AIPRS may change, be temporarily
              unavailable, or be discontinued at any time without notice.
            </p>
          </section>

          <section className="legal-section">
            <h2>7. Limitation of Liability</h2>
            <p>
              To the fullest extent permitted by law, AIPRS and its creator are not liable for any
              investment losses, damages, or decisions made in reliance on information provided by
              the platform, nor for any indirect, incidental, or consequential damages arising
              from your use of AIPRS.
            </p>
          </section>

          <section className="legal-section">
            <h2>8. Changes to These Terms</h2>
            <p>
              These terms may be updated as AIPRS evolves. Continued use of AIPRS after changes
              are posted constitutes acceptance of the updated terms.
            </p>
          </section>

          <section className="legal-section">
            <h2>9. Contact</h2>
            <p>
              Questions about these terms can be sent via the Feedback page, or to{" "}
              <a href="mailto:aiprs.support@gmail.com">aiprs.support@gmail.com</a>.
            </p>
          </section>
        </div>
      </div>
      <Footer />
    </div>
  );
}
