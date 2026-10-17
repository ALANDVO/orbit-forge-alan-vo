import React, { useEffect, useState } from "react";
import { AuthProvider, useAuth } from "./services/auth";
import { fetchHealth } from "./services/api";
import type { HealthResponse } from "./services/api";
import IntentDashboard from "./components/IntentDashboard";
import "./App.css";

function Header() {
  const { user, login, logout, authenticated } = useAuth();
  return (
    <header className="header">
      <div className="header-title">Orbit Forge</div>
      <nav className="header-nav">
        {authenticated ? (
          <>
            <span className="header-user">{user?.subject}</span>
            <button className="btn btn-sm btn-secondary" onClick={logout}>
              Logout
            </button>
          </>
        ) : (
          <button className="btn btn-sm btn-primary" onClick={() => login()}>
            Demo Login (Operator)
          </button>
        )}
      </nav>
    </header>
  );
}

function AppInner() {
  const { authenticated } = useAuth();
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthLoading, setHealthLoading] = useState(true);
  const [healthError, setHealthError] = useState<string | null>(null);

  useEffect(() => {
    fetchHealth()
      .then((data) => {
        setHealth(data);
        setHealthLoading(false);
      })
      .catch((err: Error) => {
        setHealthError(err.message);
        setHealthLoading(false);
      });
  }, []);

  return (
    <>
      <Header />
      <main className="main">
        {healthLoading ? (
          <div className="status-card">Checking backend…</div>
        ) : healthError ? (
          <div className="status-card error">
            Backend unreachable: {healthError}
          </div>
        ) : (
          <div className="status-card">
            <span className={`dot ${health?.status === "ok" ? "ok" : "warn"}`}></span>
            Backend: {health?.environment} · Demo mode:{" "}
            {health?.demo_mode ? "enabled" : "disabled"}
          </div>
        )}
        <IntentDashboard />
      </main>
    </>
  );
}

function App() {
  return (
    <AuthProvider>
      <AppInner />
    </AuthProvider>
  );
}

export default App;