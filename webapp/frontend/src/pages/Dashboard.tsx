import { useEffect, useState, useMemo } from 'react'
import { getDashboard, getCategories } from '../services/api'
import { STRATEGIES } from '../strategies'
import { useStrategies } from '../StrategyContext'
import { useI18n } from '../i18n'
import type { DashboardStats } from '../types/product'

const STRATEGY_HINTS = [
  { condition: (ids: Set<string>) => ids.size === 0, text: "Everything's off! Enable a few strategies and see what matches pop up.", icon: '~' },
  { condition: (ids: Set<string>) => ids.size === STRATEGIES.length, text: "All engines running! Try disabling a few to see which ones pull the most weight.", icon: '>' },
  { condition: (ids: Set<string>) => ids.has('ean') && ids.size === 1, text: "EAN-only is precise but narrow. Add Fuzzy or Embedding to catch more matches.", icon: '+' },
  { condition: (ids: Set<string>) => !ids.has('llm') && ids.size >= 3, text: "Tip: Enable LLM Verify to let Claude double-check uncertain matches.", icon: '?' },
  { condition: (ids: Set<string>) => !ids.has('vision') && ids.has('embedding'), text: "You've got text embeddings on. Try adding Vision for image-based matching too!", icon: '*' },
  { condition: (ids: Set<string>) => ids.has('scrape') && !ids.has('ean'), text: "Scraping works best with EAN enabled -- scraped products often have barcodes.", icon: '!' },
  { condition: (ids: Set<string>) => ids.size >= 2 && ids.size <= 4, text: "Nice combo! Toggle strategies on and off to experiment with precision vs. recall.", icon: '~' },
]

const STRATEGY_ICONS: Record<string, JSX.Element> = {
  ean: (
    <svg width="36" height="36" viewBox="0 0 36 36" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round">
      <rect x="4" y="6" width="28" height="24" rx="3" />
      <line x1="9" y1="12" x2="9" y2="24" /><line x1="12" y1="12" x2="12" y2="24" />
      <line x1="16" y1="12" x2="16" y2="24" /><line x1="18" y1="12" x2="18" y2="24" />
      <line x1="22" y1="12" x2="22" y2="24" /><line x1="24" y1="12" x2="24" y2="24" />
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
      <line x1="8" y1="28" x2="16" y2="28" /><line x1="20" y1="28" x2="28" y2="28" opacity="0.4" />
      <line x1="8" y1="8" x2="14" y2="8" /><line x1="22" y1="8" x2="28" y2="8" opacity="0.4" />
    </svg>
  ),
  embedding: (
    <svg width="36" height="36" viewBox="0 0 36 36" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="10" cy="10" r="3" /><circle cx="26" cy="10" r="3" /><circle cx="18" cy="26" r="3" />
      <circle cx="10" cy="26" r="3" opacity="0.3" /><circle cx="26" cy="26" r="3" opacity="0.3" />
      <line x1="12" y1="12" x2="16" y2="24" /><line x1="24" y1="12" x2="20" y2="24" />
      <line x1="13" y1="10" x2="23" y2="10" opacity="0.3" />
    </svg>
  ),
  vision: (
    <svg width="36" height="36" viewBox="0 0 36 36" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 18C4 18 10 8 18 8C26 8 32 18 32 18C32 18 26 28 18 28C10 28 4 18 4 18Z" />
      <circle cx="18" cy="18" r="5" /><circle cx="18" cy="18" r="2" fill="currentColor" stroke="none" />
    </svg>
  ),
  llm: (
    <svg width="36" height="36" viewBox="0 0 36 36" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round">
      <rect x="6" y="4" width="24" height="20" rx="4" />
      <path d="M12 11H24" opacity="0.3" /><path d="M12 15H20" opacity="0.3" />
      <path d="M14 24L10 32" /><path d="M22 24L26 32" />
      <circle cx="14" cy="12" r="1.5" fill="currentColor" stroke="none" />
      <circle cx="22" cy="12" r="1.5" fill="currentColor" stroke="none" />
    </svg>
  ),
  scrape: (
    <svg width="36" height="36" viewBox="0 0 36 36" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="18" cy="18" r="13" /><ellipse cx="18" cy="18" rx="6" ry="13" />
      <line x1="5" y1="13" x2="31" y2="13" /><line x1="5" y1="23" x2="31" y2="23" />
      <line x1="18" y1="5" x2="18" y2="31" />
    </svg>
  ),
}

const CONF_COLORS: Record<string, string> = {
  excellent: 'var(--success)',
  high: 'var(--accent)',
  medium: 'var(--warning)',
  low: 'var(--info)',
}

export default function Dashboard() {
  const [categories, setCategories] = useState<string[]>([])
  const [dashboard, setDashboard] = useState<DashboardStats | null>(null)
  const { enabledStrategies, toggleStrategy, enableAll, disableAll } = useStrategies()
  const { t } = useI18n()

  useEffect(() => {
    getCategories().then(setCategories).catch(() => setCategories([]))
    getDashboard().then(setDashboard).catch(() => {})
  }, [])

  const d = dashboard

  const hint = useMemo(() => {
    for (const h of STRATEGY_HINTS) {
      if (h.condition(enabledStrategies)) return h
    }
    return null
  }, [enabledStrategies])

  return (
    <>
      <div className="page-header">
        <h1>{t('dashboard.title')}</h1>
        <p>{t('dashboard.subtitle')}</p>
      </div>
      <div className="page-body">
        {/* Live Stats */}
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-label">{t('stats.source_products')}</div>
            <div className="stat-value">{d?.source_count ?? '--'}</div>
            <div className="stat-note">{t('stats.to_be_matched')}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">{t('stats.target_pool')}</div>
            <div className="stat-value">{d?.target_count ?? '--'}</div>
            <div className="stat-note">From {d?.retailers?.length ?? 0} retailers</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">{t('stats.matches_found')}</div>
            <div className="stat-value">{d?.match_count ?? '--'}</div>
            <div className="stat-note">{d?.sources_matched ?? 0} {t('stats.sources_covered')}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">{t('stats.coverage')}</div>
            <div className="stat-value">{d ? `${d.coverage_pct.toFixed(0)}%` : '--'}</div>
            <div className="stat-note">
              {d && d.source_count > 0
                ? `${d.sources_matched} / ${d.source_count} sources`
                : t('stats.no_data')}
            </div>
          </div>
        </div>

        {/* Method Breakdown + Confidence Distribution */}
        {d && (d.methods.length > 0 || d.match_count > 0) && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '24px' }}>
            {/* Method breakdown */}
            <div className="card">
              <div className="card-header">
                <span className="card-title">{t('card.methods')}</span>
              </div>
              {d.methods.length > 0 ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {d.methods.map((m) => {
                    const pct = d.match_count > 0 ? (m.count / d.match_count) * 100 : 0
                    return (
                      <div key={m.method} style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <span style={{ minWidth: '100px', fontSize: '0.84rem', fontWeight: 500, color: 'var(--stone-700)' }}>
                          {m.label}
                        </span>
                        <div style={{ flex: 1, height: '6px', background: 'var(--cream-200)', borderRadius: '3px', overflow: 'hidden' }}>
                          <div style={{ width: `${pct}%`, height: '100%', background: 'var(--accent)', borderRadius: '3px', transition: 'width 0.3s' }} />
                        </div>
                        <span className="mono" style={{ minWidth: '40px', textAlign: 'right' }}>{m.count}</span>
                      </div>
                    )
                  })}
                </div>
              ) : (
                <p style={{ color: 'var(--stone-500)', fontSize: '0.875rem' }}>Run matching to see breakdown</p>
              )}
            </div>

            {/* Confidence distribution */}
            <div className="card">
              <div className="card-header">
                <span className="card-title">{t('card.confidence')}</span>
              </div>
              {d.match_count > 0 ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {(['excellent', 'high', 'medium', 'low'] as const).map((level) => {
                    const count = d.confidence_distribution[level]
                    const pct = d.match_count > 0 ? (count / d.match_count) * 100 : 0
                    return (
                      <div key={level} style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <span style={{ minWidth: '80px', fontSize: '0.84rem', fontWeight: 500, color: 'var(--stone-700)', textTransform: 'capitalize' }}>
                          {level}
                        </span>
                        <div style={{ flex: 1, height: '6px', background: 'var(--cream-200)', borderRadius: '3px', overflow: 'hidden' }}>
                          <div style={{ width: `${pct}%`, height: '100%', background: CONF_COLORS[level], borderRadius: '3px', transition: 'width 0.3s' }} />
                        </div>
                        <span className="mono" style={{ minWidth: '40px', textAlign: 'right' }}>{count}</span>
                      </div>
                    )
                  })}
                </div>
              ) : (
                <p style={{ color: 'var(--stone-500)', fontSize: '0.875rem' }}>No matches yet</p>
              )}
            </div>
          </div>
        )}

        {/* Top Brands */}
        {d && d.brands.length > 0 && (
          <div className="card" style={{ marginBottom: '24px' }}>
            <div className="card-header">
              <span className="card-title">{t('card.top_brands')}</span>
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
              {d.brands.slice(0, 12).map((b) => (
                <div key={b.brand} style={{
                  padding: '8px 14px',
                  background: 'var(--cream-100)',
                  border: '1px solid var(--cream-300)',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '0.84rem',
                }}>
                  <strong style={{ color: 'var(--stone-800)' }}>{b.brand}</strong>
                  <span style={{ color: 'var(--stone-500)', marginLeft: '8px' }}>
                    {b.matched_sources} matched &middot; {b.total_matches} total
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Recent Runs */}
        {d && d.recent_runs.length > 0 && (
          <div className="card" style={{ marginBottom: '24px' }}>
            <div className="card-header">
              <span className="card-title">{t('card.recent_runs')}</span>
            </div>
            <div className="table-wrapper" style={{ border: 'none', boxShadow: 'none' }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Category</th>
                    <th>Sources</th>
                    <th>Matches</th>
                    <th>Covered</th>
                    <th>When</th>
                  </tr>
                </thead>
                <tbody>
                  {d.recent_runs.map((run, i) => (
                    <tr key={i}>
                      <td><span className="badge badge-accent">{run.category}</span></td>
                      <td>{run.source_count}</td>
                      <td><strong>{run.match_count}</strong></td>
                      <td>{run.sources_matched}</td>
                      <td><span className="mono">{new Date(run.created_at).toLocaleString()}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Strategies Section */}
        <div className="card" style={{ marginBottom: '24px' }}>
          <div className="card-header">
            <div>
              <span className="card-title">{t('strategies.title')}</span>
              <span style={{ fontSize: '0.78rem', color: 'var(--stone-500)', marginLeft: '10px' }}>
                {enabledStrategies.size} / {STRATEGIES.length} {t('strategies.active')}
              </span>
            </div>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button className="btn btn-secondary" style={{ padding: '5px 12px', fontSize: '0.78rem' }} onClick={enableAll}>
                {t('strategies.enable_all')}
              </button>
              <button className="btn btn-secondary" style={{ padding: '5px 12px', fontSize: '0.78rem' }} onClick={disableAll}>
                {t('strategies.disable_all')}
              </button>
            </div>
          </div>
          {hint && (
            <div className="strategy-hint">
              <span className="strategy-hint-icon">{hint.icon}</span>
              <span>{hint.text}</span>
            </div>
          )}
          <div className="strategy-grid">
            {STRATEGIES.map((s) => {
              const enabled = enabledStrategies.has(s.id)
              return (
                <div
                  key={s.id}
                  className={`strategy-card ${enabled ? 'strategy-enabled' : 'strategy-disabled'}`}
                  data-strategy={s.id}
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
              <span className="card-title">{t('card.categories')}</span>
            </div>
            {categories.length === 0 ? (
              <div className="empty-state">
                <div className="empty-icon">
                  <svg width="40" height="40" viewBox="0 0 40 40" fill="none" stroke="currentColor" strokeWidth="1.5" opacity="0.3">
                    <rect x="4" y="4" width="32" height="32" rx="4"/>
                    <line x1="12" y1="16" x2="28" y2="16"/><line x1="12" y1="22" x2="24" y2="22"/><line x1="12" y1="28" x2="20" y2="28"/>
                  </svg>
                </div>
                <h3>No categories loaded</h3>
                <p>Upload source and target data via the API or place JSON files in the data directory.</p>
              </div>
            ) : (
              <ul style={{ listStyle: 'none' }}>
                {categories.map((c) => (
                  <li key={c} style={{
                    padding: '10px 0', borderBottom: '1px solid var(--cream-200)',
                    display: 'flex', alignItems: 'center', gap: '10px',
                    fontSize: '0.9rem', color: 'var(--stone-700)',
                  }}>
                    <span className="badge badge-accent">{c}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {/* Retailers */}
          <div className="card">
            <div className="card-header">
              <span className="card-title">{t('card.retailers')}</span>
            </div>
            {d && d.retailers.length > 0 ? (
              <ul style={{ listStyle: 'none' }}>
                {d.retailers.map((r) => (
                  <li key={r} style={{
                    padding: '10px 0', borderBottom: '1px solid var(--cream-200)',
                    display: 'flex', alignItems: 'center', gap: '10px',
                    fontSize: '0.9rem', color: 'var(--stone-700)',
                  }}>
                    <span className="badge badge-info">{r}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="empty-state">
                <h3>No retailer data</h3>
                <p>Run the pipeline to discover retailers from target products.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  )
}