import { useEffect, useState } from 'react'
import { getCategories, runMatching } from '../services/api'
import type { MatchResult } from '../types/product'

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

  return (
    <div>
      <h1>Run Matching Pipeline</h1>

      <div style={{ display: 'flex', gap: '1rem', margin: '1rem 0', alignItems: 'center', flexWrap: 'wrap' }}>
        <select value={selectedCategory} onChange={(e) => setSelectedCategory(e.target.value)}
          style={{ padding: '0.5rem', borderRadius: 4 }}>
          {categories.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>

        <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          Fuzzy threshold:
          <input type="range" min={50} max={100} value={threshold}
            onChange={(e) => setThreshold(Number(e.target.value))} />
          <span>{threshold}%</span>
        </label>

        <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <input type="checkbox" checked={useLlm} onChange={(e) => setUseLlm(e.target.checked)} />
          Use LLM fallback
        </label>

        <button onClick={handleRun} disabled={loading}
          style={{ padding: '0.5rem 1.5rem', background: '#1a1a2e', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer' }}>
          {loading ? 'Running...' : 'Run Matching'}
        </button>
      </div>

      {result && (
        <div style={{ marginTop: '1.5rem' }}>
          <h2>Results: {result.category}</h2>
          <div style={{ display: 'flex', gap: '2rem', margin: '1rem 0' }}>
            <div style={{ background: '#fff', padding: '1rem 2rem', borderRadius: 8 }}>
              <div style={{ fontSize: '2rem', fontWeight: 'bold' }}>{result.total_sources}</div>
              <div style={{ color: '#888' }}>Source Products</div>
            </div>
            <div style={{ background: '#fff', padding: '1rem 2rem', borderRadius: 8 }}>
              <div style={{ fontSize: '2rem', fontWeight: 'bold' }}>{result.total_matches}</div>
              <div style={{ color: '#888' }}>Matches Found</div>
            </div>
            <div style={{ background: '#fff', padding: '1rem 2rem', borderRadius: 8 }}>
              <div style={{ fontSize: '2rem', fontWeight: 'bold' }}>
                {result.submissions.filter((s) => s.competitors.length > 0).length}
              </div>
              <div style={{ color: '#888' }}>Products with Matches</div>
            </div>
          </div>

          <table style={{ width: '100%', borderCollapse: 'collapse', background: '#fff', marginTop: '1rem' }}>
            <thead>
              <tr style={{ background: '#eee', textAlign: 'left' }}>
                <th style={{ padding: '0.5rem' }}>Source Ref</th>
                <th style={{ padding: '0.5rem' }}>Matches</th>
                <th style={{ padding: '0.5rem' }}>Best Method</th>
                <th style={{ padding: '0.5rem' }}>Best Confidence</th>
              </tr>
            </thead>
            <tbody>
              {result.submissions.map((s) => {
                const best = s.competitors.sort((a, b) => b.confidence - a.confidence)[0]
                return (
                  <tr key={s.source_reference} style={{ borderBottom: '1px solid #eee' }}>
                    <td style={{ padding: '0.5rem', fontFamily: 'monospace' }}>{s.source_reference}</td>
                    <td style={{ padding: '0.5rem' }}>{s.competitors.length}</td>
                    <td style={{ padding: '0.5rem' }}>{best?.match_method ?? '-'}</td>
                    <td style={{ padding: '0.5rem' }}>
                      {best ? `${(best.confidence * 100).toFixed(0)}%` : '-'}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
