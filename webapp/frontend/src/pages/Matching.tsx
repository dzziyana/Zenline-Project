import { useEffect, useState } from "react";
 import { Price } from "../CurrencyContext";
import {
  getCategories,
  getAllMatches,
  runMatching,
  explainMatch,
  getSubmission,
  uploadAndRun,
} from "../services/api";
import type {
  MatchResult,
  ExplainResponse,
} from "../types/product";
import { useI18n } from "../i18n";

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
  return (
    Object.entries(map).find(([k]) => method.toLowerCase().includes(k))?.[1] ??
    "badge-info"
  );
}

interface ExistingMatch {
  source: any;
  matches: any[];
}

export default function Matching() {
  const { t } = useI18n();
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
  const [tab, setTab] = useState<"run" | "upload" | "export">("run");
  const [explain, setExplain] = useState<ExplainResponse | null>(null);
  const [explainLoading, setExplainLoading] = useState(false);
  const [srcFile, setSrcFile] = useState<File | null>(null);
  const [tgtFile, setTgtFile] = useState<File | null>(null);
  const [uploadCat, setUploadCat] = useState("uploaded");
  const [uploadMsg, setUploadMsg] = useState<string | null>(null);
  const [exportJson, setExportJson] = useState<string | null>(null);

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

  const refreshMatches = async () => {
    const data = await getAllMatches();
    setExisting(data.results);
    setExistingStats({
      total_sources: data.total_sources,
      total_matched: data.total_matched,
      total_matches: data.total_matches,
    });
  };

  const handleRun = async () => {
    if (!selectedCategory) return;
    setLoading(true);
    setResult(null);
    try {
      const res = await runMatching(selectedCategory, useLlm, threshold);
      setResult(res);
      await refreshMatches();
    } catch {
      alert(t('matching.failed'));
    } finally {
      setLoading(false);
    }
  };

  const handleUpload = async () => {
    if (!srcFile || !tgtFile) return;
    setLoading(true);
    setUploadMsg(null);
    try {
      const res = await uploadAndRun(srcFile, tgtFile, uploadCat);
      setUploadMsg(
        t('matching.upload_result')
          .replace('{matches}', String(res.matches))
          .replace('{sources}', String(res.sources))
          .replace('{covered}', String(res.sources_matched)),
      );
      await refreshMatches();
      setTab("run");
    } catch {
      setUploadMsg(t('matching.upload_failed'));
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async () => {
    try {
      const data = await getSubmission();
      setExportJson(JSON.stringify(data, null, 2));
    } catch {
      setExportJson(t('matching.export_failed'));
    }
  };

  const handleDownload = () => {
    if (!exportJson) return;
    const blob = new Blob([exportJson], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "submission.json";
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleExplain = async (sourceRef: string, targetRef: string) => {
    setExplainLoading(true);
    try {
      setExplain(await explainMatch(sourceRef, targetRef));
    } catch {
      setExplain(null);
    } finally {
      setExplainLoading(false);
    }
  };

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
        <h1>{t('matching.title')}</h1>
        <p>{t('matching.subtitle')}</p>
      </div>
      <div className="page-body">
        {/* Tab bar */}
        <div className="toolbar">
          <div className="tab-group">
            <button
              className={`tab-btn ${tab === "run" ? "active" : ""}`}
              onClick={() => setTab("run")}
            >
              {t('matching.tab_run')}
            </button>
            <button
              className={`tab-btn ${tab === "upload" ? "active" : ""}`}
              onClick={() => setTab("upload")}
            >
              {t('matching.tab_upload')}
            </button>
            <button
              className={`tab-btn ${tab === "export" ? "active" : ""}`}
              onClick={() => {
                setTab("export");
                handleExport();
              }}
            >
              {t('matching.tab_export')}
            </button>
          </div>
        </div>

        {/* Run Tab */}
        {tab === "run" && (
          <>
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
                  <label>{t('matching.fuzzy_threshold')}</label>
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
                  {t('matching.llm_fallback')}
                </label>

                <div style={{ flex: 1 }} />

                <button
                  className="btn btn-primary"
                  onClick={handleRun}
                  disabled={loading}
                >
                  {loading && <span className="spinner" />}
                  {loading ? t('matching.running') : t('matching.run_btn')}
                </button>
              </div>
            </div>

            {totalSources > 0 && (
              <div className="stats-grid">
                <div className="stat-card">
                  <div className="stat-label">{t('matching.source_products')}</div>
                  <div className="stat-value">{totalSources}</div>
                </div>
                <div className="stat-card">
                  <div className="stat-label">{t('matching.total_matches')}</div>
                  <div className="stat-value">{totalMatches}</div>
                </div>
                <div className="stat-card">
                  <div className="stat-label">{t('matching.products_matched')}</div>
                  <div className="stat-value">{totalMatched}</div>
                  <div className="stat-note">
                    {totalSources > 0
                      ? `${((totalMatched / totalSources) * 100).toFixed(0)}% ${t('matching.coverage')}`
                      : ""}
                  </div>
                </div>
                <div className="stat-card">
                  <div className="stat-label">{t('matching.avg_matches')}</div>
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
                      <th>{t('matching.th_source')}</th>
                      <th>{t('matching.th_matches')}</th>
                      <th>{t('matching.th_best_method')}</th>
                      <th>{t('matching.th_confidence')}</th>
                      <th style={{ width: "70px" }}></th>
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
                              {item.source?.name &&
                                ref !== item.source.name && (
                                  <div
                                    style={{
                                      fontSize: "0.85rem",
                                      marginTop: "2px",
                                    }}
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
                                <span style={{ color: "var(--cream-400)" }}>
                                  0
                                </span>
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
                            <td>
                              {best && (
                                <button
                                  className="btn btn-secondary"
                                  style={{
                                    padding: "3px 8px",
                                    fontSize: "0.72rem",
                                  }}
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleExplain(
                                      ref,
                                      best.target_reference || best.reference,
                                    );
                                  }}
                                >
                                  {t('matching.explain')}
                                </button>
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
                                <td
                                  colSpan={2}
                                  style={{ fontSize: "0.85rem" }}
                                >
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
                                        {" | "}
                                        <a
                                          href={
                                            m.target_url || m.competitor_url
                                          }
                                          target="_blank"
                                          rel="noopener noreferrer"
                                          style={{ color: "var(--accent)" }}
                                        >
                                          {t('matching.view')}
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
                                  {(m.target_price ?? m.competitor_price) !=
                                    null && (
                                    <Price
                                      value={m.target_price ?? m.competitor_price}
                                      style={{
                                        fontSize: "0.8rem",
                                        color: "var(--stone-400)",
                                        marginLeft: "8px",
                                      }}
                                    />
                                  )}
                                </td>
                                <td>
                                  <button
                                    className="btn btn-secondary"
                                    style={{
                                      padding: "3px 8px",
                                      fontSize: "0.72rem",
                                    }}
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      handleExplain(
                                        ref,
                                        m.target_reference || m.reference,
                                      );
                                    }}
                                  >
                                    {t('matching.explain')}
                                  </button>
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
                  <h3>{t('matching.ready_title')}</h3>
                  <p>
                    {t('matching.ready_desc')}
                  </p>
                </div>
              </div>
            )}
          </>
        )}

        {/* Upload Tab */}
        {tab === "upload" && (
          <div className="card">
            <div className="card-header">
              <span className="card-title">{t('matching.upload_title')}</span>
            </div>
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                gap: "16px",
                maxWidth: "480px",
              }}
            >
              <div>
                <label
                  style={{
                    display: "block",
                    fontSize: "0.84rem",
                    fontWeight: 500,
                    color: "var(--stone-600)",
                    marginBottom: "6px",
                  }}
                >
                  {t('matching.source_json')}
                </label>
                <input
                  type="file"
                  accept=".json"
                  onChange={(e) => setSrcFile(e.target.files?.[0] ?? null)}
                />
              </div>
              <div>
                <label
                  style={{
                    display: "block",
                    fontSize: "0.84rem",
                    fontWeight: 500,
                    color: "var(--stone-600)",
                    marginBottom: "6px",
                  }}
                >
                  {t('matching.target_json')}
                </label>
                <input
                  type="file"
                  accept=".json"
                  onChange={(e) => setTgtFile(e.target.files?.[0] ?? null)}
                />
              </div>
              <div>
                <label
                  style={{
                    display: "block",
                    fontSize: "0.84rem",
                    fontWeight: 500,
                    color: "var(--stone-600)",
                    marginBottom: "6px",
                  }}
                >
                  {t('matching.category_name')}
                </label>
                <input
                  className="input-field"
                  value={uploadCat}
                  onChange={(e) => setUploadCat(e.target.value)}
                  placeholder="e.g. TV & Audio"
                />
              </div>
              <button
                className="btn btn-primary"
                onClick={handleUpload}
                disabled={loading || !srcFile || !tgtFile}
                style={{ alignSelf: "flex-start" }}
              >
                {loading && <span className="spinner" />}
                {loading ? t('matching.uploading') : t('matching.upload_btn')}
              </button>
              {uploadMsg && (
                <p style={{ fontSize: "0.875rem", color: "var(--stone-600)" }}>
                  {uploadMsg}
                </p>
              )}
            </div>
          </div>
        )}

        {/* Export Tab */}
        {tab === "export" && (
          <div className="card">
            <div className="card-header">
              <span className="card-title">{t('matching.submission_json')}</span>
              {exportJson && (
                <button
                  className="btn btn-primary"
                  style={{ padding: "6px 14px", fontSize: "0.8rem" }}
                  onClick={handleDownload}
                >
                  {t('matching.download_json')}
                </button>
              )}
            </div>
            {exportJson ? (
              <pre
                style={{
                  background: "var(--cream-100)",
                  border: "1px solid var(--cream-300)",
                  borderRadius: "var(--radius-sm)",
                  padding: "16px",
                  fontSize: "0.78rem",
                  fontFamily: "monospace",
                  maxHeight: "500px",
                  overflow: "auto",
                  color: "var(--stone-700)",
                  whiteSpace: "pre-wrap",
                  wordBreak: "break-all",
                }}
              >
                {exportJson}
              </pre>
            ) : (
              <p style={{ color: "var(--stone-500)", fontSize: "0.875rem" }}>
                {t('matching.loading_submission')}
              </p>
            )}
          </div>
        )}

        {/* Explain Modal */}
        {explain && (
          <div
            style={{
              position: "fixed",
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              background: "rgba(26,21,16,0.4)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              zIndex: 100,
            }}
            onClick={() => setExplain(null)}
          >
            <div
              className="card"
              style={{
                maxWidth: "640px",
                width: "90%",
                maxHeight: "80vh",
                overflow: "auto",
              }}
              onClick={(e) => e.stopPropagation()}
            >
              <div className="card-header">
                <span className="card-title">{t('matching.explanation')}</span>
                <button
                  className="btn btn-secondary"
                  style={{ padding: "4px 12px", fontSize: "0.78rem" }}
                  onClick={() => setExplain(null)}
                >
                  {t('matching.close')}
                </button>
              </div>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: "16px",
                  marginBottom: "16px",
                }}
              >
                <div
                  style={{
                    padding: "12px",
                    background: "var(--cream-100)",
                    borderRadius: "var(--radius-sm)",
                  }}
                >
                  <div
                    style={{
                      fontSize: "0.72rem",
                      fontWeight: 600,
                      textTransform: "uppercase",
                      letterSpacing: "0.06em",
                      color: "var(--stone-500)",
                      marginBottom: "4px",
                    }}
                  >
                    {t('matching.source')}
                  </div>
                  <div style={{ fontWeight: 500, fontSize: "0.875rem" }}>
                    {explain.source.name}
                  </div>
                  <div className="mono" style={{ marginTop: "4px" }}>
                    {explain.source.reference}
                  </div>
                </div>
                <div
                  style={{
                    padding: "12px",
                    background: "var(--cream-100)",
                    borderRadius: "var(--radius-sm)",
                  }}
                >
                  <div
                    style={{
                      fontSize: "0.72rem",
                      fontWeight: 600,
                      textTransform: "uppercase",
                      letterSpacing: "0.06em",
                      color: "var(--stone-500)",
                      marginBottom: "4px",
                    }}
                  >
p                    {t('matching.target')}
                  </div>
                  <div style={{ fontWeight: 500, fontSize: "0.875rem" }}>
                    {explain.target.name}
                  </div>
                  <div className="mono" style={{ marginTop: "4px" }}>
                    {explain.target.reference}
                  </div>
                </div>
              </div>

              <div
                style={{
                  marginBottom: "12px",
                  display: "flex",
                  gap: "10px",
                  alignItems: "center",
                }}
              >
                <span
                  className={`badge ${explain.matched ? "badge-success" : "badge-warning"}`}
                >
                  {explain.matched ? t('matching.matched') : t('matching.not_matched')}
                </span>
                {explain.method && (
                  <span className={`badge ${methodBadge(explain.method)}`}>
                    {explain.method}
                  </span>
                )}
                {explain.confidence > 0 && (
                  <span className="mono">
                    {(explain.confidence * 100).toFixed(0)}% {t('matching.confidence_label')}
                  </span>
                )}
              </div>

              <div className="card-header" style={{ marginTop: "8px" }}>
                <span className="card-title">{t('matching.signals')}</span>
              </div>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: "8px",
                }}
              >
                {(
                  [
                    [t('matching.ean_match'), explain.signals.ean_match],
                    [t('matching.brand_match'), explain.signals.brand_match],
                    [t('matching.model_exact'), explain.signals.model_exact],
                    [t('matching.series_match'), explain.signals.series_match],
                  ] as [string, boolean][]
                ).map(([label, val]) => (
                  <div
                    key={label}
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      padding: "8px 12px",
                      background: "var(--cream-100)",
                      borderRadius: "var(--radius-sm)",
                    }}
                  >
                    <span
                      style={{
                        fontSize: "0.84rem",
                        color: "var(--stone-700)",
                      }}
                    >
                      {label}
                    </span>
                    <span
                      className={`badge ${val ? "badge-success" : "badge-warning"}`}
                    >
                      {val ? t('matching.yes') : t('matching.no')}
                    </span>
                  </div>
                ))}
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    padding: "8px 12px",
                    background: "var(--cream-100)",
                    borderRadius: "var(--radius-sm)",
                  }}
                >
                  <span
                    style={{
                      fontSize: "0.84rem",
                      color: "var(--stone-700)",
                    }}
                  >
                    {t('matching.fuzzy_token_sort')}
                  </span>
                  <span className="mono">
                    {explain.signals.fuzzy_token_sort.toFixed(0)}%
                  </span>
                </div>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    padding: "8px 12px",
                    background: "var(--cream-100)",
                    borderRadius: "var(--radius-sm)",
                  }}
                >
                  <span
                    style={{
                      fontSize: "0.84rem",
                      color: "var(--stone-700)",
                    }}
                  >
                    {t('matching.fuzzy_token_set')}
                  </span>
                  <span className="mono">
                    {explain.signals.fuzzy_token_set.toFixed(0)}%
                  </span>
                </div>
                {explain.signals.model_prefix_match > 0 && (
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      padding: "8px 12px",
                      background: "var(--cream-100)",
                      borderRadius: "var(--radius-sm)",
                    }}
                  >
                    <span
                      style={{
                        fontSize: "0.84rem",
                        color: "var(--stone-700)",
                      }}
                    >
                      {t('matching.model_prefix')}
                    </span>
                    <span className="mono">
                      {explain.signals.model_prefix_match}
                    </span>
                  </div>
                )}
                {explain.signals.screen_size.source != null && (
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      padding: "8px 12px",
                      background: "var(--cream-100)",
                      borderRadius: "var(--radius-sm)",
                    }}
                  >
                    <span
                      style={{
                        fontSize: "0.84rem",
                        color: "var(--stone-700)",
                      }}
                    >
                      Screen: {explain.signals.screen_size.source}" vs{" "}
                      {explain.signals.screen_size.target}"
                    </span>
                    <span
                      className={`badge ${explain.signals.screen_size.match ? "badge-success" : "badge-warning"}`}
                    >
                      {explain.signals.screen_size.match
                        ? t('matching.screen_match')
                        : t('matching.screen_mismatch')}
                    </span>
                  </div>
                )}
                {explain.signals.ean_shared.length > 0 && (
                  <div
                    style={{
                      gridColumn: "1 / -1",
                      padding: "8px 12px",
                      background: "var(--cream-100)",
                      borderRadius: "var(--radius-sm)",
                    }}
                  >
                    <span
                      style={{
                        fontSize: "0.84rem",
                        color: "var(--stone-700)",
                      }}
                    >
                      {t('matching.shared_eans')}:{" "}
                    </span>
                    <span className="mono">
                      {explain.signals.ean_shared.join(", ")}
                    </span>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {explainLoading && (
          <div
            style={{
              position: "fixed",
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              background: "rgba(26,21,16,0.3)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              zIndex: 100,
            }}
          >
            <div
              className="card"
              style={{ padding: "32px", textAlign: "center" }}
            >
              <span
                className="spinner"
                style={{ width: "28px", height: "28px" }}
              />
              <p style={{ marginTop: "12px", color: "var(--stone-600)" }}>
                {t('matching.analyzing')}
              </p>
            </div>
          </div>
        )}
      </div>
    </>
  );
}