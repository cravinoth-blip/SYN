"use client";

import { ChangeEvent, useEffect, useMemo, useState } from "react";
import {
  BookOpen,
  Clock,
  Download,
  FilePlus,
  History,
  Loader2,
  RefreshCw,
  Send,
  UploadCloud
} from "lucide-react";
import { SECTION_NAMES } from "@stratergic/shared";
import { api, Job, Project, Upload, Workspace, WorkspaceSection } from "@/lib/api";

type Intake = {
  project_name: string;
  disease: string;
  subtype_biomarker: string;
  line_of_therapy: string;
  geography: string;
  client_name: string;
  optional_brief: string;
};

type Drawer = "history" | "references" | "regenerate" | null;
type StatusTone = "neutral" | "error";

const REQUIRED_INTAKE_FIELDS: Array<{
  key: keyof Pick<Intake, "project_name" | "disease" | "geography" | "client_name">;
  label: string;
  reason: string;
}> = [
  {
    key: "project_name",
    label: "Project name",
    reason: "needed to save and reopen the workspace"
  },
  {
    key: "disease",
    label: "Disease",
    reason: "needed to build the evidence retrieval plan"
  },
  {
    key: "geography",
    label: "Geography",
    reason: "needed to scope sources and market context"
  },
  {
    key: "client_name",
    label: "Client or account",
    reason: "needed to tailor the company, customer, and channel analysis"
  }
];

const defaultIntake: Intake = {
  project_name: "EGFRex20 NSCLC US+EU5 landscape",
  disease: "Metastatic NSCLC",
  subtype_biomarker: "EGFR exon 20 insertion",
  line_of_therapy: "2L+",
  geography: "US + EU5",
  client_name: "Pilot account",
  optional_brief:
    "Focus on competitor timing, cross-market access divergence, and stakeholder implications."
};

export default function Home() {
  const [intake, setIntake] = useState<Intake>(defaultIntake);
  const [project, setProject] = useState<Project | null>(null);
  const [recent, setRecent] = useState<Project[]>([]);
  const [uploads, setUploads] = useState<Upload[]>([]);
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [drawer, setDrawer] = useState<Drawer>(null);
  const [regenSection, setRegenSection] = useState<string | null>(null);
  const [changeInstruction, setChangeInstruction] = useState(
    "Tighten the competitive white-space narrative and emphasize only material evidence shifts."
  );
  const [excludedSources, setExcludedSources] = useState<string[]>([]);
  const [excludedFiles, setExcludedFiles] = useState<string[]>([]);
  const [status, setStatus] = useState("Ready");
  const [statusTone, setStatusTone] = useState<StatusTone>("neutral");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.recentProjects().then(setRecent).catch(() => setRecent([]));
  }, []);

  const canGenerate = useMemo(() => {
    return missingRequiredIntakeFields(intake).length === 0;
  }, [intake]);

  function updateIntake(key: keyof Intake, value: string) {
    setIntake((current) => ({ ...current, [key]: value }));
    setStatusTone("neutral");
  }

  async function ensureProject() {
    if (project) {
      return project;
    }
    const created = await api.createProject(intake);
    setProject(created);
    setRecent((current) => [created, ...current.filter((item) => item.project_id !== created.project_id)]);
    return created;
  }

  async function createProjectOnly() {
    setBusy(true);
    setStatusTone("neutral");
    setStatus("Creating project");
    try {
      const created = await ensureProject();
      setStatus(`Project ready: ${created.project_name}`);
    } catch (error) {
      setStatusTone("error");
      setStatus(error instanceof Error ? error.message : "Project creation failed");
    } finally {
      setBusy(false);
    }
  }

  async function uploadFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setBusy(true);
    setStatusTone("neutral");
    setStatus("Uploading and parsing file");
    try {
      const target = await ensureProject();
      await api.upload(target.project_id, file);
      setUploads(await api.uploads(target.project_id));
      setStatus("Upload parsed and attached");
    } catch (error) {
      setStatusTone("error");
      setStatus(error instanceof Error ? error.message : "Upload failed");
    } finally {
      setBusy(false);
      event.target.value = "";
    }
  }

  async function generate() {
    if (!canGenerate) {
      setStatusTone("error");
      setStatus(buildGenerationBlockedMessage(intake));
      return;
    }
    setBusy(true);
    setStatusTone("neutral");
    setStatus("Generating, validating, and publishing latest version");
    try {
      const target = await ensureProject();
      const job = await api.generate(target.project_id);
      await afterJob(target, job);
    } catch (error) {
      setStatusTone("error");
      setStatus(error instanceof Error ? error.message : "Generation failed");
    } finally {
      setBusy(false);
    }
  }

  async function afterJob(target: Project, job: Job) {
    if (job.status !== "Succeeded") {
      setStatusTone("error");
      setStatus(job.message);
      return;
    }
    const nextWorkspace = await api.workspace(target.project_id);
    setWorkspace(nextWorkspace);
    setUploads(await api.uploads(target.project_id));
    setStatusTone("neutral");
    setStatus(job.message);
  }

  async function openProject(target: Project) {
    setProject(target);
    setBusy(true);
    setStatusTone("neutral");
    setStatus("Opening latest published version");
    try {
      setUploads(await api.uploads(target.project_id));
      setWorkspace(await api.workspace(target.project_id));
      setStatus("Latest version loaded");
    } catch (error) {
      setWorkspace(null);
      setStatusTone("error");
      setStatus(error instanceof Error ? error.message : "No published version yet");
    } finally {
      setBusy(false);
    }
  }

  function openRegen(section?: string) {
    setRegenSection(section ?? null);
    setDrawer("regenerate");
  }

  async function regenerate() {
    if (!workspace || !project) return;
    setBusy(true);
    setStatusTone("neutral");
    setStatus("Regenerating selected scope");
    try {
      const payload = {
        parent_version_id: workspace.latest_version.version_id,
        section_name: regenSection ?? undefined,
        change_instruction: changeInstruction,
        excluded_source_categories: excludedSources,
        excluded_document_ids: excludedFiles
      };
      const job = regenSection
        ? await api.regenerateSection(project.project_id, payload)
        : await api.regenerateFull(project.project_id, payload);
      await afterJob(project, job);
      setDrawer(null);
    } catch (error) {
      setStatusTone("error");
      setStatus(error instanceof Error ? error.message : "Regeneration failed");
    } finally {
      setBusy(false);
    }
  }

  async function exportVersion(type: "pdf" | "pptx") {
    if (!workspace) return;
    setBusy(true);
    setStatusTone("neutral");
    setStatus(`Exporting ${type.toUpperCase()}`);
    try {
      const job =
        type === "pdf"
          ? await api.exportPdf(workspace.latest_version.version_id)
          : await api.exportPptx(workspace.latest_version.version_id);
      setStatus(job.message);
    } catch (error) {
      setStatusTone("error");
      setStatus(error instanceof Error ? error.message : "Export failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="app">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark" />
          <span>7Cs Disease Intelligence</span>
        </div>
        <div className="pill-row">
          <span className="pill">Portable Docker</span>
          <span className="pill">OpenAI routed</span>
        </div>
      </header>

      <div className="page">
        {!workspace ? (
          <section className="landing-grid">
            <div className="panel">
              <div className="panel-header">
                <div>
                  <h1>Generate a full 7Cs analysis</h1>
                  <p className="muted">Structured disease scope with evidence-backed output.</p>
                </div>
              </div>

              <div className="form-grid">
                <label>
                  Project name
                  <input
                    value={intake.project_name}
                    onChange={(event) => updateIntake("project_name", event.target.value)}
                  />
                </label>
                <label>
                  Disease
                  <input
                    value={intake.disease}
                    onChange={(event) => updateIntake("disease", event.target.value)}
                  />
                </label>
                <label>
                  Subtype or biomarker
                  <input
                    value={intake.subtype_biomarker}
                    onChange={(event) => updateIntake("subtype_biomarker", event.target.value)}
                  />
                </label>
                <label>
                  Line of therapy
                  <input
                    value={intake.line_of_therapy}
                    onChange={(event) => updateIntake("line_of_therapy", event.target.value)}
                  />
                </label>
                <label>
                  Geography
                  <input
                    value={intake.geography}
                    onChange={(event) => updateIntake("geography", event.target.value)}
                  />
                </label>
                <label>
                  Client or account
                  <input
                    value={intake.client_name}
                    onChange={(event) => updateIntake("client_name", event.target.value)}
                  />
                </label>
                <label className="span-2">
                  Optional brief
                  <textarea
                    value={intake.optional_brief}
                    onChange={(event) => updateIntake("optional_brief", event.target.value)}
                  />
                </label>
              </div>

              <div className="actions">
                <button className="secondary" onClick={createProjectOnly} disabled={busy || !canGenerate}>
                  <FilePlus size={18} /> Create project
                </button>
                <button className="primary" onClick={generate} disabled={busy}>
                  {busy ? <Loader2 size={18} /> : <Send size={18} />} Generate 7Cs
                </button>
              </div>
              <p className={`status ${statusTone === "error" ? "status-error" : ""}`}>{status}</p>
            </div>

            <aside className="stack">
              <div className="panel">
                <div className="panel-header">
                  <h2>Upload supporting files</h2>
                  <UploadCloud size={20} />
                </div>
                <label>
                  PDF or PPTX
                  <input type="file" accept=".pdf,.pptx" onChange={uploadFile} disabled={busy} />
                </label>
                <div className="stack" style={{ marginTop: 14 }}>
                  {uploads.length === 0 ? (
                    <div className="empty">No files attached.</div>
                  ) : (
                    uploads.map((file) => (
                      <div className="upload-item" key={file.file_id}>
                        <strong>{file.filename}</strong>
                        <div className="muted">{file.parse_status}</div>
                      </div>
                    ))
                  )}
                </div>
              </div>

              <div className="panel">
                <div className="panel-header">
                  <h2>Recent projects</h2>
                  <Clock size={20} />
                </div>
                <div className="stack">
                  {recent.length === 0 ? (
                    <div className="empty">No recent projects.</div>
                  ) : (
                    recent.map((item) => (
                      <div className="recent-item" key={item.project_id}>
                        <div>
                          <strong>{item.project_name}</strong>
                          <div className="muted">{item.disease}</div>
                        </div>
                        <button className="secondary" onClick={() => openProject(item)}>
                          Open
                        </button>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </aside>
          </section>
        ) : (
          <WorkspaceView
            workspace={workspace}
            busy={busy}
            status={status}
            statusTone={statusTone}
            onBack={() => setWorkspace(null)}
            onOpenHistory={() => setDrawer("history")}
            onOpenReferences={() => setDrawer("references")}
            onRegenerate={() => openRegen()}
            onRegenerateSection={openRegen}
            onExport={exportVersion}
          />
        )}
      </div>

      {drawer && workspace ? (
        <DrawerView
          drawer={drawer}
          workspace={workspace}
          regenSection={regenSection}
          changeInstruction={changeInstruction}
          setChangeInstruction={setChangeInstruction}
          excludedSources={excludedSources}
          setExcludedSources={setExcludedSources}
          excludedFiles={excludedFiles}
          setExcludedFiles={setExcludedFiles}
          busy={busy}
          onClose={() => setDrawer(null)}
          onRegenerate={regenerate}
          onOpenVersion={async (versionId) => {
            if (!project) return;
            setWorkspace(await api.version(project.project_id, versionId));
            setDrawer(null);
          }}
        />
      ) : null}
    </main>
  );
}

function WorkspaceView({
  workspace,
  busy,
  status,
  statusTone,
  onBack,
  onOpenHistory,
  onOpenReferences,
  onRegenerate,
  onRegenerateSection,
  onExport
}: {
  workspace: Workspace;
  busy: boolean;
  status: string;
  statusTone: StatusTone;
  onBack: () => void;
  onOpenHistory: () => void;
  onOpenReferences: () => void;
  onRegenerate: () => void;
  onRegenerateSection: (section: string) => void;
  onExport: (type: "pdf" | "pptx") => void;
}) {
  const sectionMap = new Map(workspace.sections.map((section) => [section.section_name, section]));
  return (
    <section className="workspace-grid">
      <div className="panel workspace-header">
        <div>
          <div className="pill-row">
            <span className="pill">Latest version</span>
            <span className="pill">{workspace.latest_version.version_id.slice(0, 8)}</span>
            <span className="pill">{workspace.project.geography}</span>
          </div>
          <h1>{workspace.project.project_name}</h1>
          <p className="muted">
            {workspace.project.disease} | {workspace.project.subtype_biomarker} |{" "}
            {workspace.project.line_of_therapy}
          </p>
        </div>
        <div className="workspace-actions">
          <button className="ghost" onClick={onBack}>
            Back
          </button>
          <button className="secondary" onClick={onOpenHistory}>
            <History size={18} /> History
          </button>
          <button className="secondary" onClick={onOpenReferences}>
            <BookOpen size={18} /> References
          </button>
          <button className="secondary" onClick={onRegenerate} disabled={busy}>
            <RefreshCw size={18} /> Regenerate
          </button>
          <button className="primary" onClick={() => onExport("pdf")} disabled={busy}>
            <Download size={18} /> PDF
          </button>
          <button className="primary" onClick={() => onExport("pptx")} disabled={busy}>
            <Download size={18} /> PPTX
          </button>
        </div>
        <p className={`status ${statusTone === "error" ? "status-error" : ""}`}>{status}</p>
      </div>

      {SECTION_NAMES.map((sectionName) => {
        const section = sectionMap.get(sectionName);
        return section ? (
          <SectionPanel
            key={sectionName}
            section={section}
            onRegenerate={() => onRegenerateSection(sectionName)}
          />
        ) : null;
      })}
    </section>
  );
}

function missingRequiredIntakeFields(intake: Intake) {
  return REQUIRED_INTAKE_FIELDS.filter((field) => !intake[field.key].trim());
}

function buildGenerationBlockedMessage(intake: Intake) {
  const missing = missingRequiredIntakeFields(intake);
  if (missing.length === 0) {
    return "Generation is blocked until the intake is ready.";
  }
  const reasons = missing.map((field) => `${field.label} is ${field.reason}`);
  return `Generation blocked: ${reasons.join("; ")}.`;
}

function SectionPanel({
  section,
  onRegenerate
}: {
  section: WorkspaceSection;
  onRegenerate: () => void;
}) {
  return (
    <article className="section">
      <div className="section-head">
        <h2>{section.section_name}</h2>
        <button className="secondary" onClick={onRegenerate}>
          <RefreshCw size={16} /> Regenerate this C
        </button>
      </div>
      <div className="section-body">
        <div className="section-columns">
          <div className="narrative">{section.narrative_markdown}</div>
          <div className="evidence-list">
            {section.evidence.map((item) => (
              <div className="evidence-row" key={item.evidence_id}>
                <div className="evidence-title">{item.source_title}</div>
                <div className="muted">
                  {item.source_type} | {item.evidence_strength} | {item.confidence_score}
                </div>
                <p>{item.summary}</p>
                <div className="pill-row">
                  <span className="pill">{item.classification}</span>
                  {item.geography ? <span className="pill">{item.geography}</span> : null}
                </div>
              </div>
            ))}
          </div>
        </div>
        <div className="panel">
          <h3>References</h3>
          <ol>
            {section.citations.map((citation) => (
              <li key={citation.citation_id}>
                [{citation.global_reference_number}] {citation.formatted_reference}{" "}
                {citation.clickable_link ? <a href={citation.clickable_link}>Open</a> : null}
              </li>
            ))}
          </ol>
        </div>
      </div>
    </article>
  );
}

function DrawerView({
  drawer,
  workspace,
  regenSection,
  changeInstruction,
  setChangeInstruction,
  excludedSources,
  setExcludedSources,
  excludedFiles,
  setExcludedFiles,
  busy,
  onClose,
  onRegenerate,
  onOpenVersion
}: {
  drawer: Drawer;
  workspace: Workspace;
  regenSection: string | null;
  changeInstruction: string;
  setChangeInstruction: (value: string) => void;
  excludedSources: string[];
  setExcludedSources: (value: string[]) => void;
  excludedFiles: string[];
  setExcludedFiles: (value: string[]) => void;
  busy: boolean;
  onClose: () => void;
  onRegenerate: () => void;
  onOpenVersion: (versionId: string) => void;
}) {
  function toggle(list: string[], value: string) {
    return list.includes(value) ? list.filter((item) => item !== value) : [...list, value];
  }

  return (
    <>
      <div className="drawer-backdrop" onClick={onClose} />
      <aside className="drawer">
        {drawer === "history" ? (
          <>
            <h2>Version history</h2>
            <div className="stack">
              {workspace.history.map((version) => (
                <div className="recent-item" key={version.version_id}>
                  <div>
                    <strong>{version.latest_flag ? "Latest" : "Published"}</strong>
                    <div className="muted">{new Date(version.published_at).toLocaleString()}</div>
                  </div>
                  <button className="secondary" onClick={() => onOpenVersion(version.version_id)}>
                    Open
                  </button>
                </div>
              ))}
            </div>
          </>
        ) : null}

        {drawer === "references" ? (
          <>
            <h2>Reference model</h2>
            <div className="stack">
              {workspace.global_citation_map.map((citation) => (
                <div className="evidence-row" key={citation.citation_id}>
                  <strong>[{citation.global_reference_number}]</strong> {citation.formatted_reference}
                  <div className="muted">{citation.section_name}</div>
                </div>
              ))}
            </div>
          </>
        ) : null}

        {drawer === "regenerate" ? (
          <>
            <h2>{regenSection ? `Regenerate ${regenSection}` : "Regenerate full report"}</h2>
            <label>
              Change instruction
              <textarea
                value={changeInstruction}
                onChange={(event) => setChangeInstruction(event.target.value)}
              />
            </label>
            <div className="checks">
              <h3>Exclude source categories</h3>
              {workspace.available_regeneration_exclusions.source_categories.map((source) => (
                <label className="check" key={source}>
                  <input
                    type="checkbox"
                    checked={excludedSources.includes(source)}
                    onChange={() => setExcludedSources(toggle(excludedSources, source))}
                  />
                  {source}
                </label>
              ))}
            </div>
            <div className="checks">
              <h3>Exclude uploaded files</h3>
              {workspace.available_regeneration_exclusions.uploaded_files.length === 0 ? (
                <div className="empty">No uploaded files.</div>
              ) : (
                workspace.available_regeneration_exclusions.uploaded_files.map((file) => (
                  <label className="check" key={file.file_id}>
                    <input
                      type="checkbox"
                      checked={excludedFiles.includes(file.file_id)}
                      onChange={() => setExcludedFiles(toggle(excludedFiles, file.file_id))}
                    />
                    {file.filename}
                  </label>
                ))
              )}
            </div>
            <button className="primary" onClick={onRegenerate} disabled={busy || !changeInstruction}>
              <RefreshCw size={18} /> Create new version
            </button>
          </>
        ) : null}
        <button className="secondary" onClick={onClose}>
          Close
        </button>
      </aside>
    </>
  );
}
