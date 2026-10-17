/**
 * Tests for the top-level App component.
 *
 * Covers user-visible behaviour: health-check banner, auth-gated dashboard,
 * and demo login flow.
 */
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import userEvent from "@testing-library/user-event";
import App from "../App";
import * as api from "../services/api";

vi.mock("../services/api", async () => {
  const actual = await vi.importActual("../services/api");
  return {
    ...actual,
    fetchHealth: vi.fn(),
    demoLogin: vi.fn(),
    listIntents: vi.fn(),
  };
});

describe("App", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.clearToken();
    vi.mocked(api.fetchHealth).mockResolvedValue({
      status: "ok",
      version: "1.0.0",
      environment: "development",
      demo_mode: true,
    });
    vi.mocked(api.listIntents).mockResolvedValue({
      intents: [],
      compiled: {},
      total: 0,
      page: 1,
      per_page: 20,
      has_next: false,
    });
  });

  afterEach(() => {
    cleanup();
  });

  it("renders the Orbit Forge header", async () => {
    render(<App />);
    expect(screen.getByText("Orbit Forge")).toBeInTheDocument();
  });

  it("shows backend health status after fetch", async () => {
    render(<App />);
    expect(await screen.findByText(/Backend:/, {}, { timeout: 5000 })).toBeInTheDocument();
  });

  it("shows error when backend is unreachable", async () => {
    vi.mocked(api.fetchHealth).mockRejectedValue(new Error("Connection refused"));

    render(<App />);

    expect(await screen.findByText(/Backend unreachable/, {}, { timeout: 5000 })).toBeInTheDocument();
  });

  it("shows login prompt when not authenticated", async () => {
    render(<App />);
    expect(screen.getByText("Demo Login (Operator)")).toBeInTheDocument();
  });

  it("allows demo login via button", async () => {
    vi.mocked(api.demoLogin).mockResolvedValue({
      access_token: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9." +
        btoa(JSON.stringify({ sub: "demo-operator", role: "operator", demo: true, iss: "test", aud: "test" })) +
        ".sig",
      token_type: "bearer",
      expires_in: 28800,
      role: "operator",
    });

    render(<App />);

    const user = userEvent.setup();
    await user.click(screen.getByText("Demo Login (Operator)"));

    await waitFor(() => {
      expect(api.demoLogin).toHaveBeenCalledWith("operator");
    }, { timeout: 5000 });
  });
});