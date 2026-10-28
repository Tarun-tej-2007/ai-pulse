import React, { useState, useEffect } from "react";
import Login from "./pages/Login.jsx";
import OrgPicker from "./pages/OrgPicker.jsx";
import Diagnostic from "./pages/Diagnostic.jsx";
import Report from "./pages/Report.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import { getToken, setToken, api } from "./api.js";

export default function App() {
  const [step, setStep] = useState("login");
  const [session, setSession] = useState(null);
  const [org, setOrg] = useState(null);

  function handleLogout() {
    setToken("");
    localStorage.removeItem("token");
    setSession(null);
    setOrg(null);
    setStep("login");
  }

  function handlePickOrg(chosenOrg) {
    setOrg(chosenOrg);
    if (chosenOrg.role === "admin") {
      setStep("dashboard");
    } else {
      // Check if employee already answered questions
      api("/reports/me")
        .then((rep) => {
          if (rep.answered > 0) {
            setStep("report");
          } else {
            setStep("diagnostic");
          }
        })
        .catch(() => setStep("diagnostic"));
    }
  }

  return (
    <div className="wrap">
      <header className="app-header">
        <div className="app-brand">
          <h1>AI Pulse</h1>
          {org && (
            <span style={{ fontSize: "0.85rem", background: "var(--primary-light)", color: "var(--primary)", padding: "3px 10px", borderRadius: "12px", fontWeight: 600 }}>
              {org.org_name} ({org.role})
            </span>
          )}
        </div>
        {session && (
          <div className="nav-controls">
            <span className="session-info">{session.name}</span>
            {session.organizations && session.organizations.length > 1 && (
              <button className="btn-secondary" onClick={() => setStep("org")}>
                Switch Org
              </button>
            )}
            <button className="btn-secondary" onClick={handleLogout}>
              Sign out
            </button>
          </div>
        )}
      </header>

      {step === "login" && (
        <Login onDone={(s) => { setSession(s); setStep("org"); }} />
      )}

      {step === "org" && session && (
        <OrgPicker
          orgs={session.organizations}
          onPick={handlePickOrg}
        />
      )}

      {step === "diagnostic" && (
        <Diagnostic
          onDone={() => setStep("report")}
          onCancel={() => setStep("report")}
        />
      )}

      {step === "report" && (
        <Report
          onRetake={() => setStep("diagnostic")}
          onSwitchOrg={() => setStep("org")}
        />
      )}

      {step === "dashboard" && org && (
        <Dashboard
          org={org}
          onSwitchOrg={() => setStep("org")}
        />
      )}
    </div>
  );
}
