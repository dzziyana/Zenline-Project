import { useEffect, useState } from 'react'
import { getCategories } from '../services/api'

export default function Dashboard() {
  const [categories, setCategories] = useState<string[]>([])

  useEffect(() => {
    getCategories().then(setCategories).catch(() => setCategories([]))
  }, [])

  return (
    <div>
      <h1>Dashboard</h1>
      <section style={{ marginTop: '1.5rem' }}>
        <h2>Available Categories</h2>
        {categories.length === 0 ? (
          <p style={{ color: '#888', marginTop: '0.5rem' }}>
            No categories loaded yet. Upload source/target data via the matcher API or place JSON files in matcher/data/.
          </p>
        ) : (
          <ul style={{ marginTop: '0.5rem' }}>
            {categories.map((c) => (
              <li key={c} style={{ padding: '0.25rem 0' }}>{c}</li>
            ))}
          </ul>
        )}
      </section>

      <section style={{ marginTop: '2rem' }}>
        <h2>Quick Start</h2>
        <ol style={{ marginTop: '0.5rem', paddingLeft: '1.5rem', lineHeight: 1.8 }}>
          <li>Download source products and target pool JSON from the hackathon web app</li>
          <li>Place them in <code>matcher/data/</code> or upload via the API</li>
          <li>Go to <strong>Products</strong> to browse the data</li>
          <li>Go to <strong>Matching</strong> to run the pipeline and generate submissions</li>
        </ol>
      </section>
    </div>
  )
}
