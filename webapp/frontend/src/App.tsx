import { Routes, Route, NavLink } from "react-router-dom";
import { Component, type ReactNode } from "react";
import { useI18n } from "./i18n";
import { useCurrency, type Currency } from "./CurrencyContext";
import Dashboard from "./pages/Dashboard";
import Products from "./pages/Products";
import ProductDetail from "./pages/ProductDetail";
import Matching from "./pages/Matching";
import Chat from "./pages/Chat";
import Trends from "./pages/Trends";

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

export default function App() {
  const { lang, setLang, t } = useI18n();
  const { currency, setCurrency } = useCurrency();
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
        <div className="sidebar-footer">{t("sidebar.footer")}</div>
      </aside>
      <main className="main-content">
        <ErrorBoundary>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/products" element={<Products />} />
            <Route path="/products/:ref" element={<ProductDetail />} />
            <Route path="/matching" element={<Matching />} />
            <Route path="/trends" element={<Trends />} />
            <Route path="/chat" element={<Chat />} />
          </Routes>
        </ErrorBoundary>
      </main>
    </div>
  );
}
