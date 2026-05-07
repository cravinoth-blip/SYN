import type { Competitor, Intake, WorkspaceState } from "@competitor-analysis/shared";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8006";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    }
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export type ProjectRecord = {
  projectId: string;
  projectName: string;
  disease: string;
  asset: string;
  geography: string;
  updatedAt: string;
};

export type DiscoveryResponse = {
  suggestions: Array<{
    id: string;
    name: string;
    company: string;
    candidate: string;
    rationale: string;
    confidence: number;
    sourceFamilies: string[];
    evidenceIds: string[];
  }>;
};

export const api = {
  projects: () => request<ProjectRecord[]>("/projects"),
  createProject: (intake: Intake) =>
    request<WorkspaceState>("/projects", { method: "POST", body: JSON.stringify(intake) }),
  workspace: (projectId: string) => request<WorkspaceState>(`/projects/${projectId}/workspace`),
  saveWorkspace: (workspace: WorkspaceState) =>
    request<WorkspaceState>(`/projects/${workspace.projectId}/workspace`, {
      method: "PUT",
      body: JSON.stringify(workspace)
    }),
  loadDemo: (projectId: string) =>
    request<WorkspaceState>(`/projects/${projectId}/demo`, { method: "POST" }),
  discover: (projectId: string) =>
    request<DiscoveryResponse>(`/projects/${projectId}/discovery`, { method: "POST" }),
  addCompetitor: (projectId: string, competitor: Competitor) =>
    request<WorkspaceState>(`/projects/${projectId}/competitors`, {
      method: "POST",
      body: JSON.stringify(competitor)
    }),
  importPipeline: (projectId: string) =>
    request<WorkspaceState>(`/projects/${projectId}/pipeline/import`, { method: "POST" }),
  importTrials: (projectId: string) =>
    request<WorkspaceState>(`/projects/${projectId}/timeline/clinicaltrials`, { method: "POST" }),
  pubmedGraph: (projectId: string) =>
    request<WorkspaceState>(`/projects/${projectId}/knowledge/pubmed`, { method: "POST" }),
  generate: (projectId: string, task: string) =>
    request<{ workspace: WorkspaceState }>(`/projects/${projectId}/generate/${task}`, {
      method: "POST"
    }),
  exportProject: (projectId: string, type: "pdf" | "pptx") =>
    request<{ status: string; message: string }>(`/projects/${projectId}/exports/${type}`, {
      method: "POST"
    })
};
