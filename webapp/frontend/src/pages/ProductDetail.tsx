import { useEffect, useState, useCallback } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { getProduct, getSimilar } from "../services/api";
import { useI18n } from "../i18n";
import { Price, useCurrency } from "../CurrencyContext";
import type {
  SourceProduct,
  MatchEntry,
  SimilarProduct,
} from "../types/product";

const RETAILER_COLORS: Record<string, string> = {
  mediamarkt: "#df0000",
  saturn: "#004f9f",
  "expert.at": "#e85e0c",
  "cyberport.at": "#003c7e",
  "electronic4you.at": "#00a651",
  "e-tec.at": "#ff6600",
};

function retailerColor(retailer: string): string {
  const key = retailer.toLowerCase().replace(/\s+/g, "");
  for (const [k, v] of Object.entries(RETAILER_COLORS)) {
    if (key.includes(k.replace(/[.\s]/g, ""))) return v;
  }
  return "var(--info)";
}

function verdictText(method: string, confidence: number): string {
  const conf =
    confidence >= 0.9
      ? "Very high"
      : confidence >= 0.75
        ? "High"
        : confidence >= 0.6
          ? "Moderate"
          : "Low";
  const methodLabels: Record<string, string> = {
    ean: "Identical EAN barcode",
    model_number: "Exact model number match",
    model_series: "Same model series",
    product_line: "Same product line",
    product_type: "Same product type",
    screen_size: "Screen size match",
    fuzzy_model: "Fuzzy model match",
    fuzzy_name: "Fuzzy name similarity",
    fuzzy: "Fuzzy name similarity",
    embedding: "Semantic embedding match",
    vision: "Visual image similarity",
    llm: "AI-verified match",
    scrape: "Found via web scrape",
  };
  const m = method.toLowerCase();
  const label =
    Object.entries(methodLabels).find(([k]) => m.includes(k))?.[1] ?? method;
  return `${label} · ${conf} confidence`;
}

function verdictIcon(method: string): string {
  const m = method.toLowerCase();
  if (m.includes("ean")) return "\u2713";
  if (m.includes("model")) return "#";
  if (m.includes("fuzzy")) return "\u223C";
  if (m.includes("embedding")) return "\u2261";
  if (m.includes("vision")) return "\u25CE";
  if (m.includes("llm")) return "\u2605";
  if (m.includes("scrape")) return "\u21BB";
  return "\u2022";
}

function normalizeSpecValue(val: string): string {
  return val.replace(/\s+/g, " ").trim().toLowerCase();
}

export default function ProductDetail() {
  const { ref } = useParams<{ ref: string }>();
  const navigate = useNavigate();
  const { t, tSpec } = useI18n();
  const { format } = useCurrency();
  const [product, setProduct] = useState<SourceProduct | null>(null);
  const [matches, setMatches] = useState<MatchEntry[]>([]);
  const [similar, setSimilar] = useState<SimilarProduct[]>([]);
  const [loading, setLoading] = useState(true);
  const [diffTarget, setDiffTarget] = useState<string | null>(null);
  const [targetSpecs, setTargetSpecs] = useState<Record<string, string> | null>(
    null,
  );
  const [targetLoading, setTargetLoading] = useState(false);

  useEffect(() => {
    if (!ref) return;
    setLoading(true);
    setDiffTarget(null);
    setTargetSpecs(null);
    Promise.all([
      getProduct(ref)
        .then((d) => {
          setProduct(d.product);
          setMatches(d.matches ?? []);
        })
        .catch(() => {}),
      getSimilar(ref, 12, 0.5)
        .then((d) => setSimilar(d.similar ?? []))
        .catch(() => {}),
    ]).finally(() => setLoading(false));
  }, [ref]);

  // Keyboard: Escape to go back
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        navigate("/products");
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [navigate]);

  const toggleDiff = useCallback(
    (targetRef: string) => {
      if (diffTarget === targetRef) {
        setDiffTarget(null);
        setTargetSpecs(null);
        return;
      }
      setDiffTarget(targetRef);
      setTargetLoading(true);
      setTargetSpecs(null);
      getProduct(targetRef)
        .then((d) => setTargetSpecs(d.product?.specifications ?? {}))
        .catch(() => setTargetSpecs({}))
        .finally(() => setTargetLoading(false));
    },
    [diffTarget],
  );

  if (loading) {
    return (
      <>
        <div className="page-header">
          <h1>{t("common.loading")}</h1>
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

  if (!product) {
    return (
      <>
        <div className="page-header">
          <h1>{t("product.not_found")}</h1>
        </div>
        <div className="page-body">
          <button
            className="btn btn-secondary"
            onClick={() => navigate("/products")}
          >
            {t("product.back")}
          </button>
        </div>
      </>
    );
  }

  const matchedRefs = new Set(matches.map((m) => m.target_reference));
  const nonIdenticalSimilar = similar.filter(
    (s) => !matchedRefs.has(s.reference),
  );
  const price = product.price_eur ?? product.price;
  const sourceSpecs = product.specifications ?? {};

  // Price spread data
  const pricesWithRetailer = matches
    .filter((m) => m.target_price != null)
    .map((m) => ({
      price: m.target_price!,
      retailer: m.target_retailer,
      ref: m.target_reference,
    }));
  if (price != null) {
    pricesWithRetailer.push({
      price,
      retailer: product.retailer ?? "Source",
      ref: product.reference,
    });
  }
  const allPrices = pricesWithRetailer.map((p) => p.price);
  const minPrice = allPrices.length > 0 ? Math.min(...allPrices) : 0;
  const maxPrice = allPrices.length > 0 ? Math.max(...allPrices) : 0;
  const priceRange = maxPrice - minPrice;
  const showPriceSpread = pricesWithRetailer.length >= 2 && priceRange > 0;

  // Spec diff computation
  const renderSpecDiff = () => {
    if (!diffTarget || !targetSpecs) return null;
    const srcKeys = Object.keys(sourceSpecs);
    const tgtKeys = Object.keys(targetSpecs);
    const allKeys = [...new Set([...srcKeys, ...tgtKeys])];

    return (
      <div className="spec-diff" style={{ margin: "0 0 16px" }}>
        <div className="spec-diff-col">
          <div className="spec-diff-header">
            Source — {product.name.slice(0, 40)}
          </div>
          {allKeys.map((key) => {
            const srcVal = sourceSpecs[key];
            const tgtVal = targetSpecs[key];
            const hasBoth = srcVal !== undefined && tgtVal !== undefined;
            const match =
              hasBoth &&
              normalizeSpecValue(srcVal) === normalizeSpecValue(tgtVal);
            const cls =
              srcVal === undefined
                ? "diff-missing"
                : hasBoth
                  ? match
                    ? "diff-match"
                    : "diff-mismatch"
                  : "";
            return (
              <div key={key} className={`spec-diff-row ${cls}`}>
                <span className="spec-diff-key">{tSpec(key)}</span>
                <span className="spec-diff-val">{srcVal ?? "--"}</span>
              </div>
            );
          })}
        </div>
        <div className="spec-diff-col">
          <div className="spec-diff-header">Target — {diffTarget}</div>
          {allKeys.map((key) => {
            const srcVal = sourceSpecs[key];
            const tgtVal = targetSpecs[key];
            const hasBoth = srcVal !== undefined && tgtVal !== undefined;
            const match =
              hasBoth &&
              normalizeSpecValue(srcVal) === normalizeSpecValue(tgtVal);
            const cls =
              tgtVal === undefined
                ? "diff-missing"
                : hasBoth
                  ? match
                    ? "diff-match"
                    : "diff-mismatch"
                  : "";
            return (
              <div key={key} className={`spec-diff-row ${cls}`}>
                <span className="spec-diff-key">{tSpec(key)}</span>
                <span className="spec-diff-val">{tgtVal ?? "--"}</span>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  return (
    <>
      <div className="page-header">
        <button
          className="btn btn-secondary"
          onClick={() => navigate("/products")}
          style={{ marginBottom: "8px" }}
        >
          &larr; {t("product.back")}
          <span
            style={{
              fontSize: "0.68rem",
              color: "var(--stone-500)",
              marginLeft: "8px",
            }}
          >
            Esc
          </span>
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
                <svg
                  width="64"
                  height="64"
                  viewBox="0 0 64 64"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.2"
                  opacity="0.25"
                >
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
                  <span className="meta-label">{t("common.brand")}</span>
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
                  <span className="meta-label">{t("common.retailer")}</span>
                  <span className="meta-value">
                    <span className="badge badge-info">{product.retailer}</span>
                  </span>
                </div>
              )}
              {price != null && (
                <div className="meta-row">
                  <span className="meta-label">{t("common.price")}</span>
                  <Price
                    value={price}
                    className="meta-value"
                    style={{ fontSize: "1.2rem", fontWeight: 600 }}
                  />
                </div>
              )}
              {product.category && (
                <div className="meta-row">
                  <span className="meta-label">{t("common.category")}</span>
                  <span className="meta-value">
                    <span className="badge badge-accent">
                      {product.category}
                    </span>
                  </span>
                </div>
              )}
              {product.url && (
                <div className="meta-row">
                  <span className="meta-label">{t("common.url")}</span>
                  <a
                    href={product.url}
                    target="_blank"
                    rel="noreferrer"
                    className="meta-value"
                    style={{ color: "var(--accent)", wordBreak: "break-all" }}
                  >
                    {t("common.view_original")} &rarr;
                  </a>
                </div>
              )}
            </div>
            {product.specifications &&
              Object.keys(product.specifications).length > 0 && (
                <div style={{ marginTop: "16px" }}>
                  <h3
                    style={{
                      fontSize: "0.88rem",
                      fontWeight: 600,
                      marginBottom: "8px",
                      color: "var(--stone-700)",
                    }}
                  >
                    {t("product.specifications")}
                  </h3>
                  <div className="product-detail-meta">
                    {Object.entries(product.specifications)
                      .slice(0, 10)
                      .map(([k, v]) => (
                        <div className="meta-row" key={k}>
                          <span className="meta-label">{tSpec(k)}</span>
                          <span className="meta-value">{v}</span>
                        </div>
                      ))}
                  </div>
                </div>
              )}
          </div>
        </div>

        {/* Price Spread */}
        {showPriceSpread && (
          <div className="price-spread" style={{ marginTop: "24px" }}>
            <span className="price-spread-label">Price Spread</span>
            <div style={{ flex: 1 }}>
              <div className="price-spread-track">
                {pricesWithRetailer.map((p, i) => {
                  const pct =
                    priceRange > 0
                      ? ((p.price - minPrice) / priceRange) * 100
                      : 50;
                  const isSource = p.ref === product.reference;
                  return (
                    <div
                      key={i}
                      className="price-spread-dot"
                      data-source={isSource ? "true" : undefined}
                      style={{
                        left: `${pct}%`,
                        background: isSource
                          ? "var(--accent)"
                          : retailerColor(p.retailer),
                      }}
                      title={`${p.retailer}: ${format(p.price)}`}
                    />
                  );
                })}
              </div>
              <div className="price-spread-range">
                <span>{format(minPrice)}</span>
                <span>{format(maxPrice)}</span>
              </div>
            </div>
          </div>
        )}

        {/* Matches */}
        <div className="card" style={{ marginTop: "24px" }}>
          <div className="card-header">
            <span className="card-title">
              {t("product.matches")} ({matches.length})
            </span>
          </div>
          {matches.length === 0 ? (
            <p style={{ color: "var(--stone-500)", fontSize: "0.875rem" }}>
              {t("product.no_matches")}
            </p>
          ) : (
            <>
              <div
                className="table-wrapper"
                style={{ border: "none", boxShadow: "none" }}
              >
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Target Ref</th>
                      <th>Product Name</th>
                      <th>{t("common.retailer")}</th>
                      <th>{t("common.price")}</th>
                      <th>Method</th>
                      <th>Confidence</th>
                      <th style={{ width: "36px" }}></th>
                    </tr>
                  </thead>
                  <tbody>
                    {matches.map((m) => (
                      <>
                        <tr key={m.target_reference}>
                          <td>
                            <Link
                              to={`/products/${m.target_reference}`}
                              className="mono"
                              style={{ color: "var(--accent)" }}
                            >
                              {m.target_reference}
                            </Link>
                          </td>
                          <td>
                            <span
                              className="truncate"
                              style={{ display: "block", maxWidth: "280px" }}
                            >
                              {m.target_name}
                            </span>
                            <div
                              className="match-verdict"
                              style={{ marginTop: "4px" }}
                            >
                              <span className="match-verdict-icon">
                                {verdictIcon(m.method)}
                              </span>
                              {verdictText(m.method, m.confidence)}
                            </div>
                          </td>
                          <td>
                            <span className="badge badge-info">
                              {m.target_retailer}
                            </span>
                          </td>
                          <td>
                            <Price value={m.target_price} />
                          </td>
                          <td>
                            <span className="badge badge-accent">
                              {m.method
                                .replace(/_/g, " ")
                                .replace(/\b\w/g, (c) => c.toUpperCase())}
                            </span>
                          </td>
                          <td>
                            <div className="confidence-bar">
                              <span
                                className="mono"
                                style={{ minWidth: "36px" }}
                              >
                                {(m.confidence * 100).toFixed(0)}%
                              </span>
                              <div className="confidence-track">
                                <div
                                  className={`confidence-fill ${m.confidence >= 0.85 ? "high" : m.confidence >= 0.65 ? "medium" : "low"}`}
                                  style={{ width: `${m.confidence * 100}%` }}
                                />
                              </div>
                            </div>
                          </td>
                          <td>
                            {Object.keys(sourceSpecs).length > 0 && (
                              <button
                                className={`diff-toggle ${diffTarget === m.target_reference ? "active" : ""}`}
                                onClick={() => toggleDiff(m.target_reference)}
                                title="Compare specs"
                              >
                                Diff
                              </button>
                            )}
                          </td>
                        </tr>
                        {diffTarget === m.target_reference && (
                          <tr key={`${m.target_reference}-diff`}>
                            <td colSpan={7} style={{ padding: "12px 8px" }}>
                              {targetLoading ? (
                                <div
                                  style={{
                                    textAlign: "center",
                                    padding: "20px",
                                  }}
                                >
                                  <span
                                    className="spinner"
                                    style={{ width: "20px", height: "20px" }}
                                  />
                                  <span
                                    style={{
                                      marginLeft: "8px",
                                      fontSize: "0.8rem",
                                      color: "var(--stone-500)",
                                    }}
                                  >
                                    Loading specs...
                                  </span>
                                </div>
                              ) : (
                                renderSpecDiff()
                              )}
                            </td>
                          </tr>
                        )}
                      </>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>

        {/* Similar Products (excluding already-matched) */}
        {nonIdenticalSimilar.length > 0 && (
          <div className="card" style={{ marginTop: "24px" }}>
            <div className="card-header">
              <span className="card-title">
                {t("product.similar")} ({nonIdenticalSimilar.length})
              </span>
            </div>
            <div
              className="table-wrapper"
              style={{ border: "none", boxShadow: "none" }}
            >
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Ref</th>
                    <th>Product Name</th>
                    <th>{t("common.retailer")}</th>
                    <th>{t("common.price")}</th>
                    <th>{t("common.similar")}</th>
                  </tr>
                </thead>
                <tbody>
                  {nonIdenticalSimilar.slice(0, 10).map((s) => (
                    <tr key={s.reference}>
                      <td>
                        <Link
                          to={`/products/${s.reference}`}
                          className="mono"
                          style={{ color: "var(--accent)" }}
                        >
                          {s.reference}
                        </Link>
                      </td>
                      <td>
                        <div>{s.name}</div>
                        {s.brand && (
                          <div
                            style={{
                              fontSize: "0.76rem",
                              color: "var(--stone-500)",
                              marginTop: "2px",
                            }}
                          >
                            {s.brand}
                          </div>
                        )}
                      </td>
                      <td>
                        <span className="badge badge-info">{s.retailer}</span>
                      </td>
                      <td>
                        <Price value={s.price} />
                      </td>
                      <td>
                        <div className="confidence-bar">
                          <span className="mono" style={{ minWidth: "36px" }}>
                            {(s.similarity * 100).toFixed(0)}%
                          </span>
                          <div className="confidence-track">
                            <div
                              className={`confidence-fill ${s.similarity >= 0.85 ? "high" : s.similarity >= 0.65 ? "medium" : "low"}`}
                              style={{ width: `${s.similarity * 100}%` }}
                            />
                          </div>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
