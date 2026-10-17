/** In-memory auth state management for the Orbit Forge frontend.

Tokens are kept in a React Context + module-level variable — never in
localStorage.  The demo-login flow issues short-lived JWTs from the backend
``/auth/demo-login`` endpoint (localhost-only, production-locked on the
server side).

When Keycloak OIDC is introduced in a future round, this service will be
extended to handle the PKCE redirect flow while preserving the same
in-memory storage contract.
*/

import React, { createContext, useContext, useEffect, useState } from "react";
import type { TokenResponse } from "./api";
import {
  demoLogin as apiDemoLogin,
  clearToken as apiClearToken,
  getToken as apiGetToken,
  setToken as apiSetToken,
} from "./api";

export interface AuthUser {
  subject: string;
  role: string;
  demo: boolean;
}

interface AuthContextValue {
  user: AuthUser | null;
  authenticated: boolean;
  loading: boolean;
  login: (role?: "viewer" | "operator" | "admin") => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
}

function parseToken(token: string | null): AuthUser | null {
  if (!token) return null;
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    return {
      subject: payload.sub,
      role: payload.role,
      demo: payload.demo,
    };
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }): React.ReactElement {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const token = apiGetToken();
    setUser(parseToken(token));
  }, []);

  const login = async (role: "viewer" | "operator" | "admin" = "operator"): Promise<void> => {
    setLoading(true);
    try {
      const resp: TokenResponse = await apiDemoLogin(role);
      setUser(parseToken(resp.access_token));
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      alert(`Login failed: ${message}`);
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    apiClearToken();
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, authenticated: user !== null, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}