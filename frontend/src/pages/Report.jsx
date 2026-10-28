import React, { useEffect, useState } from "react";
import { api } from "../api.js";

export default function Report({ onRetake, onSwitchOrg }) {
  const [report, setReport] = useState(null);
  const [plan, setPlan] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteNotice, setDeleteNotice] = useState(null);

  function loadData() {
    setLoading(true);
    Promise.all([
      api("/reports/me"),
      api("/practice-plan/me").catch(() => null),
    ])
      .then(([rep, pl]) => {
        setReport(rep);
        setPlan(pl);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || "Failed to load report data");
        setLoading(false);
      });
  }

  useEffect(() => {
    loadData();
  }, []);

  async function handleDelete() {
    setIsDeleting(true);
    try {
      const res = await api("/diagnostic/me", { method: "DELETE" });
      setShowDeleteModal(false);
      setIsDeleting(false);
      setDeleteNotice(res.message || "Assessment deleted successfully.");
      // Reload report and plan data
      loadData();
    } catch (err) {
      alert("Failed to delete assessment: " + err.message);
      setIsDeleting(false);
    }
  }

  async function handleToggleActivity(activityKey, currentCompleted) {
    try {
      await api("/practice-plan/me/toggle", {
        method: "POST",
        body: JSON.stringify({ activity_key: activityKey, completed: !currentCompleted }),
      });
      // Refresh plan
      const updatedPlan = await api("/practice-plan/me");
      setPlan(updatedPlan);
    } catch (err) {
      alert("Failed to update activity status: " + err.message);
    }
  }

  if (loading) {
    return <div className="card"><p>Loading your AI diagnostic report...</p></div>;
  }

  if (error) {
    return <div className="card"><div className="error-banner">{error}</div></div>;
  }

  if (!report) return null;

  const hasData = report.answered > 0;
  const completedActivities = plan?.activities?.filter((a) => a.completed)?.length || 0;
  const totalActivities = plan?.activities?.length || 0;

  return (
    <div>
      {deleteNotice && (
        <div className="success-banner" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span>{deleteNotice}</span>
          <button className="btn-secondary" style={{ padding: "4px 8px" }} onClick={() => setDeleteNotice(null)}>✕</button>
        </div>
      )}

      {!hasData ? (
        <div className="card" style={{ textAlign: "center", padding: "40px 20px" }}>
          <h2>No Completed Assessment</h2>
          <p style={{ color: "var(--text-muted)", maxWidth: "460px", margin: "10px auto 24px" }}>
            You haven't completed the AI diagnostic yet, or your previous assessment was deleted.
          </p>
          {onRetake && (
            <button onClick={onRetake}>
              Take AI Diagnostic
            </button>
          )}
        </div>
      ) : (
        <>
          <div className="card">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "12px" }}>
              <div>
                <h2>{report.name} — AI Diagnostic Report</h2>
                <div style={{ color: "var(--text-muted)", fontSize: "0.875rem" }}>
                  Organization: {report.organization}
                </div>
              </div>
              <div style={{ display: "flex", gap: "8px" }}>
                {onSwitchOrg && (
                  <button className="btn-secondary" onClick={onSwitchOrg}>
                    Switch Org
                  </button>
                )}
                {onRetake && (
                  <button className="btn-secondary" onClick={onRetake}>
                    Retake
                  </button>
                )}
                <button
                  className="danger"
                  style={{ fontSize: "0.85rem", padding: "8px 12px" }}
                  onClick={() => setShowDeleteModal(true)}
                >
                  Delete My Data
                </button>
              </div>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "16px", margin: "20px 0", padding: "16px", background: "#f8fafc", borderRadius: "8px", border: "1px solid var(--border)" }}>
              <div>
                <span className={`badge badge-${report.level.toLowerCase()}`} style={{ fontSize: "0.9rem", padding: "6px 14px" }}>
                  {report.level}
                </span>
              </div>
              <div>
                <div style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>Average Maturity Score</div>
                <div style={{ fontSize: "1.25rem", fontWeight: 700 }}>
                  {report.average_score} <span style={{ fontSize: "0.9rem", fontWeight: 400, color: "var(--text-muted)" }}>/ 5.0</span>
                </div>
              </div>
              <div style={{ marginLeft: "auto", fontSize: "0.85rem", color: "var(--text-muted)" }}>
                {report.answered} questions answered
              </div>
            </div>

            <h3>Identified Risks</h3>
            {report.risks.length === 0 ? (
              <p style={{ color: "var(--success)", fontSize: "0.9rem" }}>
                ✓ No high-risk AI habits detected in your answers.
              </p>
            ) : (
              <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
                {report.risks.map((r) => (
                  <span
                    key={r}
                    style={{
                      background: "var(--danger-light)",
                      color: "var(--danger)",
                      border: "1px solid #fecaca",
                      borderRadius: "6px",
                      padding: "4px 10px",
                      fontSize: "0.825rem",
                      fontWeight: 600,
                    }}
                  >
                    ⚠️ {r.replace(/_/g, " ")}
                  </span>
                ))}
              </div>
            )}

            <h3>Recommended Next Steps</h3>
            <ul>
              {report.next_steps.map((s, idx) => (
                <li key={idx} style={{ marginBottom: "6px", fontSize: "0.95rem" }}>{s}</li>
              ))}
            </ul>
          </div>

          {/* AI Practice Plan (Original Feature) */}
          {plan && plan.has_assessment && (
            <div className="card plan-container">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <h2>Personalized AI Practice Plan</h2>
                  <p style={{ color: "var(--text-muted)", fontSize: "0.875rem", margin: "4px 0 0" }}>
                    Actionable exercises tailored to your role and identified improvement areas.
                  </p>
                </div>
                <div style={{ background: "var(--primary-light)", color: "var(--primary)", padding: "4px 12px", borderRadius: "16px", fontWeight: 700, fontSize: "0.85rem" }}>
                  {completedActivities} / {totalActivities} Completed
                </div>
              </div>

              <div style={{ marginTop: "20px" }}>
                {plan.activities.map((act) => (
                  <div key={act.key} className={`plan-item ${act.completed ? "completed" : ""}`}>
                    <div className="plan-header">
                      <div>
                        <span className="plan-area">{act.area}</span>
                        <div className="plan-title">{act.title}</div>
                      </div>
                      <button
                        className={act.completed ? "btn-secondary" : ""}
                        style={{ fontSize: "0.8rem", padding: "6px 12px" }}
                        onClick={() => handleToggleActivity(act.key, act.completed)}
                      >
                        {act.completed ? "✓ Completed" : "Mark Complete"}
                      </button>
                    </div>
                    <div className="plan-exercise">
                      <strong>Exercise:</strong> {act.exercise}
                    </div>
                    <div className="plan-criterion">
                      <strong>Completion Criterion:</strong> {act.criterion}
                    </div>
                    {act.completed_at && (
                      <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "6px" }}>
                        Completed on {new Date(act.completed_at).toLocaleDateString()}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {/* Confirmation Modal for Right to Delete */}
      {showDeleteModal && (
        <div className="modal-backdrop">
          <div className="modal-content">
            <h3 style={{ marginTop: 0, color: "var(--danger)" }}>Delete Assessment and Report?</h3>
            <p style={{ fontSize: "0.925rem", color: "var(--text-main)", lineHeight: 1.6 }}>
              This action permanently removes all your diagnostic answers, maturity score, and personalized practice plan from the system.
            </p>
            <p style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
              In accordance with corporate privacy guidelines, your data will immediately disappear from all company and department dashboards.
            </p>
            <div className="modal-actions">
              <button
                className="btn-secondary"
                disabled={isDeleting}
                onClick={() => setShowDeleteModal(false)}
              >
                Cancel
              </button>
              <button
                className="danger"
                disabled={isDeleting}
                onClick={handleDelete}
              >
                {isDeleting ? "Deleting..." : "Permanently Delete"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
