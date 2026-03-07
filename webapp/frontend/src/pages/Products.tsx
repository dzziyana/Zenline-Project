import { useEffect, useState } from 'react'
import { getCategories, getSourceProducts, getTargetProducts } from '../services/api'
import type { SourceProduct, TargetProduct } from '../types/product'

export default function Products() {
  const [categories, setCategories] = useState<string[]>([])
  const [selectedCategory, setSelectedCategory] = useState('')
  const [sources, setSources] = useState<SourceProduct[]>([])
  const [targets, setTargets] = useState<TargetProduct[]>([])
  const [search, setSearch] = useState('')
  const [tab, setTab] = useState<'source' | 'target'>('source')

  useEffect(() => {
    getCategories().then((cats) => {
      setCategories(cats)
      if (cats.length > 0) setSelectedCategory(cats[0])
    }).catch(() => {})
  }, [])

  useEffect(() => {
    if (!selectedCategory) return
    getSourceProducts(selectedCategory).then(setSources).catch(() => setSources([]))
    getTargetProducts(selectedCategory).then(setTargets).catch(() => setTargets([]))
  }, [selectedCategory])

  const filtered = (tab === 'source' ? sources : targets).filter((p) =>
    p.name.toLowerCase().includes(search.toLowerCase()) ||
    (p.brand?.toLowerCase().includes(search.toLowerCase()) ?? false) ||
    (p.ean?.includes(search) ?? false)
  )

  return (
    <>
      <div className="page-header">
        <h1>Products</h1>
        <p>Browse and search source and target product catalogs</p>
      </div>
      <div className="page-body">
        <div className="toolbar">
          <select
            className="select-field"
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
          >
            {categories.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>

          <div className="divider" />

          <div className="tab-group">
            <button
              className={`tab-btn ${tab === 'source' ? 'active' : ''}`}
              onClick={() => setTab('source')}
            >
              Source ({sources.length})
            </button>
            <button
              className={`tab-btn ${tab === 'target' ? 'active' : ''}`}
              onClick={() => setTab('target')}
            >
              Target ({targets.length})
            </button>
          </div>

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
                <th>Reference</th>
                <th>Name</th>
                <th>Brand</th>
                <th>EAN</th>
                {tab === 'target' && <th>Retailer</th>}
                <th>Price</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={tab === 'target' ? 6 : 5}>
                    <div className="empty-state">
                      <h3>No products found</h3>
                      <p>Try adjusting your search or select a different category.</p>
                    </div>
                  </td>
                </tr>
              ) : (
                filtered.slice(0, 100).map((p) => (
                  <tr key={p.reference}>
                    <td><span className="mono">{p.reference}</span></td>
                    <td><span className="truncate" style={{ display: 'block' }}>{p.name}</span></td>
                    <td>{p.brand ?? <span style={{ color: 'var(--cream-400)' }}>--</span>}</td>
                    <td><span className="mono">{p.ean ?? '--'}</span></td>
                    {tab === 'target' && (
                      <td><span className="badge badge-info">{(p as TargetProduct).retailer ?? '--'}</span></td>
                    )}
                    <td>
                      {p.price != null
                        ? <span style={{ fontWeight: 500 }}>{p.price.toFixed(2)}</span>
                        : <span style={{ color: 'var(--cream-400)' }}>--</span>
                      }
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
          {filtered.length > 100 && (
            <div className="table-footer">
              Showing 100 of {filtered.length} products. Use search to narrow results.
            </div>
          )}
        </div>
      </div>
    </>
  )
}
