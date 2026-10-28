import React, { useEffect, useState } from "react";
import { api } from "../api.js";

export default function Diagnostic({ onDone, onCancel }) {
  const [questions, setQuestions] = useState([]);
  const [answers, setAnswers] = useState({});
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    api("/diagnostic/questions")
      .then((qs) => {
        setQuestions(qs);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || "Failed to load questions");
        setLoading(false);
      });
  }, []);

  async function submit(e) {
    e.preventDefault();
    setError(null);

    // Validate that at least all questions have answers
    const unanswered = questions.filter((q) => !answers[q.id] || !answers[q.id].trim());
    if (unanswered.length > 0) {
      setError(`Please answer all questions before submitting (${unanswered.length} remaining).`);
      return;
    }

    setSubmitting(true);
    try {
      const payload = Object.entries(answers).map(([question_id, answer]) => ({
        question_id,
        answer: answer.trim(),
      }));
      await api("/diagnostic/submit", {
        method: "POST",
        body: JSON.stringify({ answers: payload }),
      });
      onDone();
    } catch (err) {
      setError(err.message || "Submission failed. Please check your answers and try again.");
      setSubmitting(false);
    }
  }

  if (loading) {
    return <div className="card"><p>Loading your role-specific diagnostic questions...</p></div>;
  }

  return (
    <form className="card" onSubmit={submit}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
        <div>
          <h2>AI Diagnostic Assessment</h2>
          <div style={{ color: "var(--text-muted)", fontSize: "0.875rem" }}>
            Answer honestly to receive your personalized AI maturity profile and practice plan.
          </div>
        </div>
        {onCancel && (
          <button type="button" className="btn-secondary" onClick={onCancel}>
            Cancel
          </button>
        )}
      </div>

      {error && <div className="error-banner">{error}</div>}

      {questions.map((q, idx) => (
        <div key={q.id} style={{ marginBottom: "22px", paddingBottom: "18px", borderBottom: idx < questions.length - 1 ? "1px solid var(--border)" : "none" }}>
          <p style={{ fontWeight: 600, fontSize: "0.95rem", margin: "0 0 10px" }}>
            <span style={{ color: "var(--primary)", marginRight: "8px" }}>#{idx + 1}</span>
            {q.text}
          </p>
          {q.type === "mcq" ? (
            <select
              value={answers[q.id] || ""}
              onChange={(e) => setAnswers({ ...answers, [q.id]: e.target.value })}
              required
            >
              <option value="" disabled>Choose an option…</option>
              {q.options.map((o) => (
                <option key={o} value={o}>{o}</option>
              ))}
            </select>
          ) : (
            <textarea
              rows={4}
              placeholder="Describe your typical experience and approach in 1-3 sentences..."
              value={answers[q.id] || ""}
              onChange={(e) => setAnswers({ ...answers, [q.id]: e.target.value })}
              required
            />
          )}
        </div>
      ))}

      <div style={{ display: "flex", gap: "12px", marginTop: "16px" }}>
        <button type="submit" disabled={submitting}>
          {submitting ? "Analyzing & Scoring..." : "Submit Diagnostic"}
        </button>
      </div>
    </form>
  );
}
