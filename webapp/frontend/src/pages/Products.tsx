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
    <div>
      <h1>Products</h1>

      <div style={{ display: 'flex', gap: '1rem', margin: '1rem 0', alignItems: 'center' }}>
        <select value={selectedCategory} onChange={(e) => setSelectedCategory(e.target.value)}
          style={{ padding: '0.5rem', borderRadius: 4 }}>
          {categories.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>

        <button onClick={() => setTab('source')}
          style={{ padding: '0.5rem 1rem', background: tab === 'source' ? '#1a1a2e' : '#ddd', color: tab === 'source' ? '#fff' : '#333', border: 'none', borderRadius: 4, cursor: 'pointer' }}>
          Source ({sources.length})
        </button>
        <button onClick={() => setTab('target')}
          style={{ padding: '0.5rem 1rem', background: tab === 'target' ? '#1a1a2e' : '#ddd', color: tab === 'target' ? '#fff' : '#333', border: 'none', borderRadius: 4, cursor: 'pointer' }}>
          Target ({targets.length})
        </button>

        <input type="text" placeholder="Search by name, brand, or EAN..."
          value={search} onChange={(e) => setSearch(e.target.value)}
          style={{ padding: '0.5rem', borderRadius: 4, border: '1px solid #ccc', flex: 1 }} />
      </div>

      <table style={{ width: '100%', borderCollapse: 'collapse', background: '#fff' }}>
        <thead>
          <tr style={{ background: '#eee', textAlign: 'left' }}>
            <th style={{ padding: '0.5rem' }}>Reference</th>
            <th style={{ padding: '0.5rem' }}>Name</th>
            <th style={{ padding: '0.5rem' }}>Brand</th>
            <th style={{ padding: '0.5rem' }}>EAN</th>
            {tab === 'target' && <th style={{ padding: '0.5rem' }}>Retailer</th>}
            <th style={{ padding: '0.5rem' }}>Price</th>
          </tr>
        </thead>
        <tbody>
          {filtered.slice(0, 100).map((p) => (
            <tr key={p.reference} style={{ borderBottom: '1px solid #eee' }}>
              <td style={{ padding: '0.5rem', fontFamily: 'monospace', fontSize: '0.85rem' }}>{p.reference}</td>
              <td style={{ padding: '0.5rem' }}>{p.name}</td>
              <td style={{ padding: '0.5rem' }}>{p.brand ?? '-'}</td>
              <td style={{ padding: '0.5rem', fontFamily: 'monospace', fontSize: '0.85rem' }}>{p.ean ?? '-'}</td>
              {tab === 'target' && <td style={{ padding: '0.5rem' }}>{(p as TargetProduct).retailer ?? '-'}</td>}
              <td style={{ padding: '0.5rem' }}>{p.price != null ? `${p.price.toFixed(2)}` : '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {filtered.length > 100 && (
        <p style={{ marginTop: '0.5rem', color: '#888' }}>
          Showing 100 of {filtered.length} products. Use search to narrow down.
        </p>
      )}
    </div>
  )
}
