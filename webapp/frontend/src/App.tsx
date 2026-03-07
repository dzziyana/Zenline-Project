import { Routes, Route, NavLink } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Products from './pages/Products'
import Matching from './pages/Matching'

export default function App() {
  return (
    <div style={{ minHeight: '100vh' }}>
      <nav style={{
        background: '#1a1a2e',
        color: '#fff',
        padding: '1rem 2rem',
        display: 'flex',
        gap: '2rem',
        alignItems: 'center',
      }}>
        <strong style={{ fontSize: '1.2rem' }}>Zenline Product Matcher</strong>
        <NavLink to="/" style={({ isActive }) => ({
          color: isActive ? '#4fc3f7' : '#ccc',
        })}>Dashboard</NavLink>
        <NavLink to="/products" style={({ isActive }) => ({
          color: isActive ? '#4fc3f7' : '#ccc',
        })}>Products</NavLink>
        <NavLink to="/matching" style={({ isActive }) => ({
          color: isActive ? '#4fc3f7' : '#ccc',
        })}>Matching</NavLink>
      </nav>
      <main style={{ padding: '2rem' }}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/products" element={<Products />} />
          <Route path="/matching" element={<Matching />} />
        </Routes>
      </main>
    </div>
  )
}
