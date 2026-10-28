import { act, cleanup, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AgentState } from "#/types/agent-state";
import { useGitResumeDrift } from "./use-git-resume-drift";

const services = vi.hoisted(() => ({
  getGitCommits: vi.fn(),
  getGitChanges: vi.fn(),
}));
vi.mock("#/api/git-service/agent-server-git-service.api", () => ({
  default: services,
}));
vi.mock("#/hooks/query/use-active-conversation", () => ({
  useActiveConversation: () => ({
    data: {
      id: "resume-test",
      conversation_url: "http://localhost:8000",
      session_api_key: "test-only",
      workspace: { working_dir: "/workspace/project" },
    },
  }),
}));
const storageKey = "openhands:git-snapshot:resume-test";
const originalHead = "a".repeat(40);
const externalHead = "b".repeat(40);

function storedHead() {
  return JSON.parse(localStorage.getItem(storageKey)!).headSha;
}

async function flushRequests() {
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
}

describe("persisted Git baseline on reopened conversation", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
    localStorage.setItem(
      storageKey,
      JSON.stringify({
        headSha: originalHead,
        changeCount: 0,
        worktreeKey: "/workspace/project",
        capturedAt: 1,
      }),
    );
    services.getGitCommits.mockResolvedValue({
      commits: [{ sha: externalHead }],
    });
    services.getGitChanges.mockResolvedValue([]);
  });
  afterEach(cleanup);

  it("keeps the last completed-turn baseline when an idle conversation is reopened", async () => {
    const { result, rerender } = renderHook(
      ({ state }) => useGitResumeDrift(state),
      { initialProps: { state: AgentState.STOPPED } },
    );
    await flushRequests();
    rerender({ state: AgentState.RUNNING });
    await waitFor(() => expect(result.current.isChecking).toBe(false));
    expect(result.current.drift?.detected).toBe(true);
    expect(result.current.drift?.previousHead).toBe(originalHead);
    expect(result.current.drift?.currentHead).toBe(externalHead);
  });

  it("does not warn when a reopened conversation has an unchanged HEAD", async () => {
    services.getGitCommits.mockResolvedValue({
      commits: [{ sha: originalHead }],
    });
    const { result, rerender } = renderHook(
      ({ state }) => useGitResumeDrift(state),
      { initialProps: { state: AgentState.STOPPED } },
    );
    await flushRequests();
    rerender({ state: AgentState.RUNNING });
    await waitFor(() => expect(result.current.isChecking).toBe(false));
    expect(result.current.drift?.detected).toBe(false);
  });

  it("refreshes the baseline after an observed running turn ends", async () => {
    const { result, rerender } = renderHook(
      ({ state }) => useGitResumeDrift(state),
      { initialProps: { state: AgentState.RUNNING } },
    );
    await waitFor(() => expect(result.current.isChecking).toBe(false));
    expect(result.current.drift?.detected).toBe(true);
    rerender({ state: AgentState.STOPPED });
    await waitFor(() => expect(storedHead()).toBe(externalHead));
  });
});
