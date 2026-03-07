import { useEffect, useState } from 'react'
import { getCategories } from '../services/api'
import { STRATEGIES } from '../strategies'

const STRATEGY_ICONS: Record<string, JSX.Element> = {
  ean: (
    <svg width="36" height="36" viewBox="0 0 36 36" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round">
      <rect x="4" y="6" width="28" height="24" rx="3" />
      <line x1="9" y1="12" x2="9" y2="24" />
      <line x1="12" y1="12" x2="12" y2="24" />
      <line x1="16" y1="12" x2="16" y2="24" />
      <line x1="18" y1="12" x2="18" y2="24" />
      <line x1="22" y1="12" x2="22" y2="24" />
      <line x1="24" y1="12" x2="24" y2="24" />
      <line x1="27" y1="12" x2="27" y2="24" />
    </svg>
  ),
  model_number: (
    <svg width="36" height="36" viewBox="0 0 36 36" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round">
      <rect x="4" y="8" width="28" height="20" rx="3" />
      <text x="10" y="22" fontSize="10" fontWeight="600" fill="currentColor" stroke="none" fontFamily="monospace">A-42</text>
      <circle cx="28" cy="12" r="2" fill="currentColor" stroke="none" opacity="0.3" />
    </svg>
  ),
  fuzzy: (
    <svg width="36" height="36" viewBox="0 0 36 36" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round">
      <path d="M6 18C10 12 14 24 18 18C22 12 26 24 30 18" opacity="0.3" />
      <path d="M6 18C10 14 14 22 18 18C22 14 26 22 30 18" />
      <line x1="8" y1="28" x2="16" y2="28" />
      <line x1="20" y1="28" x2="28" y2="28" opacity="0.4" />
      <line x1="8" y1="8" x2="14" y2="8" />
      <line x1="22" y1="8" x2="28" y2="8" opacity="0.4" />
    </svg>
  ),
  embedding: (
    <svg width="36" height="36" viewBox="0 0 36 36" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="10" cy="10" r="3" />
      <circle cx="26" cy="10" r="3" />
      <circle cx="18" cy="26" r="3" />
      <circle cx="10" cy="26" r="3" opacity="0.3" />
      <circle cx="26" cy="26" r="3" opacity="0.3" />
      <line x1="12" y1="12" x2="16" y2="24" />
      <line x1="24" y1="12" x2="20" y2="24" />
      <line x1="13" y1="10" x2="23" y2="10" opacity="0.3" />
    </svg>
  ),
  vision: (
    <svg width="36" height="36" viewBox="0 0 36 36" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 18C4 18 10 8 18 8C26 8 32 18 32 18C32 18 26 28 18 28C10 28 4 18 4 18Z" />
      <circle cx="18" cy="18" r="5" />
      <circle cx="18" cy="18" r="2" fill="currentColor" stroke="none" />
    </svg>
  ),
  llm: (
    <svg width="36" height="36" viewBox="0 0 36 36" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round">
      <rect x="6" y="4" width="24" height="20" rx="4" />
      <path d="M12 11H24" opacity="0.3" />
      <path d="M12 15H20" opacity="0.3" />
      <path d="M14 24L10 32" />
      <path d="M22 24L26 32" />
      <circle cx="14" cy="12" r="1.5" fill="currentColor" stroke="none" />
      <circle cx="22" cy="12" r="1.5" fill="currentColor" stroke="none" />
    </svg>
  ),
  scrape: (
    <svg width="36" height="36" viewBox="0 0 36 36" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="18" cy="18" r="13" />
      <ellipse cx="18" cy="18" rx="6" ry="13" />
      <line x1="5" y1="13" x2="31" y2="13" />
      <line x1="5" y1="23" x2="31" y2="23" />
      <line x1="18" y1="5" x2="18" y2="31" />
    </svg>
  ),
}

export default function Dashboard() {
  const [categories, setCategories] = useState<string[]>([])
  const [enabledStrategies, setEnabledStrategies] = useState<Set<string>>(() =>
    new Set(STRATEGIES.filter((s) => s.defaultEnabled).map((s) => s.id))
  )

  useEffect(() => {
    getCategories().then(setCategories).catch(() => setCategories([]))
  }, [])

  const toggleStrategy = (id: string) => {
    setEnabledStrategies((prev) => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }

  const enableAll = () => setEnabledStrategies(new Set(STRATEGIES.map((s) => s.id)))
  const disableAll = () => setEnabledStrategies(new Set())

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
            <div className="stat-label">Active Strategies</div>
            <div className="stat-value">{enabledStrategies.size}<span style={{ fontSize: '1rem', color: 'var(--stone-500)', fontFamily: 'DM Sans, sans-serif' }}> / {STRATEGIES.length}</span></div>
            <div className="stat-note">Toggle below to configure</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Retailers</div>
            <div className="stat-value">6+</div>
            <div className="stat-note">Austrian electronics retailers</div>
          </div>
        </div>

        {/* Strategies Section */}
        <div className="card" style={{ marginBottom: '24px' }}>
          <div className="card-header">
            <span className="card-title">Matching Strategies</span>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button className="btn btn-secondary" style={{ padding: '5px 12px', fontSize: '0.78rem' }} onClick={enableAll}>
                Enable all
              </button>
              <button className="btn btn-secondary" style={{ padding: '5px 12px', fontSize: '0.78rem' }} onClick={disableAll}>
                Disable all
              </button>
            </div>
          </div>
          <div className="strategy-grid">
            {STRATEGIES.map((s) => {
              const enabled = enabledStrategies.has(s.id)
              return (
                <div
                  key={s.id}
                  className={`strategy-card ${enabled ? 'strategy-enabled' : 'strategy-disabled'}`}
                  onClick={() => toggleStrategy(s.id)}
                >
                  <div className="strategy-header">
                    <div className={`strategy-icon ${enabled ? '' : 'strategy-icon-dim'}`}>
                      {STRATEGY_ICONS[s.id]}
                    </div>
                    <label className="strategy-toggle">
                      <input
                        type="checkbox"
                        checked={enabled}
                        onChange={() => toggleStrategy(s.id)}
                        onClick={(e) => e.stopPropagation()}
                      />
                      <span className="toggle-slider" />
                    </label>
                  </div>
                  <div className="strategy-body">
                    <div className="strategy-name">
                      <span className="strategy-priority">{s.priority}</span>
                      {s.name}
                    </div>
                    <p className="strategy-desc">{s.description}</p>
                  </div>
                </div>
              )
            })}
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
