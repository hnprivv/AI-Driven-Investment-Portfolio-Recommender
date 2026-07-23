// VITE_API_BASE is set as a build-time env var on the hosting platform
// (e.g. Vercel project settings) pointing at the deployed backend
// (e.g. https://your-space.hf.space). Falls back to local dev.
export const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

// Session auth uses a bearer token (in localStorage), not a cookie.
// Hugging Face Spaces' edge proxy answers CORS preflight (OPTIONS) requests
// itself and never forwards them to the app, so it can't be made to echo
// Access-Control-Allow-Credentials — which breaks cookies (the browser
// requires that header whenever a request uses credentials: "include").
// A bearer token isn't sent in credentialed mode, so it isn't affected.
const TOKEN_KEY = "aiprs_token";

export const getToken = () => localStorage.getItem(TOKEN_KEY);
const setToken = (token) => localStorage.setItem(TOKEN_KEY, token);
export const clearToken = () => localStorage.removeItem(TOKEN_KEY);

async function request(path, options = {}) {
  const token = getToken();
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    ...options,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || "Request failed");
  }
  if (data.token) setToken(data.token);
  return data;
}

export function login(email, password) {
  return request("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function signup(payload) {
  return request("/auth/signup", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function logout() {
  try {
    await request("/auth/logout", { method: "POST" });
  } finally {
    clearToken();
  }
}

export function me() {
  return request("/auth/me");
}

export function getFullProfile() {
  return request("/users/me");
}

export function updateAccount(payload) {
  return request("/users/me/account", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function updateEmailPreference(emailOptIn) {
  return request("/users/me/email-preference", {
    method: "PUT",
    body: JSON.stringify({ email_opt_in: emailOptIn }),
  });
}

export function updateProfile(payload) {
  return request("/users/me/profile", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function changePassword(currentPassword, newPassword) {
  return request("/users/me/password", {
    method: "PUT",
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
    }),
  });
}

export function deleteAccount(password) {
  return request("/users/me", {
    method: "DELETE",
    body: JSON.stringify({ password }),
  });
}

export function getPortfolioOverview() {
  return request("/portfolio/overview");
}

// The PDF report can't be a plain <a href> anymore — that's a direct
// browser navigation with no way to attach the Authorization header the
// bearer-token session needs, so it's fetched here and turned into a
// blob: URL for the browser to download instead.
export async function downloadReportPdf() {
  const token = getToken();
  const res = await fetch(`${API_BASE}/portfolio/report.pdf`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || "Could not generate report");
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "aiprs_portfolio_report.pdf";
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export function getClusterPlacement() {
  return request("/portfolio/cluster-placement");
}

export function getRecommendations() {
  return request("/recommendations");
}

export function getMarketStatus(market) {
  return request(`/market/status?market=${market}`);
}

export function getMarketQuotes(symbols, crypto = false) {
  return request(`/market/quotes?symbols=${encodeURIComponent(symbols.join(","))}&crypto=${crypto}`);
}

export function getMarketCandles(symbol, timeframe, limit, crypto = false) {
  return request(
    `/market/candles?symbol=${encodeURIComponent(symbol)}&timeframe=${timeframe}&limit=${limit}&crypto=${crypto}`
  );
}

export function getPsxQuotes(symbols) {
  return request(`/market/psx/quotes?symbols=${encodeURIComponent(symbols.join(","))}`);
}

export function getPsxCandles(symbol, limit) {
  return request(`/market/psx/candles?symbol=${encodeURIComponent(symbol)}&limit=${limit}`);
}

export function getMarketNews(limit) {
  return request(`/news/market?limit=${limit}`);
}

export function getTickerNews(symbol, limit) {
  return request(`/news/ticker?symbol=${encodeURIComponent(symbol)}&limit=${limit}`);
}

export function getPsxMarketNews(limit) {
  return request(`/news/psx/market?limit=${limit}`);
}

export function getPsxCompanyNews(query, limit) {
  return request(`/news/psx/company?query=${encodeURIComponent(query)}&limit=${limit}`);
}

export function submitFeedback(payload) {
  return request("/feedback", { method: "POST", body: JSON.stringify(payload) });
}

export function submitSurvey(payload) {
  return request("/survey", { method: "POST", body: JSON.stringify(payload) });
}

export function saveHoldings(holdingsText) {
  return request("/users/me/holdings", {
    method: "PUT",
    body: JSON.stringify({ holdings_text: holdingsText }),
  });
}

export function clearHoldings() {
  return request("/users/me/holdings", { method: "DELETE" });
}
