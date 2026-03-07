import { useEffect, useState } from "react";
import { getCategories, getAllMatches, runMatching } from "../services/api";
import type { MatchResult } from "../types/product";

function confidenceLevel(val: number) {
  if (val >= 0.85) return "high";
  if (val >= 0.65) return "medium";
  return "low";
}

function methodBadge(method: string) {
  const map: Record<string, string> = {
    ean: "badge-success",
    model_number: "badge-success",
    model_series: "badge-info",
    fuzzy_model: "badge-warning",
    fuzzy_name: "badge-warning",
    fuzzy: "badge-warning",
    scrape: "badge-accent",
    embedding: "badge-info",
    vision: "badge-info",
    llm: "badge-accent",
  };
  const cls =
    Object.entries(map).find(([k]) => method.toLowerCase().includes(k))?.[1] ??
    "badge-info";
  return cls;
}

interface ExistingMatch {
  source: any;
  matches: any[];
}

export default function Matching() {
  const [categories, setCategories] = useState<string[]>([]);
  const [selectedCategory, setSelectedCategory] = useState("");
  const [useLlm, setUseLlm] = useState(false);
  const [threshold, setThreshold] = useState(75);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<MatchResult | null>(null);
  const [existing, setExisting] = useState<ExistingMatch[] | null>(null);
  const [existingStats, setExistingStats] = useState<{
    total_sources: number;
    total_matched: number;
    total_matches: number;
  } | null>(null);
  const [expandedSource, setExpandedSource] = useState<string | null>(null);

  useEffect(() => {
    getCategories()
      .then((cats) => {
        setCategories(cats);
        if (cats.length > 0) setSelectedCategory(cats[0]);
      })
      .catch(() => {});

    getAllMatches()
      .then((data) => {
        setExisting(data.results);
        setExistingStats({
          total_sources: data.total_sources,
          total_matched: data.total_matched,
          total_matches: data.total_matches,
        });
      })
      .catch(() => {});
  }, []);

  const handleRun = async () => {
    if (!selectedCategory) return;
    setLoading(true);
    setResult(null);
    try {
      const res = await runMatching(selectedCategory, useLlm, threshold);
      setResult(res);
      // Refresh existing matches after run
      const data = await getAllMatches();
      setExisting(data.results);
      setExistingStats({
        total_sources: data.total_sources,
        total_matched: data.total_matched,
        total_matches: data.total_matches,
      });
    } catch {
      alert("Matching failed. Is the matcher service running?");
    } finally {
      setLoading(false);
    }
  };

  // Use pipeline result if available, otherwise show existing DB matches
  const displayData = result
    ? result.submissions.map((s) => ({
        source: { reference: s.source_reference, name: s.source_reference },
        matches: s.competitors.map((c) => ({
          target_reference: c.reference,
          target_name: c.competitor_product_name || "",
          target_retailer: c.competitor_retailer || "",
          target_url: c.competitor_url || "",
          target_price: c.competitor_price,
          confidence: c.confidence,
          method: c.match_method,
        })),
      }))
    : existing;

  const totalSources = result
    ? result.total_sources
    : (existingStats?.total_sources ?? 0);
  const totalMatched = result
    ? result.submissions.filter((s) => s.competitors.length > 0).length
    : (existingStats?.total_matched ?? 0);
  const totalMatches = result
    ? result.total_matches
    : (existingStats?.total_matches ?? 0);

  return (
    <>
      <div className="page-header">
        <h1>Matching Pipeline</h1>
        <p>Configure and run the multi-strategy product matching engine</p>
      </div>
      <div className="page-body">
        <div className="card" style={{ marginBottom: "24px" }}>
          <div className="toolbar" style={{ marginBottom: 0 }}>
            <select
              className="select-field"
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
            >
              {categories.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
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
              {loading ? "Running..." : "Run Matching"}
            </button>
          </div>
        </div>

        {totalSources > 0 && (
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-label">Source Products</div>
              <div className="stat-value">{totalSources}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Total Matches</div>
              <div className="stat-value">{totalMatches}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Products Matched</div>
              <div className="stat-value">{totalMatched}</div>
              <div className="stat-note">
                {totalSources > 0
                  ? `${((totalMatched / totalSources) * 100).toFixed(0)}% coverage`
                  : ""}
              </div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Avg Matches/Source</div>
              <div className="stat-value">
                {totalMatched > 0
                  ? (totalMatches / totalMatched).toFixed(1)
                  : "0"}
              </div>
            </div>
          </div>
        )}

        {displayData && displayData.length > 0 && (
          <div className="table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th style={{ width: "30px" }}></th>
                  <th>Source</th>
                  <th>Matches</th>
                  <th>Best Method</th>
                  <th>Confidence</th>
                </tr>
              </thead>
              <tbody>
                {displayData.map((item) => {
                  const ref = item.source?.reference || "";
                  const matches = item.matches || [];
                  const best = [...matches].sort(
                    (a: any, b: any) => b.confidence - a.confidence,
                  )[0];
                  const conf = best?.confidence ?? 0;
                  const level = confidenceLevel(conf);
                  const isExpanded = expandedSource === ref;

                  return (
                    <>
                      <tr
                        key={ref}
                        onClick={() =>
                          setExpandedSource(isExpanded ? null : ref)
                        }
                        style={{ cursor: "pointer" }}
                      >
                        <td
                          style={{
                            textAlign: "center",
                            color: "var(--stone-400)",
                          }}
                        >
                          {matches.length > 0
                            ? isExpanded
                              ? "\u25BC"
                              : "\u25B6"
                            : ""}
                        </td>
                        <td>
                          <span
                            className="mono"
                            style={{
                              fontSize: "0.8rem",
                              color: "var(--stone-400)",
                            }}
                          >
                            {ref}
                          </span>
                          {item.source?.name && ref !== item.source.name && (
                            <div
                              style={{ fontSize: "0.85rem", marginTop: "2px" }}
                            >
                              {item.source.name}
                            </div>
                          )}
                        </td>
                        <td>
                          {matches.length > 0 ? (
                            <span className="badge badge-success">
                              {matches.length}
                            </span>
                          ) : (
                            <span style={{ color: "var(--cream-400)" }}>0</span>
                          )}
                        </td>
                        <td>
                          {best ? (
                            <span
                              className={`badge ${methodBadge(best.method || best.match_method || "")}`}
                            >
                              {best.method || best.match_method}
                            </span>
                          ) : (
                            <span style={{ color: "var(--cream-400)" }}>
                              --
                            </span>
                          )}
                        </td>
                        <td>
                          {best ? (
                            <div className="confidence-bar">
                              <span
                                className="mono"
                                style={{ minWidth: "36px" }}
                              >
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
                            <span style={{ color: "var(--cream-400)" }}>
                              --
                            </span>
                          )}
                        </td>
                      </tr>
                      {isExpanded &&
                        matches.map((m: any, i: number) => (
                          <tr
                            key={`${ref}-match-${i}`}
                            style={{ background: "var(--cream-100)" }}
                          >
                            <td></td>
                            <td colSpan={2} style={{ fontSize: "0.85rem" }}>
                              <div>
                                {m.target_name ||
                                  m.competitor_product_name ||
                                  m.target_reference}
                              </div>
                              <div
                                style={{
                                  fontSize: "0.8rem",
                                  color: "var(--stone-400)",
                                  marginTop: "2px",
                                }}
                              >
                                {m.target_retailer ||
                                  m.competitor_retailer ||
                                  ""}{" "}
                                | {m.target_reference || m.reference}
                                {(m.target_url || m.competitor_url) && (
                                  <>
                                    {" "}
                                    |{" "}
                                    <a
                                      href={m.target_url || m.competitor_url}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      style={{ color: "var(--accent)" }}
                                    >
                                      View
                                    </a>
                                  </>
                                )}
                              </div>
                            </td>
                            <td>
                              <span
                                className={`badge ${methodBadge(m.method || m.match_method || "")}`}
                              >
                                {m.method || m.match_method}
                              </span>
                            </td>
                            <td>
                              <div className="confidence-bar">
                                <span
                                  className="mono"
                                  style={{ minWidth: "36px" }}
                                >
                                  {((m.confidence ?? 0) * 100).toFixed(0)}%
                                </span>
                                <div className="confidence-track">
                                  <div
                                    className={`confidence-fill ${confidenceLevel(m.confidence ?? 0)}`}
                                    style={{
                                      width: `${(m.confidence ?? 0) * 100}%`,
                                    }}
                                  />
                                </div>
                              </div>
                              {(m.target_price || m.competitor_price) !=
                                null && (
                                <span
                                  style={{
                                    fontSize: "0.8rem",
                                    color: "var(--stone-400)",
                                    marginLeft: "8px",
                                  }}
                                >
                                  EUR{" "}
                                  {(
                                    m.target_price || m.competitor_price
                                  )?.toFixed(2)}
                                </span>
                              )}
                            </td>
                          </tr>
                        ))}
                    </>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {(!displayData || displayData.length === 0) && !loading && (
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
                  <circle cx="18" cy="18" r="10" />
                  <circle cx="30" cy="30" r="10" />
                  <line x1="25" y1="25" x2="22" y2="22" />
                </svg>
              </div>
              <h3>Ready to match</h3>
              <p>
                Select a category, configure your parameters, and hit Run
                Matching to start the pipeline.
              </p>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
