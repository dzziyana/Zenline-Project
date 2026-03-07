import { useEffect, useState } from 'react'
import { getTrends } from '../services/api'
import { useI18n } from '../i18n'
import type { TrendInsight, TrendArticle } from '../types/product'

const SENTIMENT_COLORS: Record<string, string> = {
  positive: 'var(--success)',
  neutral: 'var(--accent)',
  negative: 'var(--warning)',
}

const CATEGORY_COLORS: Record<string, string> = {
  news: 'var(--info)',
  social: 'var(--accent)',
  review: 'var(--success)',
}

export default function Trends() {
  const { lang } = useI18n()
  const [insights, setInsights] = useState<TrendInsight[]>([])
  const [articles, setArticles] = useState<TrendArticle[]>([])
  const [sourcesList, setSourcesList] = useState<string[]>([])
  const [totalArticles, setTotalArticles] = useState(0)
  const [loading, setLoading] = useState(false)
  const [loaded, setLoaded] = useState(false)
  const [categoryFilter, setCategoryFilter] = useState('')

  const loadTrends = (refresh = false) => {
    setLoading(true)
    getTrends(refresh)
      .then((d) => {
        setInsights(d.insights || [])
        setArticles(d.articles || [])
        setSourcesList(d.sources_scraped || [])
        setTotalArticles(d.total_articles || 0)
        setLoaded(true)
      })
      .catch(() => setLoaded(true))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    loadTrends()
  }, [])

  const categories = [...new Set(insights.map((i) => i.category).filter(Boolean))]
  const filteredInsights = categoryFilter
    ? insights.filter((i) => i.category === categoryFilter)
    : insights
  const topInsight = filteredInsights.length > 0 ? filteredInsights[0] : null

  return (
    <>
      <div className="page-header">
        <h1>{lang === 'de' ? 'Markttrends' : 'Market Trends'}</h1>
        <p>{lang === 'de'
          ? 'Trendende Produkte aus Tech-Journalen, Bewertungsseiten und Social Media'
          : 'Trending products from tech journals, review sites, and social media'
        }</p>
      </div>
      <div className="page-body">
        {/* Sources & Refresh */}
        <div className="toolbar" style={{ marginBottom: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
            {sourcesList.map((s) => (
              <span key={s} className="badge badge-info" style={{ fontSize: '0.72rem' }}>{s}</span>
            ))}
            {totalArticles > 0 && (
              <span style={{ fontSize: '0.8rem', color: 'var(--stone-500)' }}>
                {totalArticles} {lang === 'de' ? 'Artikel analysiert' : 'articles analyzed'}
              </span>
            )}
          </div>
          {categories.length > 1 && (
            <select
              className="select-field"
              style={{ marginLeft: 'auto', fontSize: '0.8rem' }}
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
            >
              <option value="">{lang === 'de' ? 'Alle Kategorien' : 'All categories'}</option>
              {categories.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          )}
          <button
            className="btn btn-secondary"
            style={{ marginLeft: categories.length > 1 ? undefined : 'auto', padding: '6px 14px', fontSize: '0.8rem' }}
            onClick={() => loadTrends(true)}
            disabled={loading}
          >
            {loading ? (
              <span className="spinner" style={{ width: '14px', height: '14px' }} />
            ) : (
              lang === 'de' ? 'Aktualisieren' : 'Refresh'
            )}
          </button>
        </div>

        {!loaded ? (
          <div className="card" style={{ padding: '60px', textAlign: 'center' }}>
            <span className="spinner" />
            <p style={{ marginTop: '16px', color: 'var(--stone-500)' }}>
              {lang === 'de' ? 'Scrape Trends von mehreren Quellen...' : 'Scraping trends from multiple sources...'}
            </p>
          </div>
        ) : insights.length === 0 ? (
          <div className="card">
            <div className="empty-state">
              <h3>{lang === 'de' ? 'Keine Trends gefunden' : 'No trends found'}</h3>
              <p>{lang === 'de'
                ? 'Klicken Sie auf Aktualisieren um erneut zu scrapen.'
                : 'Click Refresh to scrape again. Make sure the backend has internet access.'
              }</p>
            </div>
          </div>
        ) : (
          <>
            {/* Hero: Top Trending */}
            {topInsight && (
              <div className="trend-hero">
                <div className="trend-hero-badge">
                  <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M10 2L12.5 7.5L18 8.5L14 12.5L15 18L10 15.5L5 18L6 12.5L2 8.5L7.5 7.5L10 2Z" />
                  </svg>
                  {lang === 'de' ? 'Top-Trend' : 'Top Trending'}
                </div>
                <h2 className="trend-hero-title">{topInsight.product_name}</h2>
                <p className="trend-hero-summary">{topInsight.summary}</p>
                <div className="trend-hero-qualities">
                  {topInsight.qualities.map((q, i) => (
                    <span key={i} className="trend-quality-tag">{q}</span>
                  ))}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginTop: '12px' }}>
                  <span className="badge badge-accent">{topInsight.brand}</span>
                  <span className="badge" style={{ background: SENTIMENT_COLORS[topInsight.sentiment] + '18', color: SENTIMENT_COLORS[topInsight.sentiment], border: `1px solid ${SENTIMENT_COLORS[topInsight.sentiment]}30` }}>
                    {topInsight.sentiment}
                  </span>
                  <span style={{ fontSize: '0.78rem', color: 'var(--stone-500)' }}>
                    Score: {topInsight.trend_score}/10
                  </span>
                </div>
              </div>
            )}

            {/* Trend Insights Grid */}
            <h2 style={{ fontSize: '1.05rem', fontWeight: 600, color: 'var(--stone-800)', margin: '24px 0 14px' }}>
              {lang === 'de' ? 'Trendende Produkte' : 'Trending Products'}
            </h2>
            <div className="trend-grid">
              {filteredInsights.map((t, i) => (
                <div key={i} className="trend-card">
                  <div className="trend-card-header">
                    <div className="trend-score-ring" data-score={t.trend_score}>
                      <span>{t.trend_score}</span>
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div className="trend-card-name">{t.product_name}</div>
                      <div style={{ display: 'flex', gap: '6px', alignItems: 'center', marginTop: '4px' }}>
                        <span className="badge badge-accent" style={{ fontSize: '0.68rem' }}>{t.brand}</span>
                        <span style={{ fontSize: '0.72rem', color: 'var(--stone-500)' }}>{t.category}</span>
                      </div>
                    </div>
                  </div>
                  <p className="trend-card-summary">{t.summary}</p>
                  <div className="trend-card-qualities">
                    {t.qualities.slice(0, 4).map((q, j) => (
                      <span key={j} className="trend-quality-tag small">{q}</span>
                    ))}
                  </div>
                  <div className="trend-card-footer">
                    <span
                      className="trend-sentiment-dot"
                      style={{ background: SENTIMENT_COLORS[t.sentiment] }}
                    />
                    <span style={{ fontSize: '0.72rem', color: 'var(--stone-500)', textTransform: 'capitalize' }}>
                      {t.sentiment}
                    </span>
                    {t.sources.length > 0 && (
                      <span style={{ fontSize: '0.68rem', color: 'var(--cream-400)', marginLeft: 'auto' }}>
                        {t.sources.slice(0, 2).join(', ')}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>

            {/* Source Articles */}
            {articles.length > 0 && (
              <>
                <h2 style={{ fontSize: '1.05rem', fontWeight: 600, color: 'var(--stone-800)', margin: '28px 0 14px' }}>
                  {lang === 'de' ? 'Quellartikel' : 'Source Articles'}
                </h2>
                <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
                  {articles.slice(0, 15).map((a, i) => (
                    <div key={i} className="trend-article-row">
                      <span
                        className="badge"
                        style={{
                          fontSize: '0.65rem',
                          background: (CATEGORY_COLORS[a.category] || 'var(--stone-500)') + '15',
                          color: CATEGORY_COLORS[a.category] || 'var(--stone-500)',
                          border: `1px solid ${CATEGORY_COLORS[a.category] || 'var(--stone-500)'}25`,
                          flexShrink: 0,
                        }}
                      >
                        {a.source}
                      </span>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        {a.url ? (
                          <a
                            href={a.url}
                            target="_blank"
                            rel="noreferrer"
                            className="trend-article-title"
                          >
                            {a.title}
                          </a>
                        ) : (
                          <span className="trend-article-title">{a.title}</span>
                        )}
                        {a.snippet && (
                          <p className="trend-article-snippet">{a.snippet}</p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </>
            )}
          </>
        )}
      </div>
    </>
  )
}
