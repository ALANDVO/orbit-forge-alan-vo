/**
 * Tests for the IntentDashboard component.
 *
 * Covers user-visible behaviour: empty state, intent listing, selection,
 * and the create-new-intent flow.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, type RenderResult, screen, waitFor, act, fireEvent, cleanup } from "@testing-library/react";
import IntentDashboard from "../components/IntentDashboard";
import * as api from "../services/api";

vi.mock("../services/api", async () => {
  const actual = await vi.importActual("../services/api");
  return {
    ...actual,
    listIntents: vi.fn(),
    createIntent: vi.fn(),
    deleteIntent: vi.fn(),
    fetchArchetypes: vi.fn(),
    compileIntent: vi.fn(),
    getCompiledIntent: vi.fn(),
  };
});

vi.mock("../services/auth", () => ({
  useAuth: () => ({
    user: { subject: "demo-test", role: "operator", demo: true },
    authenticated: true,
    loading: false,
    login: vi.fn(),
    logout: vi.fn(),
  }),
}));

const testIntent = {
  id: "int_test123",
  style_archetype: "cinematic-portrait",
  subject: "A mysterious woman in a leather jacket",
  mood: "dramatic",
  lighting: "three-point-studio",
  composition: "close-up",
  resolution_w: 1024,
  resolution_h: 1024,
  created_at: "2026-10-12T00:00:00Z",
  updated_at: "2026-10-12T00:00:00Z",
};

async function renderAndFlush(ui: React.ReactElement): Promise<RenderResult> {
  let result: RenderResult;
  await act(async () => {
    result = render(ui);
    const { promise, resolve } = Promise.withResolvers<void>();
    setTimeout(resolve, 0);
    await promise;
  });
  return result!;
}

describe("IntentDashboard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.listIntents).mockResolvedValue({
      intents: [],
      compiled: {},
      total: 0,
      page: 1,
      per_page: 20,
      has_next: false,
    });
    vi.mocked(api.fetchArchetypes).mockResolvedValue({
      style_archetypes: ["cinematic-portrait"],
      moods: ["dramatic"],
      lighting: ["three-point-studio"],
      compositions: ["close-up"],
    });
  });

  afterEach(() => {
    cleanup();
  });

  it("shows empty state when no intents exist", async () => {
    await renderAndFlush(<IntentDashboard />);
    expect(await screen.findByText("No intents yet", {}, { timeout: 5000 })).toBeInTheDocument();
    expect(screen.getByText("Create Intent")).toBeInTheDocument();
  });

  it("shows loading state on initial render", () => {
    render(<IntentDashboard />);
    expect(screen.getByText("Loading intents…")).toBeInTheDocument();
  });

  it("lists created intents", async () => {
    vi.mocked(api.listIntents).mockResolvedValue({
      intents: [testIntent],
      compiled: {},
      total: 1,
      page: 1,
      per_page: 20,
      has_next: false,
    });

    await renderAndFlush(<IntentDashboard />);

    expect(await screen.findByText("A mysterious woman in a leather jacket", {}, { timeout: 5000 })).toBeInTheDocument();
    expect(screen.getByText("cinematic-portrait")).toBeInTheDocument();
  });

  it("allows creating an intent via the form", async () => {
    vi.mocked(api.createIntent).mockResolvedValue(testIntent);

    await renderAndFlush(<IntentDashboard />);

    // Wait for EmptyState, then click "Create Intent" to open the form.
    await screen.findByText("No intents yet", {}, { timeout: 5000 });
    const btn = screen.queryByText("Create Intent");
    expect(btn).not.toBeNull();
    await act(async () => {
      fireEvent.click(btn!);
    });

    // Form should now be visible.
    const input = await screen.findByPlaceholderText(
      /e.g. A woman/, {}, { timeout: 5000 },
    );

    // Fill in the subject and submit.
    await act(async () => {
      fireEvent.change(input, {
        target: { value: "A mysterious woman in a leather jacket" },
      });
      fireEvent.click(screen.getByRole("button", { name: "Create Intent" }));
    });

    await waitFor(() => {
      expect(api.createIntent).toHaveBeenCalled();
    }, { timeout: 5000 });
  });
});