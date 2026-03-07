import { useEffect, useState } from 'react'
import { getCategories, runMatching } from '../services/api'
import type { MatchResult } from '../types/product'

function confidenceLevel(val: number) {
  if (val >= 0.85) return 'high'
  if (val >= 0.65) return 'medium'
  return 'low'
}

function methodBadge(method: string) {
  const map: Record<string, string> = {
    ean: 'badge-success',
    model_number: 'badge-success',
    fuzzy: 'badge-warning',
    embedding: 'badge-info',
    vision: 'badge-info',
    llm: 'badge-accent',
  }
  const cls = Object.entries(map).find(([k]) => method.toLowerCase().includes(k))?.[1] ?? 'badge-info'
  return cls
}

export default function Matching() {
  const [categories, setCategories] = useState<string[]>([])
  const [selectedCategory, setSelectedCategory] = useState('')
  const [useLlm, setUseLlm] = useState(false)
  const [threshold, setThreshold] = useState(75)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<MatchResult | null>(null)

  useEffect(() => {
    getCategories().then((cats) => {
      setCategories(cats)
      if (cats.length > 0) setSelectedCategory(cats[0])
    }).catch(() => {})
  }, [])

  const handleRun = async () => {
    if (!selectedCategory) return
    setLoading(true)
    setResult(null)
    try {
      const res = await runMatching(selectedCategory, useLlm, threshold)
      setResult(res)
    } catch {
      alert('Matching failed. Is the matcher service running?')
    } finally {
      setLoading(false)
    }
  }

  const matchedCount = result
    ? result.submissions.filter((s) => s.competitors.length > 0).length
    : 0

  return (
    <>
      <div className="page-header">
        <h1>Matching Pipeline</h1>
        <p>Configure and run the multi-strategy product matching engine</p>
      </div>
      <div className="page-body">
        <div className="card" style={{ marginBottom: '24px' }}>
          <div className="toolbar" style={{ marginBottom: 0 }}>
            <select
              className="select-field"
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
            >
              {categories.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>

            <div className="divider" />

            <div className="range-group">
              <label>Fuzzy threshold</label>
              <input
                type="range"
                className="range-field"
                min={50}
                max={100}
                value={threshold}
                onChange={(e) => setThreshold(Number(e.target.value))}
              />
              <span className="range-value">{threshold}%</span>
            </div>

            <div className="divider" />

            <label className="checkbox-group">
              <input
                type="checkbox"
                checked={useLlm}
                onChange={(e) => setUseLlm(e.target.checked)}
              />
              LLM fallback
            </label>

            <div style={{ flex: 1 }} />

            <button
              className="btn btn-primary"
              onClick={handleRun}
              disabled={loading}
            >
              {loading && <span className="spinner" />}
              {loading ? 'Running...' : 'Run Matching'}
            </button>
          </div>
        </div>

        {result && (
          <>
            <div className="stats-grid">
              <div className="stat-card">
                <div className="stat-label">Source Products</div>
                <div className="stat-value">{result.total_sources}</div>
              </div>
              <div className="stat-card">
                <div className="stat-label">Total Matches</div>
                <div className="stat-value">{result.total_matches}</div>
              </div>
              <div className="stat-card">
                <div className="stat-label">Products Matched</div>
                <div className="stat-value">{matchedCount}</div>
                <div className="stat-note">
                  {result.total_sources > 0
                    ? `${((matchedCount / result.total_sources) * 100).toFixed(0)}% coverage`
                    : ''}
                </div>
              </div>
              <div className="stat-card">
                <div className="stat-label">Category</div>
                <div className="stat-value" style={{ fontSize: '1.25rem', marginTop: '10px' }}>
                  {result.category}
                </div>
              </div>
            </div>

            <div className="table-wrapper">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Source Reference</th>
                    <th>Matches</th>
                    <th>Best Method</th>
                    <th>Confidence</th>
                  </tr>
                </thead>
                <tbody>
                  {result.submissions.map((s) => {
                    const best = [...s.competitors].sort((a, b) => b.confidence - a.confidence)[0]
                    const conf = best?.confidence ?? 0
                    const level = confidenceLevel(conf)
                    return (
                      <tr key={s.source_reference}>
                        <td><span className="mono">{s.source_reference}</span></td>
                        <td>
                          {s.competitors.length > 0
                            ? <span className="badge badge-success">{s.competitors.length}</span>
                            : <span style={{ color: 'var(--cream-400)' }}>0</span>
                          }
                        </td>
                        <td>
                          {best
                            ? <span className={`badge ${methodBadge(best.match_method)}`}>{best.match_method}</span>
                            : <span style={{ color: 'var(--cream-400)' }}>--</span>
                          }
                        </td>
                        <td>
                          {best ? (
                            <div className="confidence-bar">
                              <span className="mono" style={{ minWidth: '36px' }}>
                                {(conf * 100).toFixed(0)}%
                              </span>
                              <div className="confidence-track">
                                <div
                                  className={`confidence-fill ${level}`}
                                  style={{ width: `${conf * 100}%` }}
                                />
                              </div>
                            </div>
                          ) : (
                            <span style={{ color: 'var(--cream-400)' }}>--</span>
                          )}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </>
        )}

        {!result && !loading && (
          <div className="card">
            <div className="empty-state">
              <div className="empty-icon">
                <svg width="48" height="48" viewBox="0 0 48 48" fill="none" stroke="currentColor" strokeWidth="1.5" opacity="0.3">
                  <circle cx="18" cy="18" r="10"/>
                  <circle cx="30" cy="30" r="10"/>
                  <line x1="25" y1="25" x2="22" y2="22"/>
                </svg>
              </div>
              <h3>Ready to match</h3>
              <p>Select a category, configure your parameters, and hit Run Matching to start the pipeline.</p>
            </div>
          </div>
        )}
      </div>
    </>
  )
}