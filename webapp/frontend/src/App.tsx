import { Routes, Route, NavLink } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Products from './pages/Products'
import Matching from './pages/Matching'

export default function App() {
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
        </nav>
        <div className="sidebar-footer">
          Zenline Hackathon 2026
        </div>
      </aside>
      <main className="main-content">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/products" element={<Products />} />
          <Route path="/matching" element={<Matching />} />
        </Routes>
      </main>
    </div>
  )
}
