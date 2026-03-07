import { useEffect, useState, useCallback, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { searchProducts, getAllSourceProducts, getBrands, getTrends } from '../services/api'
import { Price } from '../CurrencyContext'
import { useI18n } from '../i18n'
import type { SourceProduct, BrandEntry, TrendInsight } from '../types/product'

export default function Products() {
  const { t, lang } = useI18n()
  const [sources, setSources] = useState<SourceProduct[]>([])
  const [search, setSearch] = useState('')
  const [searchResults, setSearchResults] = useState<SourceProduct[] | null>(null)
  const [brands, setBrands] = useState<BrandEntry[]>([])
  const [brandFilter, setBrandFilter] = useState('')
  const [tab, setTab] = useState<'all' | 'unmatched'>('all')
  const [trendInsights, setTrendInsights] = useState<TrendInsight[]>([])

  useEffect(() => {
    getAllSourceProducts().then((d) => setSources(d.sources)).catch(() => {})
    getBrands().then((d) => setBrands(d.brands)).catch(() => {})
    getTrends().then((d) => setTrendInsights(d.insights || [])).catch(() => {})
  }, [])

  // Map brand names (lowercased) to their trend info
  const trendByBrand = useMemo(() => {
    const map: Record<string, TrendInsight> = {}
    for (const t of trendInsights) {
      map[t.brand.toLowerCase()] = t
    }
    return map
  }, [trendInsights])

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

  return (
    <>
      <div className="page-header">
        <h1>{t('products.title')}</h1>
        <p>{t('products.subtitle')}</p>
      </div>
      <div className="page-body">
        <div className="toolbar">
          <div className="tab-group">
            <button className={`tab-btn ${tab === 'all' ? 'active' : ''}`} onClick={() => setTab('all')}>
              {t('filter.all')} ({displayProducts.length})
            </button>
            <button className={`tab-btn ${tab === 'unmatched' ? 'active' : ''}`} onClick={() => setTab('unmatched')}>
              {t('filter.unmatched')} ({displayProducts.filter((p) => (p.match_count ?? 0) === 0).length})
            </button>
          </div>

          <div className="divider" />

          <select
            className="select-field"
            value={brandFilter}
            onChange={(e) => setBrandFilter(e.target.value)}
          >
            <option value="">{t('filter.all_brands')}</option>
            {brands.map((b) => (
              <option key={b.brand} value={b.brand}>{b.brand} ({b.source_count})</option>
            ))}
          </select>

          <input
            type="text"
            className="input-field search-field"
            placeholder={t('filter.search')}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        {brandFiltered.length === 0 ? (
          <div className="card">
            <div className="empty-state">
              <h3>{t('filter.no_products')}</h3>
            </div>
          </div>
        ) : (
          <>
            <div className="product-grid">
              {brandFiltered.slice(0, 60).map((p) => {
                const price = p.price_eur ?? p.price
                const mc = p.match_count ?? 0
                const trend = p.brand ? trendByBrand[p.brand.toLowerCase()] : null
                return (
                  <Link
                    key={p.reference}
                    to={`/products/${p.reference}`}
                    className={`product-card${trend ? ' product-card--trending' : ''}`}
                    style={{ textDecoration: 'none' }}
                  >
                    {trend && (
                      <div className="product-trending-badge">
                        <svg width="12" height="12" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <polyline points="2 14 6 8 10 11 16 3"/>
                          <polyline points="12 3 16 3 16 7"/>
                        </svg>
                        {lang === 'de' ? 'Trend' : 'Trending'}
                        <span className="product-trending-score">{trend.trend_score}</span>
                      </div>
                    )}
                    <div className="product-card-image">
                      {p.image_url ? (
                        <img src={p.image_url} alt={p.name} />
                      ) : (
                        <div className="product-image-placeholder">
                          <svg width="40" height="40" viewBox="0 0 64 64" fill="none" stroke="currentColor" strokeWidth="1.2" opacity="0.25">
                            <rect x="4" y="8" width="56" height="48" rx="6" />
                            <circle cx="22" cy="26" r="6" />
                            <path d="M4 44L20 32L36 42L48 34L60 42" />
                          </svg>
                        </div>
                      )}
                    </div>
                    <div className="product-card-body">
                      <div className="product-card-brand">{p.brand ?? 'Unknown'}</div>
                      <div className="product-card-name">{p.name}</div>
                      {trend && (
                        <div className="product-trend-qualities">
                          {trend.qualities.slice(0, 2).map((q, i) => (
                            <span key={i} className="trend-quality-tag small">{q}</span>
                          ))}
                        </div>
                      )}
                      <div className="product-card-footer">
                        {p.retailer && <span className="badge badge-info" style={{ fontSize: '0.7rem' }}>{p.retailer}</span>}
                        {price != null && <Price value={price} style={{ fontWeight: 600, fontSize: '0.88rem' }} />}
                      </div>
                      <div className="product-card-matches">
                        {mc > 0
                          ? <span className="badge badge-success">{mc} match{mc !== 1 ? 'es' : ''}</span>
                          : <span style={{ color: 'var(--stone-500)', fontSize: '0.75rem' }}>{t('common.no_matches')}</span>
                        }
                        <span className="mono" style={{ fontSize: '0.72rem', color: 'var(--stone-500)' }}>{p.reference}</span>
                      </div>
                    </div>
                  </Link>
                )
              })}
            </div>
            {brandFiltered.length > 60 && (
              <div className="table-footer" style={{ marginTop: '12px', borderRadius: 'var(--radius-sm)' }}>
                Showing 60 of {brandFiltered.length} products. Use search to narrow results.
              </div>
            )}
          </>
        )}
      </div>
    </>
  )
}
