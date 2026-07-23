import { Link } from "react-router-dom";

export default function Footer() {
  return (
    <footer className="site-footer">
      <p>AIPRS — AI-powered portfolio insights, for research and educational purposes only.</p>
      <p className="site-footer-links">
        <Link to="/updates">Update Log</Link>
        <span aria-hidden="true">·</span>
        <Link to="/privacy">Privacy Policy</Link>
        <span aria-hidden="true">·</span>
        <Link to="/terms">Terms &amp; Conditions</Link>
      </p>
    </footer>
  );
}
