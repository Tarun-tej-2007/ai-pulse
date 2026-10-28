import React, { useEffect, useState } from "react";
import { api } from "../api.js";

export default function Dashboard({ org, onSwitchOrg }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    api(`/dashboard?org_id=${org.org_id}`)
      .then((res) => {
        setData(res);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || "Failed to load dashboard data");
        setLoading(false);
      });
  }, [org]);

  if (loading) {
    return <div className="card"><p>Loading leadership dashboard...</p></div>;
  }

  if (error) {
    return (
      <div className="card">
        <div className="error-banner">{error}</div>
        {onSwitchOrg && <button onClick={onSwitchOrg}>Switch Organization</button>}
      </div>
    );
  }

  if (!data) return null;

  const suppressedCount = data.departments.filter((d) => d.suppressed).length;

  return (
    <div>
      <div className="privacy-callout">
        <div>
          <strong>Small-Group Privacy Protection Active:</strong>
          <div style={{ marginTop: "4px" }}>
            To safeguard individual employee confidentiality, department scores and risk details are automatically suppressed whenever fewer than {data.privacy_threshold || 5} completed responses are recorded.
          </div>
        </div>
      </div>

      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <h2>{data.organization} — AI Maturity Dashboard</h2>
            <div style={{ color: "var(--text-muted)", fontSize: "0.875rem" }}>
              Company-wide AI adoption and governance overview
            </div>
          </div>
          {onSwitchOrg && (
            <button className="btn-secondary" onClick={onSwitchOrg}>
              Switch Org
            </button>
          )}
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "16px", marginTop: "20px" }}>
          <div style={{ background: "#f8fafc", padding: "16px", borderRadius: "8px", border: "1px solid var(--border)" }}>
            <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", textTransform: "uppercase" }}>Departments</div>
            <div style={{ fontSize: "1.75rem", fontWeight: 700 }}>{data.departments.length}</div>
          </div>
          <div style={{ background: "#f8fafc", padding: "16px", borderRadius: "8px", border: "1px solid var(--border)" }}>
            <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", textTransform: "uppercase" }}>Protected Groups</div>
            <div style={{ fontSize: "1.75rem", fontWeight: 700, color: "var(--purple)" }}>{suppressedCount}</div>
          </div>
          <div style={{ background: "#f8fafc", padding: "16px", borderRadius: "8px", border: "1px solid var(--border)" }}>
            <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", textTransform: "uppercase" }}>Top Risks Tracked</div>
            <div style={{ fontSize: "1.75rem", fontWeight: 700, color: "var(--danger)" }}>{data.top_risks.length}</div>
          </div>
        </div>

        <h3>Department AI Maturity</h3>
        <table className="dept-table">
          <thead>
            <tr>
              <th>Department</th>
              <th>Staff</th>
              <th>Responded</th>
              <th>Average Score</th>
              <th>Maturity Level</th>
            </tr>
          </thead>
          <tbody>
            {data.departments.map((dept) => (
              <tr key={dept.department}>
                <td><strong>{dept.department}</strong></td>
                <td>{dept.employees}</td>
                <td>{dept.responded}</td>
                <td>
                  {dept.suppressed ? (
                    <span className="badge badge-protected" title={dept.privacy_note}>
                      Protected
                    </span>
                  ) : (
                    <span><strong>{dept.average_score}</strong> / 5.0</span>
                  )}
                </td>
                <td>
                  {dept.suppressed ? (
                    <span style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
                      {dept.level}
                    </span>
                  ) : (
                    <span className={`badge badge-${dept.level.toLowerCase()}`}>
                      {dept.level}
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        <h3>Company-Wide Key AI Risks</h3>
        {data.top_risks.length === 0 ? (
          <p style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>
            No high-priority aggregate risks identified across qualifying departments.
          </p>
        ) : (
          <div style={{ display: "flex", flexWrap: "wrap", gap: "10px", marginTop: "10px" }}>
            {data.top_risks.map(([riskName, count]) => (
              <div
                key={riskName}
                style={{
                  background: "var(--danger-light)",
                  border: "1px solid #fecaca",
                  borderRadius: "8px",
                  padding: "8px 14px",
                  display: "flex",
                  alignItems: "center",
                  gap: "10px",
                }}
              >
                <span style={{ fontWeight: 600, color: "var(--danger)", fontSize: "0.9rem" }}>
                  {riskName.replace(/_/g, " ")}
                </span>
                <span style={{ background: "var(--danger)", color: "#fff", borderRadius: "10px", padding: "2px 8px", fontSize: "0.75rem", fontWeight: 700 }}>
                  {count}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
