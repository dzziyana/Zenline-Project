import { useEffect, useState } from 'react'
import { getCategories } from '../services/api'

export default function Dashboard() {
  const [categories, setCategories] = useState<string[]>([])

  useEffect(() => {
    getCategories().then(setCategories).catch(() => setCategories([]))
  }, [])

  return (
    <>
      <div className="page-header">
        <h1>Dashboard</h1>
        <p>Overview of your product matching workspace</p>
      </div>
      <div className="page-body">
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-label">Categories</div>
            <div className="stat-value">{categories.length}</div>
            <div className="stat-note">Available to match</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Strategies</div>
            <div className="stat-value">7</div>
            <div className="stat-note">EAN, fuzzy, embedding, vision, LLM, scrape, model#</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Retailers</div>
            <div className="stat-value">6+</div>
            <div className="stat-note">Austrian electronics retailers</div>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
          <div className="card">
            <div className="card-header">
              <span className="card-title">Categories</span>
            </div>
            {categories.length === 0 ? (
              <div className="empty-state">
                <div className="empty-icon">
                  <svg width="40" height="40" viewBox="0 0 40 40" fill="none" stroke="currentColor" strokeWidth="1.5" opacity="0.3">
                    <rect x="4" y="4" width="32" height="32" rx="4"/>
                    <line x1="12" y1="16" x2="28" y2="16"/>
                    <line x1="12" y1="22" x2="24" y2="22"/>
                    <line x1="12" y1="28" x2="20" y2="28"/>
                  </svg>
                </div>
                <h3>No categories loaded</h3>
                <p>Upload source and target data via the API or place JSON files in the data directory.</p>
              </div>
            ) : (
              <ul style={{ listStyle: 'none' }}>
                {categories.map((c) => (
                  <li key={c} style={{
                    padding: '10px 0',
                    borderBottom: '1px solid var(--cream-200)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px',
                    fontSize: '0.9rem',
                    color: 'var(--stone-700)',
                  }}>
                    <span className="badge badge-accent">{c}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="card">
            <div className="card-header">
              <span className="card-title">Quick Start</span>
            </div>
            <ol className="steps-list">
              <li>Download source products and target pool JSON from the hackathon platform</li>
              <li>Place them in <code style={{
                background: 'var(--cream-200)',
                padding: '2px 6px',
                borderRadius: '4px',
                fontSize: '0.84rem',
                fontFamily: 'monospace',
              }}>data/</code> or upload via the API</li>
              <li>Go to <strong>Products</strong> to browse and search the catalog</li>
              <li>Go to <strong>Matching</strong> to run the pipeline and generate submissions</li>
            </ol>
          </div>
        </div>
      </div>
    </>
  )
}
