import { useEffect, useState } from "react";
import { getDashboard } from "../services/api";
import type { DashboardStats } from "../types/product";

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getDashboard()
      .then(setStats)
      .catch(() => setStats(null))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <>
        <div className="page-header">
          <h1>Dashboard</h1>
          <p>Loading stats...</p>
        </div>
      </>
    );
  }

  if (!stats || stats.source_count === 0) {
    return (
      <>
        <div className="page-header">
          <h1>Dashboard</h1>
          <p>Overview of your product matching workspace</p>
        </div>
        <div className="page-body">
          <div className="card">
            <div className="empty-state">
              <h3>No data loaded</h3>
              <p>
                Run the pipeline first to populate the database, then refresh.
              </p>
            </div>
          </div>
        </div>
      </>
    );
  }

  const confDist = stats.confidence_distribution;
  const confTotal =
    (confDist.excellent || 0) +
    (confDist.high || 0) +
    (confDist.medium || 0) +
    (confDist.low || 0);

  return (
    <>
      <div className="page-header">
        <h1>Dashboard</h1>
        <p>Overview of your product matching workspace</p>
      </div>
      <div className="page-body">
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-label">Sources Matched</div>
            <div className="stat-value">
              {stats.sources_matched}/{stats.source_count}
            </div>
            <div className="stat-note">{stats.coverage_pct}% coverage</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Total Matches</div>
            <div className="stat-value">{stats.match_count}</div>
            <div className="stat-note">Across all strategies</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Target Pool</div>
            <div className="stat-value">{stats.target_count}</div>
            <div className="stat-note">{stats.retailers.length} retailers</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Strategies</div>
            <div className="stat-value">{stats.methods.length}</div>
            <div className="stat-note">
              {stats.methods.map((m) => m.label).join(", ")}
            </div>
          </div>
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: "16px",
          }}
        >
          <div className="card">
            <div className="card-header">
              <span className="card-title">Matching Methods</span>
            </div>
            <div style={{ padding: "12px 0" }}>
              {stats.methods.map((m) => (
                <div
                  key={m.method}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "12px",
                    padding: "8px 0",
                    borderBottom: "1px solid var(--cream-200)",
                  }}
                >
                  <span
                    style={{
                      flex: "0 0 120px",
                      fontSize: "0.85rem",
                      fontWeight: 500,
                    }}
                  >
                    {m.label}
                  </span>
                  <div
                    style={{
                      flex: 1,
                      height: "8px",
                      background: "var(--cream-200)",
                      borderRadius: "4px",
                      overflow: "hidden",
                    }}
                  >
                    <div
                      style={{
                        width: `${Math.min((m.count / stats.match_count) * 100, 100)}%`,
                        height: "100%",
                        background: "var(--accent)",
                        borderRadius: "4px",
                      }}
                    />
                  </div>
                  <span
                    className="mono"
                    style={{
                      flex: "0 0 36px",
                      textAlign: "right",
                      fontSize: "0.85rem",
                    }}
                  >
                    {m.count}
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div className="card">
            <div className="card-header">
              <span className="card-title">Confidence Distribution</span>
            </div>
            <div style={{ padding: "12px 0" }}>
              {[
                {
                  label: "Excellent (95%+)",
                  count: confDist.excellent || 0,
                  color: "#16a34a",
                },
                {
                  label: "High (85-95%)",
                  count: confDist.high || 0,
                  color: "#2563eb",
                },
                {
                  label: "Medium (70-85%)",
                  count: confDist.medium || 0,
                  color: "#d97706",
                },
                {
                  label: "Low (<70%)",
                  count: confDist.low || 0,
                  color: "#dc2626",
                },
              ].map((tier) => (
                <div
                  key={tier.label}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "12px",
                    padding: "8px 0",
                    borderBottom: "1px solid var(--cream-200)",
                  }}
                >
                  <span
                    style={{
                      flex: "0 0 120px",
                      fontSize: "0.85rem",
                      fontWeight: 500,
                    }}
                  >
                    {tier.label}
                  </span>
                  <div
                    style={{
                      flex: 1,
                      height: "8px",
                      background: "var(--cream-200)",
                      borderRadius: "4px",
                      overflow: "hidden",
                    }}
                  >
                    <div
                      style={{
                        width: confTotal
                          ? `${(tier.count / confTotal) * 100}%`
                          : "0%",
                        height: "100%",
                        background: tier.color,
                        borderRadius: "4px",
                      }}
                    />
                  </div>
                  <span
                    className="mono"
                    style={{
                      flex: "0 0 36px",
                      textAlign: "right",
                      fontSize: "0.85rem",
                    }}
                  >
                    {tier.count}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {stats.brands.length > 0 && (
          <div className="card" style={{ marginTop: "16px" }}>
            <div className="card-header">
              <span className="card-title">Brands</span>
            </div>
            <div className="table-wrapper">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Brand</th>
                    <th>Sources Matched</th>
                    <th>Total Matches</th>
                  </tr>
                </thead>
                <tbody>
                  {stats.brands.map((b) => (
                    <tr key={b.brand}>
                      <td>
                        <strong>{b.brand}</strong>
                      </td>
                      <td>{b.matched_sources}</td>
                      <td>{b.total_matches}</td>
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
