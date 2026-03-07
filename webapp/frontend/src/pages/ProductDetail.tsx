import { useEffect, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { getProduct, getSimilar } from '../services/api'
import type { SourceProduct, MatchEntry, SimilarProduct } from '../types/product'

export default function ProductDetail() {
  const { ref } = useParams<{ ref: string }>()
  const navigate = useNavigate()
  const [product, setProduct] = useState<SourceProduct | null>(null)
  const [matches, setMatches] = useState<MatchEntry[]>([])
  const [similar, setSimilar] = useState<SimilarProduct[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!ref) return
    setLoading(true)
    Promise.all([
      getProduct(ref).then((d) => {
        setProduct(d.product)
        setMatches(d.matches)
      }).catch(() => {}),
      getSimilar(ref, 12, 0.5).then((d) => setSimilar(d.similar)).catch(() => {}),
    ]).finally(() => setLoading(false))
  }, [ref])

  if (loading) {
    return (
      <>
        <div className="page-header">
          <h1>Loading...</h1>
        </div>
        <div className="page-body">
          <div className="card" style={{ padding: '40px', textAlign: 'center' }}>
            <span className="spinner" />
          </div>
        </div>
      </>
    )
  }

  if (!product) {
    return (
      <>
        <div className="page-header">
          <h1>Product not found</h1>
        </div>
        <div className="page-body">
          <button className="btn btn-secondary" onClick={() => navigate('/products')}>
            Back to Products
          </button>
        </div>
      </>
    )
  }

  const price = product.price_eur ?? product.price

  return (
    <>
      <div className="page-header">
        <button className="btn btn-secondary" onClick={() => navigate('/products')} style={{ marginBottom: '8px' }}>
          &larr; Back to Products
        </button>
        <h1>{product.name}</h1>
        <p>
          <span className="mono">{product.reference}</span>
          {product.brand && <> &middot; {product.brand}</>}
        </p>
      </div>
      <div className="page-body">
        {/* Product Info */}
        <div className="product-detail-top">
          <div className="product-detail-image">
            {product.image_url ? (
              <img src={product.image_url} alt={product.name} />
            ) : (
              <div className="product-image-placeholder large">
                <svg width="64" height="64" viewBox="0 0 64 64" fill="none" stroke="currentColor" strokeWidth="1.2" opacity="0.25">
                  <rect x="4" y="8" width="56" height="48" rx="6" />
                  <circle cx="22" cy="26" r="6" />
                  <path d="M4 44L20 32L36 42L48 34L60 42" />
                </svg>
              </div>
            )}
          </div>
          <div className="product-detail-info">
            <div className="product-detail-meta">
              {product.brand && (
                <div className="meta-row">
                  <span className="meta-label">Brand</span>
                  <span className="meta-value">{product.brand}</span>
                </div>
              )}
              {product.ean && (
                <div className="meta-row">
                  <span className="meta-label">EAN</span>
                  <span className="meta-value mono">{product.ean}</span>
                </div>
              )}
              {product.retailer && (
                <div className="meta-row">
                  <span className="meta-label">Retailer</span>
                  <span className="meta-value"><span className="badge badge-info">{product.retailer}</span></span>
                </div>
              )}
              {price != null && (
                <div className="meta-row">
                  <span className="meta-label">Price</span>
                  <span className="meta-value" style={{ fontSize: '1.2rem', fontWeight: 600 }}>&euro;{price.toFixed(2)}</span>
                </div>
              )}
              {product.category && (
                <div className="meta-row">
                  <span className="meta-label">Category</span>
                  <span className="meta-value"><span className="badge badge-accent">{product.category}</span></span>
                </div>
              )}
              {product.url && (
                <div className="meta-row">
                  <span className="meta-label">URL</span>
                  <a href={product.url} target="_blank" rel="noreferrer" className="meta-value" style={{ color: 'var(--accent)', wordBreak: 'break-all' }}>
                    View original &rarr;
                  </a>
                </div>
              )}
            </div>
            {product.specifications && Object.keys(product.specifications).length > 0 && (
              <div style={{ marginTop: '16px' }}>
                <h3 style={{ fontSize: '0.88rem', fontWeight: 600, marginBottom: '8px', color: 'var(--stone-700)' }}>Specifications</h3>
                <div className="product-detail-meta">
                  {Object.entries(product.specifications).slice(0, 10).map(([k, v]) => (
                    <div className="meta-row" key={k}>
                      <span className="meta-label">{k}</span>
                      <span className="meta-value">{v}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Matches */}
        <div className="card" style={{ marginTop: '24px' }}>
          <div className="card-header">
            <span className="card-title">Matches ({matches.length})</span>
          </div>
          {matches.length === 0 ? (
            <p style={{ color: 'var(--stone-500)', fontSize: '0.875rem' }}>No matches found for this product.</p>
          ) : (
            <div className="table-wrapper" style={{ border: 'none', boxShadow: 'none' }}>
              <table className="data-table">
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
                  {matches.map((m) => (
                    <tr key={m.target_reference}>
                      <td><Link to={`/products/${m.target_reference}`} className="mono" style={{ color: 'var(--accent)' }}>{m.target_reference}</Link></td>
                      <td><span className="truncate" style={{ display: 'block', maxWidth: '280px' }}>{m.target_name}</span></td>
                      <td><span className="badge badge-info">{m.target_retailer}</span></td>
                      <td>{m.target_price != null ? `\u20AC${m.target_price.toFixed(2)}` : '--'}</td>
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
            </div>
          )}
        </div>

        {/* Similar Products */}
        {similar.length > 0 && (
          <div style={{ marginTop: '24px' }}>
            <h2 style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: '14px', color: 'var(--stone-800)' }}>
              Similar Products
            </h2>
            <div className="product-grid">
              {similar.map((s) => (
                <Link
                  key={s.reference}
                  to={`/products/${s.reference}`}
                  className="product-card"
                  style={{ textDecoration: 'none' }}
                >
                  <div className="product-card-image">
                    <div className="product-image-placeholder">
                      <svg width="32" height="32" viewBox="0 0 64 64" fill="none" stroke="currentColor" strokeWidth="1.2" opacity="0.25">
                        <rect x="4" y="8" width="56" height="48" rx="6" />
                        <circle cx="22" cy="26" r="6" />
                        <path d="M4 44L20 32L36 42L48 34L60 42" />
                      </svg>
                    </div>
                  </div>
                  <div className="product-card-body">
                    <div className="product-card-brand">{s.brand}</div>
                    <div className="product-card-name">{s.name}</div>
                    <div className="product-card-footer">
                      <span className="badge badge-info" style={{ fontSize: '0.7rem' }}>{s.retailer}</span>
                      {s.price != null && <span style={{ fontWeight: 600, fontSize: '0.85rem' }}>&euro;{s.price.toFixed(2)}</span>}
                    </div>
                    <div className="product-card-similarity">
                      <div className="confidence-track" style={{ height: '3px' }}>
                        <div
                          className={`confidence-fill ${s.similarity >= 0.85 ? 'high' : s.similarity >= 0.65 ? 'medium' : 'low'}`}
                          style={{ width: `${s.similarity * 100}%` }}
                        />
                      </div>
                      <span className="mono" style={{ fontSize: '0.72rem' }}>{(s.similarity * 100).toFixed(0)}% similar</span>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        )}
      </div>
    </>
  )
}