import { Routes, Route, NavLink } from "react-router-dom";
import { Component, useState, type ReactNode } from "react";
import { useI18n } from "./i18n";
import { useCurrency, type Currency } from "./CurrencyContext";
import { useAuth } from "./AuthContext";
import Dashboard from "./pages/Dashboard";
import Products from "./pages/Products";
import ProductDetail from "./pages/ProductDetail";
import Matching from "./pages/Matching";
import Chat from "./pages/Chat";
import Trends from "./pages/Trends";
import Scraping from "./pages/Scraping";

class ErrorBoundary extends Component<
  { children: ReactNode },
  { error: Error | null }
> {
  state = { error: null as Error | null };
  static getDerivedStateFromError(error: Error) {
    return { error };
  }
  render() {
    if (this.state.error) {
      return (
        <div style={{ padding: 40, color: "#ef4444" }}>
          <h2>Something went wrong</h2>
          <pre style={{ whiteSpace: "pre-wrap", fontSize: "0.85rem" }}>
            {this.state.error.message}
            {"\n"}
            {this.state.error.stack}
          </pre>
          <button
            onClick={() => this.setState({ error: null })}
            style={{ marginTop: 16 }}
          >
            Try again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

function LoginModal({ onClose }: { onClose: () => void }) {
  const { login } = useAuth();
  const [key, setKey] = useState("");
  const [error, setError] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(false);
    const ok = await login(key);
    setLoading(false);
    if (ok) onClose();
    else setError(true);
  };

  return (
    <div className="login-overlay" onClick={onClose}>
      <div className="login-modal" onClick={(e) => e.stopPropagation()}>
        <h3>Sign In</h3>
        <p
          style={{
            fontSize: "0.82rem",
            color: "var(--stone-400)",
            margin: "0 0 16px",
          }}
        >
          Enter your API key to access write operations.
        </p>
        <form onSubmit={handleSubmit}>
          <input
            type="password"
            placeholder="API key"
            value={key}
            onChange={(e) => setKey(e.target.value)}
            autoFocus
            style={{
              width: "100%",
              padding: "10px 12px",
              border: error
                ? "1px solid var(--red-400, #ef4444)"
                : "1px solid var(--cream-400)",
              borderRadius: "var(--radius-sm)",
              background: "var(--cream-50)",
              fontSize: "0.88rem",
              outline: "none",
            }}
          />
          {error && (
            <p
              style={{
                color: "var(--red-400, #ef4444)",
                fontSize: "0.78rem",
                margin: "6px 0 0",
              }}
            >
              Invalid API key. Please try again.
            </p>
          )}
          <div
            style={{
              display: "flex",
              gap: 8,
              marginTop: 16,
              justifyContent: "flex-end",
            }}
          >
            <button type="button" onClick={onClose} className="btn-secondary">
              Cancel
            </button>
            <button
              type="submit"
              className="btn-primary"
              disabled={loading || !key}
            >
              {loading ? "Verifying..." : "Sign In"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function App() {
  const { lang, setLang, t } = useI18n();
  const { currency, setCurrency } = useCurrency();
  const { isAuthenticated, user, logout } = useAuth();
  const [showLogin, setShowLogin] = useState(false);
  const currencies: Currency[] = ["EUR", "USD", "GBP", "CHF"];

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <h1>Zenline</h1>
          <span>{t("sidebar.subtitle")}</span>
        </div>
        <nav className="sidebar-nav">
          <NavLink to="/">
            <span className="nav-icon">
              <svg
                width="18"
                height="18"
                viewBox="0 0 18 18"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <rect x="1" y="1" width="7" height="7" rx="1.5" />
                <rect x="10" y="1" width="7" height="4" rx="1.5" />
                <rect x="1" y="10" width="7" height="4" rx="1.5" />
                <rect x="10" y="7" width="7" height="7" rx="1.5" />
              </svg>
            </span>
            {t("nav.dashboard")}
          </NavLink>
          <NavLink to="/products">
            <span className="nav-icon">
              <svg
                width="18"
                height="18"
                viewBox="0 0 18 18"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <rect x="2" y="2" width="14" height="14" rx="2" />
                <line x1="2" y1="7" x2="16" y2="7" />
                <line x1="7" y1="7" x2="7" y2="16" />
              </svg>
            </span>
            {t("nav.products")}
          </NavLink>
          <NavLink to="/matching">
            <span className="nav-icon">
              <svg
                width="18"
                height="18"
                viewBox="0 0 18 18"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <circle cx="5" cy="5" r="3" />
                <circle cx="13" cy="13" r="3" />
                <line x1="7.5" y1="7.5" x2="10.5" y2="10.5" />
              </svg>
            </span>
            {t("nav.matching")}
          </NavLink>
          <NavLink to="/trends">
            <span className="nav-icon">
              <svg
                width="18"
                height="18"
                viewBox="0 0 18 18"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <polyline points="2 14 6 8 10 11 16 3" />
                <polyline points="12 3 16 3 16 7" />
              </svg>
            </span>
            {t("nav.trends")}
          </NavLink>
          <NavLink to="/chat">
            <span className="nav-icon">
              <svg
                width="18"
                height="18"
                viewBox="0 0 18 18"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <rect x="1" y="1" width="16" height="12" rx="3" />
                <path d="M5 16L8 13H10L13 16" />
                <line x1="5" y1="6" x2="13" y2="6" />
                <line x1="5" y1="9" x2="10" y2="9" />
              </svg>
            </span>
            {t("nav.chat")}
          </NavLink>
          <NavLink to="/scraping">
            <span className="nav-icon">
              <svg
                width="18"
                height="18"
                viewBox="0 0 18 18"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <circle cx="9" cy="9" r="7" />
                <ellipse cx="9" cy="9" rx="3" ry="7" />
                <line x1="2" y1="7" x2="16" y2="7" />
                <line x1="2" y1="11" x2="16" y2="11" />
              </svg>
            </span>
            {t("nav.scraping")}
          </NavLink>
        </nav>
        <div className="sidebar-toggles">
          <div className="lang-toggle">
            <button
              className={`lang-btn ${lang === "en" ? "active" : ""}`}
              onClick={() => setLang("en")}
            >
              EN
            </button>
            <button
              className={`lang-btn ${lang === "de" ? "active" : ""}`}
              onClick={() => setLang("de")}
            >
              DE
            </button>
          </div>
          <div className="currency-toggle">
            {currencies.map((c) => (
              <button
                key={c}
                className={`currency-btn ${currency === c ? "active" : ""}`}
                onClick={() => setCurrency(c)}
              >
                {c}
              </button>
            ))}
          </div>
        </div>
        <div className="sidebar-auth">
          {isAuthenticated ? (
            <div className="auth-info">
              <svg
                width="16"
                height="16"
                viewBox="0 0 16 16"
                fill="none"
                stroke="var(--green-500, #22c55e)"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <circle cx="8" cy="5" r="3" />
                <path d="M2 14c0-3.3 2.7-5 6-5s6 1.7 6 5" />
              </svg>
              <span className="auth-user">{user}</span>
              <button className="auth-logout" onClick={logout} title="Sign out">
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 14 14"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M5 1H3a2 2 0 00-2 2v8a2 2 0 002 2h2" />
                  <polyline points="8 10 12 7 8 4" />
                  <line x1="12" y1="7" x2="5" y2="7" />
                </svg>
              </button>
            </div>
          ) : (
            <button
              className="auth-login-btn"
              onClick={() => setShowLogin(true)}
            >
              <svg
                width="16"
                height="16"
                viewBox="0 0 16 16"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <rect x="3" y="7" width="10" height="7" rx="1.5" />
                <path d="M5 7V5a3 3 0 016 0v2" />
              </svg>
              Sign In
            </button>
          )}
        </div>
        <div className="sidebar-footer">{t("sidebar.footer")}</div>
      </aside>
      {showLogin && <LoginModal onClose={() => setShowLogin(false)} />}
      <main className="main-content">
        <ErrorBoundary>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/products" element={<Products />} />
            <Route path="/products/:ref" element={<ProductDetail />} />
            <Route path="/matching" element={<Matching />} />
            <Route path="/trends" element={<Trends />} />
            <Route path="/chat" element={<Chat />} />
            <Route path="/scraping" element={<Scraping />} />
          </Routes>
        </ErrorBoundary>
      </main>
    </div>
  );
}
