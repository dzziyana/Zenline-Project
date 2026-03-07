import { useEffect, useState, useMemo } from "react";
import { useI18n } from "../i18n";

interface ScrapeResult {
  id: number;
  source_reference: string;
  retailer: string;
  query: string;
  result_name: string;
  result_url: string;
  result_price: number | null;
  result_ean: string | null;
  matched: number;
  created_at: string;
}

interface SourceInfo {
  reference: string;
  name: string;
  brand?: string;
}

export default function Scraping() {
  const { lang } = useI18n();
  const [results, setResults] = useState<ScrapeResult[]>([]);
  const [sources, setSources] = useState<Record<string, SourceInfo>>({});
  const [loading, setLoading] = useState(true);
  const [scraping, setScraping] = useState<string | null>(null);
  const [retailerFilter, setRetailerFilter] = useState("");
  const [sourceFilter, setSourceFilter] = useState("");

  useEffect(() => {
    Promise.all([
      fetch("/api/scrape-results").then((r) => r.json()),
      fetch("/api/sources").then((r) => r.json()),
    ])
      .then(([scrapeData, sourceData]) => {
        setResults(scrapeData.results || []);
        const map: Record<string, SourceInfo> = {};
        for (const s of sourceData.sources || []) {
          map[s.reference] = s;
        }
        setSources(map);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const retailers = useMemo(() => {
    const set = new Set<string>();
    for (const r of results) set.add(r.retailer);
    return Array.from(set).sort();
  }, [results]);

  const sourceRefs = useMemo(() => {
    const set = new Set<string>();
    for (const r of results) set.add(r.source_reference);
    return Array.from(set).sort();
  }, [results]);

  const filtered = useMemo(() => {
    let items = results;
    if (retailerFilter)
      items = items.filter((r) => r.retailer === retailerFilter);
    if (sourceFilter)
      items = items.filter((r) => r.source_reference === sourceFilter);
    return items;
  }, [results, retailerFilter, sourceFilter]);

  const retailerStats = useMemo(() => {
    const map: Record<string, { total: number; matched: number }> = {};
    for (const r of results) {
      if (!map[r.retailer]) map[r.retailer] = { total: 0, matched: 0 };
      map[r.retailer].total++;
      if (r.matched) map[r.retailer].matched++;
    }
    return map;
  }, [results]);

  const handleScrape = async (ref: string) => {
    setScraping(ref);
    try {
      const res = await fetch(`/api/scrape/${ref}`, { method: "POST" });
      if (res.ok) {
        const fresh = await fetch("/api/scrape-results").then((r) => r.json());
        setResults(fresh.results || []);
      }
    } catch {}
    setScraping(null);
  };

  // Group results by source
  const grouped = useMemo(() => {
    const map: Record<string, ScrapeResult[]> = {};
    for (const r of filtered) {
      if (!map[r.source_reference]) map[r.source_reference] = [];
      map[r.source_reference].push(r);
    }
    return Object.entries(map).sort((a, b) => b[1].length - a[1].length);
  }, [filtered]);

  if (loading) {
    return (
      <>
        <div className="page-header">
          <h1>{lang === "de" ? "Web-Scraping" : "Web Scraping"}</h1>
        </div>
        <div className="page-body">
          <div
            className="card"
            style={{ padding: "40px", textAlign: "center" }}
          >
            <span className="spinner" />
          </div>
        </div>
      </>
    );
  }

  return (
    <>
      <div className="page-header">
        <h1>{lang === "de" ? "Web-Scraping" : "Web Scraping"}</h1>
        <p>
          {lang === "de"
            ? "Konkurrenzprodukte von versteckten Haendlern finden und vergleichen"
            : "Find and compare competitor products from hidden retailers"}
        </p>
      </div>
      <div className="page-body">
        {/* Retailer overview cards */}
        <div className="stats-grid" style={{ marginBottom: "24px" }}>
          <div className="stat-card">
            <div className="stat-label">
              {lang === "de" ? "Gesamt Ergebnisse" : "Total Results"}
            </div>
            <div className="stat-value">{results.length}</div>
            <div className="stat-note">
              {lang === "de" ? "Von" : "From"} {retailers.length}{" "}
              {lang === "de" ? "Haendlern" : "retailers"}
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-label">
              {lang === "de" ? "Quellprodukte" : "Source Products"}
            </div>
            <div className="stat-value">{sourceRefs.length}</div>
            <div className="stat-note">
              {lang === "de"
                ? "mit Scraping-Ergebnissen"
                : "with scrape results"}
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-label">
              {lang === "de" ? "Verifizierte Treffer" : "Verified Matches"}
            </div>
            <div className="stat-value">
              {results.filter((r) => r.matched).length}
            </div>
            <div className="stat-note">
              {lang === "de" ? "Automatisch bestaetigt" : "Auto-confirmed"}
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-label">
              {lang === "de" ? "Durchschn. Preis" : "Avg Price"}
            </div>
            <div className="stat-value">
              {results.filter((r) => r.result_price).length > 0
                ? `${(results.filter((r) => r.result_price).reduce((s, r) => s + (r.result_price || 0), 0) / results.filter((r) => r.result_price).length).toFixed(0)}`
                : "--"}
            </div>
            <div className="stat-note">EUR</div>
          </div>
        </div>

        {/* Retailer breakdown */}
        <div className="card" style={{ marginBottom: "24px" }}>
          <div className="card-header">
            <span className="card-title">
              {lang === "de" ? "Haendler-Uebersicht" : "Retailer Coverage"}
            </span>
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "10px" }}>
            {retailers.map((ret) => {
              const stats = retailerStats[ret];
              const isActive = retailerFilter === ret;
              return (
                <button
                  key={ret}
                  onClick={() => setRetailerFilter(isActive ? "" : ret)}
                  style={{
                    padding: "10px 16px",
                    background: isActive ? "var(--accent)" : "var(--cream-100)",
                    color: isActive ? "white" : "var(--stone-700)",
                    border: `1px solid ${isActive ? "var(--accent)" : "var(--cream-300)"}`,
                    borderRadius: "var(--radius-sm)",
                    cursor: "pointer",
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    gap: "4px",
                    minWidth: "120px",
                    transition: "all 0.15s",
                  }}
                >
                  <strong style={{ fontSize: "0.88rem" }}>{ret}</strong>
                  <span style={{ fontSize: "0.78rem", opacity: 0.7 }}>
                    {stats.total} {lang === "de" ? "Produkte" : "products"}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Filters & on-demand scrape */}
        <div className="toolbar" style={{ marginBottom: "16px" }}>
          <select
            className="select-field"
            value={sourceFilter}
            onChange={(e) => setSourceFilter(e.target.value)}
          >
            <option value="">
              {lang === "de" ? "Alle Quellprodukte" : "All source products"}
            </option>
            {sourceRefs.map((ref) => (
              <option key={ref} value={ref}>
                {sources[ref]?.name ? `${sources[ref].name.slice(0, 50)}` : ref}
              </option>
            ))}
          </select>

          {retailerFilter && (
            <button
              className="btn btn-secondary"
              style={{ padding: "5px 12px", fontSize: "0.78rem" }}
              onClick={() => setRetailerFilter("")}
            >
              {lang === "de" ? "Filter zuruecksetzen" : "Clear filter"}
            </button>
          )}

          <div style={{ flex: 1 }} />

          <span style={{ fontSize: "0.84rem", color: "var(--stone-500)" }}>
            {filtered.length} {lang === "de" ? "Ergebnisse" : "results"}
          </span>
        </div>

        {/* Grouped results */}
        {grouped.length === 0 ? (
          <div className="card">
            <div className="empty-state">
              <div className="empty-icon">
                <svg
                  width="48"
                  height="48"
                  viewBox="0 0 48 48"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  opacity="0.3"
                >
                  <circle cx="24" cy="24" r="18" />
                  <ellipse cx="24" cy="24" rx="8" ry="18" />
                  <line x1="6" y1="18" x2="42" y2="18" />
                  <line x1="6" y1="30" x2="42" y2="30" />
                </svg>
              </div>
              <h3>
                {lang === "de"
                  ? "Keine Scraping-Ergebnisse"
                  : "No scraping results yet"}
              </h3>
              <p>
                {lang === "de"
                  ? "Fuehren Sie die Pipeline mit aktiviertem Scraping aus oder nutzen Sie den On-Demand-Scrape-Button."
                  : "Run the pipeline with scraping enabled or use the on-demand scrape button on a source product."}
              </p>
            </div>
          </div>
        ) : (
          grouped.map(([srcRef, items]) => {
            const src = sources[srcRef];
            return (
              <div
                key={srcRef}
                className="card"
                style={{ marginBottom: "16px" }}
              >
                <div className="card-header">
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "10px",
                    }}
                  >
                    <span
                      className="card-title"
                      style={{ fontSize: "0.95rem" }}
                    >
                      {src?.name || srcRef}
                    </span>
                    {src?.brand && (
                      <span
                        className="badge badge-accent"
                        style={{ fontSize: "0.7rem" }}
                      >
                        {src.brand}
                      </span>
                    )}
                    <span
                      className="mono"
                      style={{ fontSize: "0.72rem", color: "var(--stone-400)" }}
                    >
                      {srcRef}
                    </span>
                  </div>
                  <button
                    className="btn btn-secondary"
                    style={{ padding: "5px 12px", fontSize: "0.78rem" }}
                    onClick={() => handleScrape(srcRef)}
                    disabled={scraping === srcRef}
                  >
                    {scraping === srcRef ? (
                      <>
                        <span
                          className="spinner"
                          style={{ width: "12px", height: "12px" }}
                        />{" "}
                        Scraping...
                      </>
                    ) : lang === "de" ? (
                      "Erneut scrapen"
                    ) : (
                      "Re-scrape"
                    )}
                  </button>
                </div>
                <div
                  className="table-wrapper"
                  style={{ border: "none", boxShadow: "none" }}
                >
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>{lang === "de" ? "Haendler" : "Retailer"}</th>
                        <th>{lang === "de" ? "Produkt" : "Product"}</th>
                        <th>{lang === "de" ? "Preis" : "Price"}</th>
                        <th>EAN</th>
                        <th>{lang === "de" ? "Status" : "Status"}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {items.map((r) => (
                        <tr key={r.id}>
                          <td>
                            <span
                              className="badge badge-info"
                              style={{ fontSize: "0.72rem" }}
                            >
                              {r.retailer}
                            </span>
                          </td>
                          <td>
                            <div style={{ maxWidth: "380px" }}>
                              {r.result_url ? (
                                <a
                                  href={r.result_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  style={{
                                    color: "var(--accent)",
                                    fontSize: "0.85rem",
                                    textDecoration: "none",
                                  }}
                                >
                                  {r.result_name}
                                </a>
                              ) : (
                                <span style={{ fontSize: "0.85rem" }}>
                                  {r.result_name}
                                </span>
                              )}
                            </div>
                          </td>
                          <td>
                            {r.result_price != null ? (
                              <span
                                style={{ fontWeight: 600, fontSize: "0.88rem" }}
                              >
                                &euro;{r.result_price.toFixed(2)}
                              </span>
                            ) : (
                              <span style={{ color: "var(--cream-400)" }}>
                                --
                              </span>
                            )}
                          </td>
                          <td>
                            {r.result_ean ? (
                              <span
                                className="mono"
                                style={{ fontSize: "0.78rem" }}
                              >
                                {r.result_ean}
                              </span>
                            ) : (
                              <span style={{ color: "var(--cream-400)" }}>
                                --
                              </span>
                            )}
                          </td>
                          <td>
                            <span
                              className={`badge ${r.matched ? "badge-success" : "badge-warning"}`}
                            >
                              {r.matched
                                ? lang === "de"
                                  ? "Verifiziert"
                                  : "Verified"
                                : lang === "de"
                                  ? "Gefunden"
                                  : "Found"}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            );
          })
        )}
      </div>
    </>
  );
}
