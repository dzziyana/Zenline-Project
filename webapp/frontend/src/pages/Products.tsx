import { useEffect, useState, useCallback } from 'react'
import { searchProducts, getSources, getBrands, getMatchesForSource } from '../services/api'
import type { SourceProduct, BrandEntry, MatchEntry } from '../types/product'

export default function Products() {
  const [sources, setSources] = useState<SourceProduct[]>([])
  const [search, setSearch] = useState('')
  const [searchResults, setSearchResults] = useState<SourceProduct[] | null>(null)
  const [brands, setBrands] = useState<BrandEntry[]>([])
  const [brandFilter, setBrandFilter] = useState('')
  const [tab, setTab] = useState<'all' | 'unmatched'>('all')
  const [expandedRef, setExpandedRef] = useState<string | null>(null)
  const [expandedMatches, setExpandedMatches] = useState<MatchEntry[]>([])

  useEffect(() => {
    getSources().then((d) => setSources(d.sources)).catch(() => {})
    getBrands().then((d) => setBrands(d.brands)).catch(() => {})
  }, [])

  const doSearch = useCallback((q: string) => {
    if (!q.trim()) {
      setSearchResults(null)
      return
    }
    searchProducts(q, { brand: brandFilter || undefined, limit: 100 })
      .then((d) => setSearchResults(d.results))
      .catch(() => setSearchResults([]))
  }, [brandFilter])

  useEffect(() => {
    const timer = setTimeout(() => doSearch(search), 300)
    return () => clearTimeout(timer)
  }, [search, doSearch])

  const displayProducts = searchResults ?? sources
  const filtered = tab === 'unmatched'
    ? displayProducts.filter((p) => (p.match_count ?? 0) === 0)
    : displayProducts

  const brandFiltered = brandFilter
    ? filtered.filter((p) => p.brand?.toLowerCase() === brandFilter.toLowerCase())
    : filtered

  const handleExpand = async (ref: string) => {
    if (expandedRef === ref) {
      setExpandedRef(null)
      setExpandedMatches([])
      return
    }
    setExpandedRef(ref)
    try {
      const data = await getMatchesForSource(ref)
      setExpandedMatches(data.matches)
    } catch {
      setExpandedMatches([])
    }
  }

  return (
    <>
      <div className="page-header">
        <h1>Products</h1>
        <p>Browse, search, and inspect source products and their matches</p>
      </div>
      <div className="page-body">
        <div className="toolbar">
          <div className="tab-group">
            <button className={`tab-btn ${tab === 'all' ? 'active' : ''}`} onClick={() => setTab('all')}>
              All ({displayProducts.length})
            </button>
            <button className={`tab-btn ${tab === 'unmatched' ? 'active' : ''}`} onClick={() => setTab('unmatched')}>
              Unmatched ({displayProducts.filter((p) => (p.match_count ?? 0) === 0).length})
            </button>
          </div>

          <div className="divider" />

          <select
            className="select-field"
            value={brandFilter}
            onChange={(e) => setBrandFilter(e.target.value)}
          >
            <option value="">All brands</option>
            {brands.map((b) => (
              <option key={b.brand} value={b.brand}>{b.brand} ({b.source_count})</option>
            ))}
          </select>

          <input
            type="text"
            className="input-field search-field"
            placeholder="Search by name, brand, or EAN..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <div className="table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th style={{ width: '32px' }}></th>
                <th>Reference</th>
                <th>Name</th>
                <th>Brand</th>
                <th>EAN</th>
                <th>Retailer</th>
                <th>Price</th>
                <th>Matches</th>
              </tr>
            </thead>
            <tbody>
              {brandFiltered.length === 0 ? (
                <tr>
                  <td colSpan={8}>
                    <div className="empty-state">
                      <h3>No products found</h3>
                      <p>Try adjusting your search or filters.</p>
                    </div>
                  </td>
                </tr>
              ) : (
                brandFiltered.slice(0, 100).map((p) => {
                  const price = p.price_eur ?? p.price
                  const mc = p.match_count ?? 0
                  const isExpanded = expandedRef === p.reference
                  return (
                    <>
                      <tr
                        key={p.reference}
                        onClick={() => handleExpand(p.reference)}
                        style={{ cursor: 'pointer' }}
                      >
                        <td style={{ textAlign: 'center', fontSize: '0.7rem', color: 'var(--stone-500)' }}>
                          {isExpanded ? '\u25BC' : '\u25B6'}
                        </td>
                        <td><span className="mono">{p.reference}</span></td>
                        <td><span className="truncate" style={{ display: 'block' }}>{p.name}</span></td>
                        <td>{p.brand ?? <span style={{ color: 'var(--cream-400)' }}>--</span>}</td>
                        <td><span className="mono">{p.ean ?? '--'}</span></td>
                        <td>
                          {p.retailer
                            ? <span className="badge badge-info">{p.retailer}</span>
                            : <span style={{ color: 'var(--cream-400)' }}>--</span>
                          }
                        </td>
                        <td>
                          {price != null
                            ? <span style={{ fontWeight: 500 }}>{price.toFixed(2)}</span>
                            : <span style={{ color: 'var(--cream-400)' }}>--</span>
                          }
                        </td>
                        <td>
                          {mc > 0
                            ? <span className="badge badge-success">{mc}</span>
                            : <span style={{ color: 'var(--cream-400)' }}>0</span>
                          }
                        </td>
                      </tr>
                      {isExpanded && (
                        <tr key={`${p.reference}-detail`}>
                          <td colSpan={8} style={{ padding: 0 }}>
                            <div style={{
                              background: 'var(--cream-100)',
                              padding: '16px 24px',
                              borderTop: '1px solid var(--cream-200)',
                              borderBottom: '2px solid var(--accent-muted)',
                            }}>
                              {expandedMatches.length === 0 ? (
                                <p style={{ color: 'var(--stone-500)', fontSize: '0.875rem' }}>
                                  No matches found for this product.
                                </p>
                              ) : (
                                <table className="data-table" style={{ background: 'var(--cream-50)', borderRadius: 'var(--radius-sm)' }}>
                                  <thead>
                                    <tr>
                                      <th>Target Ref</th>
                                      <th>Product Name</th>
                                      <th>Retailer</th>
                                      <th>Price</th>
                                      <th>Method</th>
                                      <th>Confidence</th>
                                    </tr>
                                  </thead>
                                  <tbody>
                                    {expandedMatches.map((m) => (
                                      <tr key={m.target_reference}>
                                        <td><span className="mono">{m.target_reference}</span></td>
                                        <td><span className="truncate" style={{ display: 'block', maxWidth: '240px' }}>{m.target_name}</span></td>
                                        <td><span className="badge badge-info">{m.target_retailer}</span></td>
                                        <td>{m.target_price != null ? m.target_price.toFixed(2) : '--'}</td>
                                        <td><span className="badge badge-accent">{m.method}</span></td>
                                        <td>
                                          <div className="confidence-bar">
                                            <span className="mono" style={{ minWidth: '36px' }}>
                                              {(m.confidence * 100).toFixed(0)}%
                                            </span>
                                            <div className="confidence-track">
                                              <div
                                                className={`confidence-fill ${m.confidence >= 0.85 ? 'high' : m.confidence >= 0.65 ? 'medium' : 'low'}`}
                                                style={{ width: `${m.confidence * 100}%` }}
                                              />
                                            </div>
                                          </div>
                                        </td>
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              )}
                            </div>
                          </td>
                        </tr>
                      )}
                    </>
                  )
                })
              )}
            </tbody>
          </table>
          {brandFiltered.length > 100 && (
            <div className="table-footer">
              Showing 100 of {brandFiltered.length} products. Use search to narrow results.
            </div>
          )}
        </div>
      </div>
    </>
  )
}