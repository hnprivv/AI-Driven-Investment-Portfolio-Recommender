import { useEffect, useState } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { me } from "./api";
import Layout from "./components/Layout";
import ScrollToTop from "./components/ScrollToTop";
import Home from "./pages/Home";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import Dashboard from "./pages/Dashboard";
import EditProfile from "./pages/EditProfile";
import Feedback from "./pages/Feedback";
import MarketOverview from "./pages/MarketOverview";
import NewsSentiment from "./pages/NewsSentiment";
import PrivacyPolicy from "./pages/PrivacyPolicy";
import Recommendations from "./pages/Recommendations";
import Settings from "./pages/Settings";
import TermsConditions from "./pages/TermsConditions";

export default function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    me()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return null;

  return (
    <>
      <ScrollToTop />
      <Routes>
        <Route path="/" element={<Home user={user} onLogout={() => setUser(null)} />} />
        <Route path="/privacy" element={<PrivacyPolicy user={user} onLogout={() => setUser(null)} />} />
        <Route path="/terms" element={<TermsConditions user={user} onLogout={() => setUser(null)} />} />
        <Route
          path="/login"
          element={user ? <Navigate to="/dashboard" /> : <Login onLogin={setUser} />}
        />
        <Route
          path="/signup"
          element={user ? <Navigate to="/dashboard" /> : <Signup onLogin={setUser} />}
        />
        <Route
          element={
            <Layout
              user={user}
              onLogout={() => setUser(null)}
              onUserUpdate={(updates) => setUser((u) => ({ ...u, ...updates }))}
            />
          }
        >
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/recommendations" element={<Recommendations />} />
          <Route path="/market" element={<MarketOverview />} />
          <Route path="/news" element={<NewsSentiment />} />
          <Route path="/feedback" element={<Feedback />} />
          <Route path="/profile" element={<EditProfile />} />
          <Route path="/settings" element={<Settings />} />
        </Route>
      </Routes>
    </>
  );
}
