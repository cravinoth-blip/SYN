export type Project = {
  project_id: string;
  project_name: string;
  disease: string;
  geography: string;
  client_name: string;
  subtype_biomarker?: string | null;
  line_of_therapy?: string | null;
  optional_brief?: string | null;
  created_at: string;
  updated_at: string;
};

export type Upload = {
  file_id: string;
  project_id: string;
  filename: string;
  file_type: string;
  storage_uri: string;
  parse_status: string;
  uploaded_at: string;
};

export type Job = {
  job_id: string;
  status: "Queued" | "Running" | "Succeeded" | "Failed";
  message: string;
  candidate_version_id?: string | null;
  version_id?: string | null;
  export_job_id?: string | null;
};

export type Evidence = {
  evidence_id: string;
  source_type: string;
  source_title: string;
  source_date?: string | null;
  geography?: string | null;
  summary: string;
  relevance: string;
  confidence_score: number;
  evidence_strength: string;
  classification: string;
  notes?: string | null;
};

export type Citation = {
  citation_id: string;
  global_reference_number: number;
  section_name: string;
  evidence_id: string;
  formatted_reference: string;
  clickable_link?: string | null;
};

export type WorkspaceSection = {
  section_name: string;
  narrative_markdown: string;
  structured_fields: Record<string, unknown>;
  evidence: Evidence[];
  citations: Citation[];
};

export type VersionSummary = {
  version_id: string;
  parent_version_id?: string | null;
  source_candidate_version_id: string;
  latest_flag: boolean;
  publish_status: string;
  published_at: string;
};

export type Workspace = {
  project: Project;
  latest_version: VersionSummary;
  history: VersionSummary[];
  sections: WorkspaceSection[];
  global_citation_map: Citation[];
  available_regeneration_exclusions: {
    source_categories: string[];
    uploaded_files: Array<{ file_id: string; filename: string; parse_status: string }>;
  };
  export_availability: Record<string, boolean>;
};

function defaultApiBase() {
  if (typeof window !== "undefined" && window.location.port === "3005") {
    return "http://127.0.0.1:8005";
  }
  return "http://127.0.0.1:8005";
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? defaultApiBase();

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      ...(init?.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...init?.headers
    },
    cache: "no-store"
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const payload = await response.json();
      detail = typeof payload.detail === "string" ? payload.detail : JSON.stringify(payload.detail);
    } catch {
      detail = response.statusText;
    }
    throw new Error(detail);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

export const api = {
  createProject(payload: Partial<Project>) {
    return request<Project>("/projects", { method: "POST", body: JSON.stringify(payload) });
  },
  recentProjects() {
    return request<Project[]>("/projects/recent");
  },
  uploads(projectId: string) {
    return request<Upload[]>(`/projects/${projectId}/uploads`);
  },
  upload(projectId: string, file: File) {
    const form = new FormData();
    form.append("file", file);
    return request<Upload>(`/projects/${projectId}/uploads`, { method: "POST", body: form });
  },
  generate(projectId: string) {
    return request<Job>(`/projects/${projectId}/generate`, { method: "POST", body: "{}" });
  },
  workspace(projectId: string) {
    return request<Workspace>(`/projects/${projectId}/workspace`);
  },
  version(projectId: string, versionId: string) {
    return request<Workspace>(`/projects/${projectId}/versions/${versionId}`);
  },
  regenerateFull(projectId: string, payload: Record<string, unknown>) {
    return request<Job>(`/projects/${projectId}/regenerate/full`, {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },
  regenerateSection(projectId: string, payload: Record<string, unknown>) {
    return request<Job>(`/projects/${projectId}/regenerate/section`, {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },
  exportPdf(versionId: string) {
    return request<Job>(`/versions/${versionId}/export/pdf`, { method: "POST" });
  },
  exportPptx(versionId: string) {
    return request<Job>(`/versions/${versionId}/export/pptx`, { method: "POST" });
  }
};
