import { Routes, Route, NavLink } from 'react-router-dom'
import { useI18n } from './i18n'
import Dashboard from './pages/Dashboard'
import Products from './pages/Products'
import ProductDetail from './pages/ProductDetail'
import Matching from './pages/Matching'
import Chat from './pages/Chat'
import Trends from './pages/Trends'

export default function App() {
  const { lang, setLang } = useI18n()

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <h1>Zenline</h1>
          <span>Product Matcher</span>
        </div>
        <nav className="sidebar-nav">
          <NavLink to="/">
            <span className="nav-icon">
              <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <rect x="1" y="1" width="7" height="7" rx="1.5"/>
                <rect x="10" y="1" width="7" height="4" rx="1.5"/>
                <rect x="1" y="10" width="7" height="4" rx="1.5"/>
                <rect x="10" y="7" width="7" height="7" rx="1.5"/>
              </svg>
            </span>
            Dashboard
          </NavLink>
          <NavLink to="/products">
            <span className="nav-icon">
              <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <rect x="2" y="2" width="14" height="14" rx="2"/>
                <line x1="2" y1="7" x2="16" y2="7"/>
                <line x1="7" y1="7" x2="7" y2="16"/>
              </svg>
            </span>
            Products
          </NavLink>
          <NavLink to="/matching">
            <span className="nav-icon">
              <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="5" cy="5" r="3"/>
                <circle cx="13" cy="13" r="3"/>
                <line x1="7.5" y1="7.5" x2="10.5" y2="10.5"/>
              </svg>
            </span>
            Matching
          </NavLink>
          <NavLink to="/trends">
            <span className="nav-icon">
              <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="2 14 6 8 10 11 16 3"/>
                <polyline points="12 3 16 3 16 7"/>
              </svg>
            </span>
            Trends
          </NavLink>
          <NavLink to="/chat">
            <span className="nav-icon">
              <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <rect x="1" y="1" width="16" height="12" rx="3"/>
                <path d="M5 16L8 13H10L13 16"/>
                <line x1="5" y1="6" x2="13" y2="6"/>
                <line x1="5" y1="9" x2="10" y2="9"/>
              </svg>
            </span>
            Chat
          </NavLink>
        </nav>
        <div className="lang-toggle">
          <button
            className={`lang-btn ${lang === 'en' ? 'active' : ''}`}
            onClick={() => setLang('en')}
          >EN</button>
          <button
            className={`lang-btn ${lang === 'de' ? 'active' : ''}`}
            onClick={() => setLang('de')}
          >DE</button>
        </div>
        <div className="sidebar-footer">
          Zenline Hackathon 2026
        </div>
      </aside>
      <main className="main-content">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/products" element={<Products />} />
          <Route path="/products/:ref" element={<ProductDetail />} />
          <Route path="/matching" element={<Matching />} />
          <Route path="/trends" element={<Trends />} />
          <Route path="/chat" element={<Chat />} />
        </Routes>
      </main>
    </div>
  )
}