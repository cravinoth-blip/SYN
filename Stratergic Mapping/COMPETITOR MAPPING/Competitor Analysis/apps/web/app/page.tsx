"use client";

import { MouseEvent, useEffect, useMemo, useRef, useState } from "react";
import {
  BarChart3,
  BookOpen,
  Brain,
  Check,
  Download,
  FileJson,
  FlaskConical,
  Loader2,
  Plus,
  RefreshCw,
  Save,
  Search,
  Sparkles,
  Trash2
} from "lucide-react";
import type {
  Competitor,
  EvidenceItem,
  Intake,
  PipelineAsset,
  TabKey,
  TimelineTrial,
  WorkspaceState
} from "@competitor-analysis/shared";
import { SOURCE_FAMILIES, TABS } from "@competitor-analysis/shared";
import { api, DiscoveryResponse, ProjectRecord } from "@/lib/api";

const colors = ["#01696f", "#964219", "#a12c7b", "#006494", "#7a39bb", "#437a22"];

const blankIntake: Intake = {
  projectName: "",
  disease: "",
  asset: "",
  mechanism: "",
  geography: "",
  timeHorizon: "",
  knownCompetitors: "",
  objective: ""
};

function makeCompetitor(partial: Partial<Competitor> = {}): Competitor {
  return {
    id: `cmp_${crypto.randomUUID().slice(0, 8)}`,
    name: partial.name ?? "New competitor",
    company: partial.company ?? "",
    color: partial.color ?? colors[Math.floor(Math.random() * colors.length)],
    x: partial.x ?? 0,
    y: partial.y ?? 0,
    isAsset: partial.isAsset ?? false,
    rationale: partial.rationale ?? "",
    sourceCount: partial.sourceCount ?? 0
  };
}

export default function Home() {
  const [projects, setProjects] = useState<ProjectRecord[]>([]);
  const [workspace, setWorkspace] = useState<WorkspaceState | null>(null);
  const [intake, setIntake] = useState<Intake>(blankIntake);
  const [activeTab, setActiveTab] = useState<TabKey>("map");
  const [suggestions, setSuggestions] = useState<DiscoveryResponse["suggestions"]>([]);
  const [selectedSuggestions, setSelectedSuggestions] = useState<string[]>([]);
  const [nodeDetail, setNodeDetail] = useState<string | null>(null);
  const [savedOpen, setSavedOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("Blank workspace ready");
  const [error, setError] = useState(false);

  useEffect(() => {
    api.projects().then(setProjects).catch(() => setProjects([]));
  }, []);

  const sourceCounts = useMemo(() => {
    const counts = new Map<string, number>();
    workspace?.evidence.forEach((item) => {
      counts.set(item.sourceFamily, (counts.get(item.sourceFamily) ?? 0) + 1);
    });
    return counts;
  }, [workspace]);

  async function run<T>(label: string, fn: () => Promise<T>, after?: (value: T) => void) {
    setBusy(true);
    setError(false);
    setStatus(label);
    try {
      const value = await fn();
      after?.(value);
      setStatus("Done");
    } catch (err) {
      setError(true);
      setStatus(err instanceof Error ? err.message : "Action failed");
    } finally {
      setBusy(false);
    }
  }

  async function createProject() {
    await run("Creating project", () => api.createProject(intake), (created) => {
      setWorkspace(created);
      setProjects((current) => [
        {
          projectId: created.projectId,
          projectName: created.intake.projectName || "Untitled competitor analysis",
          disease: created.intake.disease,
          asset: created.intake.asset,
          geography: created.intake.geography,
          updatedAt: new Date().toISOString()
        },
        ...current
      ]);
    });
  }

  async function saveWorkspace(next = workspace) {
    if (!next) return;
    await run("Saving workspace", () => api.saveWorkspace(next), setWorkspace);
  }

  function updateWorkspace(mutator: (current: WorkspaceState) => WorkspaceState) {
    setWorkspace((current) => (current ? mutator(structuredClone(current)) : current));
  }

  function addManualCompetitor() {
    updateWorkspace((current) => {
      current.map.competitors.push(
        makeCompetitor({
          name: "New competitor",
          company: "Company",
          color: colors[current.map.competitors.length % colors.length],
          x: 0,
          y: 0
        })
      );
      return current;
    });
  }

  async function approveSuggestions(ids: string[]) {
    if (!workspace) return;
    const approved = suggestions.filter((item) => ids.includes(item.id));
    let next = workspace;
    for (const suggestion of approved) {
      const competitor = makeCompetitor({
        name: suggestion.candidate,
        company: suggestion.company,
        rationale: suggestion.rationale,
        sourceCount: suggestion.sourceFamilies.length,
        x: Math.round((suggestion.confidence - 0.5) * 160),
        y: 35
      });
      next = await api.addCompetitor(next.projectId, competitor);
    }
    setWorkspace(next);
    setSuggestions((current) => current.filter((item) => !ids.includes(item.id)));
    setSelectedSuggestions([]);
    setStatus(`${approved.length} suggestion${approved.length === 1 ? "" : "s"} approved`);
  }

  const canCreate = intake.projectName && intake.disease && intake.asset && intake.objective;

  return (
    <main className="app">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark"><BarChart3 size={18} /></span>
          <span>Competitor Analysis</span>
        </div>
        <div className="header-actions">
          <button className="btn ghost" onClick={() => setSavedOpen(true)}>
            Saved Workspaces
          </button>
          {workspace ? (
            <button className="btn" onClick={() => saveWorkspace()} disabled={busy}>
              <Save size={16} /> Save
            </button>
          ) : null}
        </div>
      </header>

      {workspace ? (
        <nav className="tabs" aria-label="Workspace tabs">
          {TABS.map((tab) => (
            <button
              className={`tab ${activeTab === tab ? "active" : ""}`}
              key={tab}
              onClick={() => setActiveTab(tab)}
            >
              {tabLabel(tab)}
            </button>
          ))}
        </nav>
      ) : null}

      <div className="page">
        {!workspace ? (
          <StartScreen
            intake={intake}
            setIntake={setIntake}
            busy={busy}
            canCreate={Boolean(canCreate)}
            createProject={createProject}
          />
        ) : (
          <section className="stack">
            <WorkspaceHeader
              workspace={workspace}
              busy={busy}
              status={status}
              error={error}
              sourceCounts={sourceCounts}
              onBlank={() => {
                setWorkspace(null);
                setSuggestions([]);
                setActiveTab("map");
              }}
              onDemo={() => run("Loading sample demo data", () => api.loadDemo(workspace.projectId), setWorkspace)}
              onDiscover={() =>
                run("Running validated-source discovery", () => api.discover(workspace.projectId), (data) => {
                  setSuggestions(data.suggestions);
                  setStatus(`${data.suggestions.length} suggestions ready for review`);
                })
              }
              onGenerate={() =>
                run("Running four-pass strategic analysis", () => api.generate(workspace.projectId, "full_workspace"), (data) =>
                  setWorkspace(data.workspace)
                )
              }
            />

            {suggestions.length ? (
              <Suggestions
                suggestions={suggestions}
                selected={selectedSuggestions}
                setSelected={setSelectedSuggestions}
                approve={approveSuggestions}
              />
            ) : null}

            {activeTab === "map" ? (
              <MapTab workspace={workspace} updateWorkspace={updateWorkspace} addManualCompetitor={addManualCompetitor} />
            ) : null}
            {activeTab === "pipeline" ? (
              <PipelineTab
                workspace={workspace}
                updateWorkspace={updateWorkspace}
                importPipeline={() =>
                  run("Building pipeline rows from mapped competitors", () => api.importPipeline(workspace.projectId), setWorkspace)
                }
              />
            ) : null}
            {activeTab === "timeline" ? (
              <TimelineTab
                workspace={workspace}
                importTrials={() =>
                  run("Importing ClinicalTrials.gov records", () => api.importTrials(workspace.projectId), setWorkspace)
                }
              />
            ) : null}
            {activeTab === "knowledge" ? (
              <KnowledgeTab
                workspace={workspace}
                nodeDetail={nodeDetail}
                setNodeDetail={setNodeDetail}
                buildGraph={() =>
                  run("Building PubMed knowledge graph", () => api.pubmedGraph(workspace.projectId), setWorkspace)
                }
              />
            ) : null}
            {activeTab === "evidence" ? <EvidenceTab workspace={workspace} updateWorkspace={updateWorkspace} /> : null}
            {activeTab === "exports" ? (
              <ExportsTab
                workspace={workspace}
                exportProject={(type) =>
                  run(`Creating ${type.toUpperCase()} export`, () => api.exportProject(workspace.projectId, type), (data) =>
                    setStatus(data.message)
                  )
                }
              />
            ) : null}
          </section>
        )}
      </div>
      {savedOpen ? (
        <SavedWorkspacesModal
          projects={projects}
          busy={busy}
          onClose={() => setSavedOpen(false)}
          openProject={(project) =>
            run("Opening project", () => api.workspace(project.projectId), (opened) => {
              setWorkspace(opened);
              setSavedOpen(false);
            })
          }
        />
      ) : null}
    </main>
  );
}

function StartScreen({
  intake,
  setIntake,
  busy,
  canCreate,
  createProject
}: {
  intake: Intake;
  setIntake: (value: Intake) => void;
  busy: boolean;
  canCreate: boolean;
  createProject: () => void;
}) {
  return (
    <section className="start-layout">
      <div className="panel stack">
        <div>
          <h1 className="title">Create competitor workspace</h1>
          <p className="subtle">Start blank, then explicitly run discovery when you are ready.</p>
        </div>
        <div className="grid-2">
          <Field label="Project name" value={intake.projectName} onChange={(v) => setIntake({ ...intake, projectName: v })} />
          <Field label="Disease / indication" value={intake.disease} onChange={(v) => setIntake({ ...intake, disease: v })} />
          <Field label="Asset or compound" value={intake.asset} onChange={(v) => setIntake({ ...intake, asset: v })} />
          <Field label="Mechanism / modality" value={intake.mechanism} onChange={(v) => setIntake({ ...intake, mechanism: v })} />
          <Field label="Custom geography / market" value={intake.geography} onChange={(v) => setIntake({ ...intake, geography: v })} />
          <Field label="Time horizon" value={intake.timeHorizon} onChange={(v) => setIntake({ ...intake, timeHorizon: v })} />
        </div>
        <Field area label="Known competitors (optional)" value={intake.knownCompetitors} onChange={(v) => setIntake({ ...intake, knownCompetitors: v })} />
        <Field area label="Strategic question / objective" value={intake.objective} onChange={(v) => setIntake({ ...intake, objective: v })} />
        <div className="actions">
          <button className="btn primary" onClick={createProject} disabled={busy || !canCreate}>
            {busy ? <Loader2 size={16} /> : <Plus size={16} />} Create blank project
          </button>
        </div>
      </div>
    </section>
  );
}

function SavedWorkspacesModal({
  projects,
  busy,
  onClose,
  openProject
}: {
  projects: ProjectRecord[];
  busy: boolean;
  onClose: () => void;
  openProject: (project: ProjectRecord) => void;
}) {
  return (
    <>
      <div className="modal-backdrop" onClick={onClose} />
      <section className="modal" role="dialog" aria-modal="true" aria-labelledby="saved-workspaces-title">
        <div className="modal-head">
          <div>
            <h2 id="saved-workspaces-title">Saved Workspaces</h2>
            <p className="subtle">Open an existing competitor analysis workspace.</p>
          </div>
          <button className="btn ghost" onClick={onClose}>
            Close
          </button>
        </div>
        <div className="stack">
          {projects.length ? (
            projects.map((project) => (
              <div className="saved-workspace-row" key={project.projectId}>
                <div>
                  <strong>{project.projectName}</strong>
                  <p className="subtle">
                    {project.disease || "Disease not set"} - {project.asset || "Asset not set"} -{" "}
                    {project.geography || "Market not set"}
                  </p>
                </div>
                <button className="btn primary" disabled={busy} onClick={() => openProject(project)}>
                  Open
                </button>
              </div>
            ))
          ) : (
            <div className="empty">No saved projects yet.</div>
          )}
        </div>
      </section>
    </>
  );
}

function WorkspaceHeader({
  workspace,
  busy,
  status,
  error,
  sourceCounts,
  onBlank,
  onDemo,
  onDiscover,
  onGenerate
}: {
  workspace: WorkspaceState;
  busy: boolean;
  status: string;
  error: boolean;
  sourceCounts: Map<string, number>;
  onBlank: () => void;
  onDemo: () => void;
  onDiscover: () => void;
  onGenerate: () => void;
}) {
  return (
    <div className="panel stack">
      <div className="row-actions" style={{ justifyContent: "space-between" }}>
        <div>
          <h1 className="title">{workspace.intake.projectName || "Untitled competitor analysis"}</h1>
          <p className="subtle">
            {workspace.intake.disease || "Disease not set"} - {workspace.intake.asset || "Asset not set"} - {workspace.intake.geography || "Market not set"}
          </p>
        </div>
        <div className="actions">
          <button className="btn ghost" onClick={onBlank}>Close</button>
          <button className="btn" onClick={onDemo} disabled={busy}><Sparkles size={16} /> Load demo</button>
          <button className="btn" onClick={onDiscover} disabled={busy}><Search size={16} /> Run discovery</button>
          <button className="btn primary" onClick={onGenerate} disabled={busy}><Brain size={16} /> Run 4-pass AI</button>
        </div>
      </div>
      <div className="row-actions">
        {SOURCE_FAMILIES.map((source) => (
          <span className="pill" key={source}>{source}: {sourceCounts.get(source) ?? 0}</span>
        ))}
      </div>
      <div className={`status ${error ? "error" : ""}`}>{busy ? "Working..." : status}</div>
    </div>
  );
}

function Suggestions({
  suggestions,
  selected,
  setSelected,
  approve
}: {
  suggestions: DiscoveryResponse["suggestions"];
  selected: string[];
  setSelected: (value: string[]) => void;
  approve: (ids: string[]) => void;
}) {
  return (
    <div className="panel stack">
      <div className="row-actions" style={{ justifyContent: "space-between" }}>
        <h2 className="section-title">Discovery suggestions</h2>
        <button className="btn primary" disabled={!selected.length} onClick={() => approve(selected)}>
          <Check size={16} /> Approve selected
        </button>
      </div>
      <div className="grid-2">
        {suggestions.map((suggestion) => (
          <div className="suggestion stack" key={suggestion.id}>
            <label className="inline">
              <input
                type="checkbox"
                checked={selected.includes(suggestion.id)}
                onChange={() =>
                  setSelected(
                    selected.includes(suggestion.id)
                      ? selected.filter((id) => id !== suggestion.id)
                      : [...selected, suggestion.id]
                  )
                }
              />
              <strong>{suggestion.candidate}</strong>
            </label>
            <p className="subtle">{suggestion.company} - confidence {Math.round(suggestion.confidence * 100)}%</p>
            <p>{suggestion.rationale}</p>
            <div className="row-actions">
              {suggestion.sourceFamilies.map((source) => <span className="pill" key={source}>{source}</span>)}
            </div>
            <button className="btn" onClick={() => approve([suggestion.id])}>Approve this competitor</button>
          </div>
        ))}
      </div>
    </div>
  );
}

function MapTab({
  workspace,
  updateWorkspace,
  addManualCompetitor
}: {
  workspace: WorkspaceState;
  updateWorkspace: (mutator: (current: WorkspaceState) => WorkspaceState) => void;
  addManualCompetitor: () => void;
}) {
  const asset = workspace.map.competitors.find((item) => item.isAsset);
  const highThreat = workspace.map.competitors.filter((item) => !item.isAsset && (Math.abs(item.x) > 50 || Math.abs(item.y) > 50)).length;
  return (
    <div className="workspace">
      <aside className="panel stack">
        <h2 className="section-title">Map setup</h2>
        <Field label="Title" value={workspace.map.title} onChange={(v) => updateWorkspace((c) => ({ ...c, map: { ...c.map, title: v } }))} />
        <Field label="Subtitle" value={workspace.map.subtitle} onChange={(v) => updateWorkspace((c) => ({ ...c, map: { ...c.map, subtitle: v } }))} />
        <Field label="X axis" value={workspace.map.xAxis} onChange={(v) => updateWorkspace((c) => ({ ...c, map: { ...c.map, xAxis: v } }))} />
        <Field label="Y axis" value={workspace.map.yAxis} onChange={(v) => updateWorkspace((c) => ({ ...c, map: { ...c.map, yAxis: v } }))} />
        <Field label="Framing question" value={workspace.map.framingQuestion} onChange={(v) => updateWorkspace((c) => ({ ...c, map: { ...c.map, framingQuestion: v } }))} />
        <button className="btn" onClick={addManualCompetitor}><Plus size={16} /> Add competitor</button>
        <div className="stack">
          {workspace.map.competitors.map((competitor) => (
            <CompetitorEditor key={competitor.id} competitor={competitor} updateWorkspace={updateWorkspace} />
          ))}
        </div>
      </aside>
      <section className="stack">
        <div className="map-wrap stack">
          <div>
            <h1 className="title">{workspace.map.title}</h1>
            <p className="subtle">{workspace.map.subtitle}</p>
            <p className="subtle"><em>{workspace.map.framingQuestion}</em></p>
          </div>
          <MapCanvas workspace={workspace} updateWorkspace={updateWorkspace} />
          <div className="row-actions" style={{ justifyContent: "space-between" }}>
            <span className="pill">{workspace.map.xAxis}</span>
            <span className="pill">{workspace.map.yAxis}</span>
          </div>
        </div>
        <div className="insight-grid">
          <div className="insight"><strong>{workspace.map.competitors.length}</strong><span className="subtle">Mapped competitors</span></div>
          <div className="insight"><strong>{asset?.name ?? "None"}</strong><span className="subtle">Primary asset</span></div>
          <div className="insight"><strong>{highThreat}</strong><span className="subtle">High-position pressure points</span></div>
        </div>
        <div className="panel stack">
          <h2 className="section-title">Strategy notes</h2>
          {workspace.map.strategyNotes.map((note, index) => (
            <div className="inline" key={`${note}-${index}`}>
              <input
                value={note}
                onChange={(event) =>
                  updateWorkspace((current) => {
                    current.map.strategyNotes[index] = event.target.value;
                    return current;
                  })
                }
              />
              <button
                className="btn ghost"
                onClick={() =>
                  updateWorkspace((current) => {
                    current.map.strategyNotes.splice(index, 1);
                    return current;
                  })
                }
              >
                <Trash2 size={15} />
              </button>
            </div>
          ))}
          <button className="btn" onClick={() => updateWorkspace((current) => {
            current.map.strategyNotes.push("New strategic implication");
            return current;
          })}>Add note</button>
        </div>
      </section>
    </div>
  );
}

function CompetitorEditor({
  competitor,
  updateWorkspace
}: {
  competitor: Competitor;
  updateWorkspace: (mutator: (current: WorkspaceState) => WorkspaceState) => void;
}) {
  return (
    <div className={`competitor-card stack ${competitor.isAsset ? "asset" : ""}`}>
      <div className="inline">
        <input
          value={competitor.name}
          onChange={(event) => updateCompetitor(updateWorkspace, competitor.id, { name: event.target.value })}
        />
        <input
          type="color"
          style={{ width: 42, padding: 2 }}
          value={competitor.color}
          onChange={(event) => updateCompetitor(updateWorkspace, competitor.id, { color: event.target.value })}
        />
      </div>
      <Field label="Company" value={competitor.company} onChange={(v) => updateCompetitor(updateWorkspace, competitor.id, { company: v })} />
      <div className="row-actions">
        <button className="btn" onClick={() => updateWorkspace((current) => {
          current.map.competitors.forEach((item) => { item.isAsset = item.id === competitor.id; });
          return current;
        })}>Set Asset X</button>
        <button className="btn ghost" onClick={() => updateWorkspace((current) => {
          current.map.competitors = current.map.competitors.filter((item) => item.id !== competitor.id);
          return current;
        })}><Trash2 size={15} /></button>
      </div>
    </div>
  );
}

function MapCanvas({
  workspace,
  updateWorkspace
}: {
  workspace: WorkspaceState;
  updateWorkspace: (mutator: (current: WorkspaceState) => WorkspaceState) => void;
}) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [dragging, setDragging] = useState<string | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const scale = window.devicePixelRatio || 1;
    canvas.width = rect.width * scale;
    canvas.height = rect.height * scale;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.scale(scale, scale);
    ctx.clearRect(0, 0, rect.width, rect.height);
    ctx.fillStyle = "#fbfbf9";
    ctx.fillRect(0, 0, rect.width, rect.height);
    const pad = 36;
    const w = rect.width - pad * 2;
    const h = rect.height - pad * 2;
    ctx.strokeStyle = "rgba(40,37,29,0.14)";
    ctx.lineWidth = 1;
    for (let i = 0; i <= 4; i += 1) {
      const x = pad + (w / 4) * i;
      const y = pad + (h / 4) * i;
      ctx.beginPath(); ctx.moveTo(x, pad); ctx.lineTo(x, pad + h); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(pad, y); ctx.lineTo(pad + w, y); ctx.stroke();
    }
    ctx.strokeStyle = "#28251d";
    ctx.lineWidth = 1.4;
    ctx.beginPath(); ctx.moveTo(pad + w / 2, pad); ctx.lineTo(pad + w / 2, pad + h); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(pad, pad + h / 2); ctx.lineTo(pad + w, pad + h / 2); ctx.stroke();
    ctx.font = "700 12px sans-serif";
    ctx.fillStyle = "#7a7974";
    workspace.map.quadrantNames.forEach((name, index) => {
      const positions = [
        [pad + 12, pad + 18],
        [pad + w - 90, pad + 18],
        [pad + 12, pad + h - 12],
        [pad + w - 105, pad + h - 12]
      ];
      const [x, y] = positions[index];
      ctx.fillText(name, x, y);
    });
    workspace.map.competitors.forEach((competitor) => {
      const x = pad + ((competitor.x + 100) / 200) * w;
      const y = pad + ((100 - competitor.y) / 200) * h;
      ctx.beginPath();
      ctx.arc(x, y, competitor.isAsset ? 19 : 15, 0, Math.PI * 2);
      ctx.fillStyle = competitor.color;
      ctx.fill();
      ctx.lineWidth = competitor.isAsset ? 4 : 2;
      ctx.strokeStyle = competitor.isAsset ? "#28251d" : "#fff";
      ctx.stroke();
      ctx.fillStyle = "#28251d";
      ctx.font = "700 12px sans-serif";
      ctx.fillText(competitor.name, x + 20, y + 4);
    });
  }, [workspace.map]);

  function positionFromEvent(event: MouseEvent<HTMLCanvasElement>) {
    const canvas = canvasRef.current;
    if (!canvas) return { x: 0, y: 0 };
    const rect = canvas.getBoundingClientRect();
    const pad = 36;
    const w = rect.width - pad * 2;
    const h = rect.height - pad * 2;
    const x = Math.max(-100, Math.min(100, ((event.clientX - rect.left - pad) / w) * 200 - 100));
    const y = Math.max(-100, Math.min(100, 100 - ((event.clientY - rect.top - pad) / h) * 200));
    return { x: Math.round(x), y: Math.round(y) };
  }

  function hitTest(event: MouseEvent<HTMLCanvasElement>) {
    const pos = positionFromEvent(event);
    return workspace.map.competitors.find((competitor) => Math.hypot(competitor.x - pos.x, competitor.y - pos.y) < 15)?.id ?? null;
  }

  return (
    <canvas
      ref={canvasRef}
      className="map-canvas"
      onMouseDown={(event) => setDragging(hitTest(event))}
      onMouseUp={() => setDragging(null)}
      onMouseLeave={() => setDragging(null)}
      onMouseMove={(event) => {
        if (!dragging) return;
        const pos = positionFromEvent(event);
        updateCompetitor(updateWorkspace, dragging, pos);
      }}
    />
  );
}

function PipelineTab({
  workspace,
  updateWorkspace,
  importPipeline
}: {
  workspace: WorkspaceState;
  updateWorkspace: (mutator: (current: WorkspaceState) => WorkspaceState) => void;
  importPipeline: () => void;
}) {
  const rows: Array<[keyof PipelineAsset, string]> = [
    ["candidate", "Candidate"],
    ["mechanism", "MOA"],
    ["modality", "Modality"],
    ["route", "ROA"],
    ["dosingFrequency", "Dosing"],
    ["phase", "Phase"],
    ["trialName", "Trial"],
    ["nctId", "NCT ID"],
    ["anticipatedLaunch", "Launch"],
    ["efficacySignal", "Efficacy"],
    ["safetySignal", "Safety"],
    ["positioning", "Positioning"],
    ["threatLevel", "Threat"],
    ["threatRationale", "Rationale"]
  ];
  return (
    <section className="stack">
      <div className="panel row-actions" style={{ justifyContent: "space-between" }}>
        <div>
          <h2 className="section-title">Pipeline comparison</h2>
          <p className="subtle">Pipeline rows stay connected to mapped competitors.</p>
        </div>
        <button className="btn primary" onClick={importPipeline}><FlaskConical size={16} /> Build from competitors</button>
      </div>
      {workspace.pipeline.length ? (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Field</th>
                {workspace.pipeline.map((asset) => <th key={asset.id}>{asset.company || asset.candidate}</th>)}
              </tr>
            </thead>
            <tbody>
              {rows.map(([key, label]) => (
                <tr key={key}>
                  <th>{label}</th>
                  {workspace.pipeline.map((asset, col) => (
                    <td
                      key={`${asset.id}-${key}`}
                      contentEditable
                      suppressContentEditableWarning
                      onBlur={(event) => updateWorkspace((current) => {
                        const value = event.currentTarget.innerText;
                        (current.pipeline[col] as unknown as Record<string, string>)[key] = value;
                        return current;
                      })}
                    >
                      {String(asset[key] ?? "")}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="empty">No pipeline assets yet. Build rows from mapped competitors after discovery or manual entry.</div>
      )}
    </section>
  );
}

function TimelineTab({ workspace, importTrials }: { workspace: WorkspaceState; importTrials: () => void }) {
  return (
    <section className="stack">
      <div className="panel row-actions" style={{ justifyContent: "space-between" }}>
        <div>
          <h2 className="section-title">Clinical timeline</h2>
          <p className="subtle">Imported trial records are source-controlled and not manually editable.</p>
        </div>
        <button className="btn primary" onClick={importTrials}><RefreshCw size={16} /> Import ClinicalTrials.gov</button>
      </div>
      {workspace.timeline.length ? (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                {["NCT ID", "Disease", "Compound", "Study", "Status", "Start", "Primary completion", "Completion", "First posted", "Expected launch"].map((head) => <th key={head}>{head}</th>)}
              </tr>
            </thead>
            <tbody>
              {workspace.timeline.map((trial: TimelineTrial) => (
                <tr key={trial.id}>
                  <td>{trial.nctId}</td>
                  <td>{trial.disease}</td>
                  <td>{trial.compound}</td>
                  <td>{trial.title}</td>
                  <td>{trial.status}</td>
                  <td>{trial.startDate}</td>
                  <td>{trial.primaryCompletionDate}</td>
                  <td>{trial.completionDate}</td>
                  <td>{trial.firstPostedDate}</td>
                  <td>{trial.expectedLaunchDate}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="empty">No imported trials yet.</div>
      )}
    </section>
  );
}

function KnowledgeTab({
  workspace,
  nodeDetail,
  setNodeDetail,
  buildGraph
}: {
  workspace: WorkspaceState;
  nodeDetail: string | null;
  setNodeDetail: (id: string | null) => void;
  buildGraph: () => void;
}) {
  const detail = workspace.knowledgeGraph.nodes.find((node) => node.id === nodeDetail);
  return (
    <section className="stack">
      <div className="panel row-actions" style={{ justifyContent: "space-between" }}>
        <div>
          <h2 className="section-title">Knowledge graph</h2>
          <p className="subtle">Nodes include articles, authors, MeSH terms, compounds, companies, and trials as evidence becomes available.</p>
        </div>
        <button className="btn primary" onClick={buildGraph}><BookOpen size={16} /> Search PubMed</button>
      </div>
      <div className="kg-layout">
        <div className="kg-canvas">
          <svg width="100%" height="520" viewBox="0 0 900 520" role="img">
            {workspace.knowledgeGraph.edges.map((edge, index) => {
              const sourceIndex = workspace.knowledgeGraph.nodes.findIndex((node) => node.id === edge.source);
              const targetIndex = workspace.knowledgeGraph.nodes.findIndex((node) => node.id === edge.target);
              const a = nodePoint(sourceIndex);
              const b = nodePoint(targetIndex);
              return <line key={`${edge.source}-${edge.target}-${index}`} x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke="#d4d1ca" strokeWidth={edge.weight} />;
            })}
            {workspace.knowledgeGraph.nodes.map((node, index) => {
              const p = nodePoint(index);
              return (
                <g key={node.id} onClick={() => setNodeDetail(node.id)} style={{ cursor: "pointer" }}>
                  <circle cx={p.x} cy={p.y} r={node.type === "disease" ? 28 : node.type === "compound" ? 22 : 15} fill={nodeColor(node.type)} />
                  <text x={p.x + 20} y={p.y + 4} fontSize="12" fontWeight="700" fill="#28251d">{node.label.slice(0, 32)}</text>
                </g>
              );
            })}
          </svg>
        </div>
        <aside className="stack">
          <div className="insight"><strong>{workspace.knowledgeGraph.nodes.length}</strong><span className="subtle">Nodes</span></div>
          <div className="insight"><strong>{workspace.knowledgeGraph.edges.length}</strong><span className="subtle">Edges</span></div>
          {detail ? (
            <div className="node-detail stack">
              <strong>{detail.label}</strong>
              <p className="subtle">{detail.type}</p>
              <p>{detail.detail}</p>
              {detail.url ? <a className="btn" href={detail.url} target="_blank">Open source</a> : null}
            </div>
          ) : (
            <div className="empty">Click a node for in-app details and external links.</div>
          )}
        </aside>
      </div>
    </section>
  );
}

function EvidenceTab({
  workspace,
  updateWorkspace
}: {
  workspace: WorkspaceState;
  updateWorkspace: (mutator: (current: WorkspaceState) => WorkspaceState) => void;
}) {
  return (
    <section className="stack">
      <div className="panel">
        <h2 className="section-title">Evidence review</h2>
        <p className="subtle">Auto-validated evidence can be inspected, filtered, and excluded before AI regeneration.</p>
      </div>
      <div className="grid-2">
        {workspace.evidence.length ? workspace.evidence.map((item: EvidenceItem) => (
          <div className="evidence-item stack" key={item.id}>
            <div className="row-actions" style={{ justifyContent: "space-between" }}>
              <strong>{item.title}</strong>
              <span className="pill">{item.validationStatus}</span>
            </div>
            <p>{item.summary}</p>
            <div className="row-actions">
              <span className="pill">{item.sourceFamily}</span>
              <span className="pill">{item.evidenceLabel}</span>
              <span className="pill">{Math.round(item.confidence * 100)}%</span>
            </div>
            <button className="btn" onClick={() => updateWorkspace((current) => {
              const target = current.evidence.find((evidence) => evidence.id === item.id);
              if (target) target.validationStatus = target.validationStatus === "Excluded" ? "AutoValidated" : "Excluded";
              return current;
            })}>
              {item.validationStatus === "Excluded" ? "Restore evidence" : "Exclude evidence"}
            </button>
          </div>
        )) : <div className="empty">No evidence yet. Run discovery or load demo data.</div>}
      </div>
    </section>
  );
}

function ExportsTab({ workspace, exportProject }: { workspace: WorkspaceState; exportProject: (type: "pdf" | "pptx") => void }) {
  return (
    <section className="grid-2">
      <div className="panel stack">
        <h2 className="section-title">Backend exports</h2>
        <p>Exports include executive summary, map, pipeline, timeline, knowledge graph snapshot, evidence appendix, AI recommendations, methodology, and source list.</p>
        <div className="actions">
          <button className="btn primary" onClick={() => exportProject("pptx")}><Download size={16} /> Generate PowerPoint</button>
          <button className="btn primary" onClick={() => exportProject("pdf")}><Download size={16} /> Generate PDF</button>
        </div>
      </div>
      <div className="panel stack">
        <h2 className="section-title">Project bundle</h2>
        <p className="subtle">JSON import/export keeps workspaces portable while Snowflake remains the system of record.</p>
        <button
          className="btn"
          onClick={() => {
            const blob = new Blob([JSON.stringify(workspace, null, 2)], { type: "application/json" });
            const url = URL.createObjectURL(blob);
            const link = document.createElement("a");
            link.href = url;
            link.download = `${workspace.projectId}.json`;
            link.click();
            URL.revokeObjectURL(url);
          }}
        >
          <FileJson size={16} /> Download JSON
        </button>
      </div>
    </section>
  );
}

function Field({
  label,
  value,
  onChange,
  area = false
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  area?: boolean;
}) {
  return (
    <label>
      {label}
      {area ? <textarea value={value} onChange={(event) => onChange(event.target.value)} /> : <input value={value} onChange={(event) => onChange(event.target.value)} />}
    </label>
  );
}

function updateCompetitor(
  updateWorkspace: (mutator: (current: WorkspaceState) => WorkspaceState) => void,
  id: string,
  patch: Partial<Competitor>
) {
  updateWorkspace((current) => {
    const competitor = current.map.competitors.find((item) => item.id === id);
    if (competitor) Object.assign(competitor, patch);
    return current;
  });
}

function nodePoint(index: number) {
  if (index < 0) return { x: 450, y: 260 };
  const center = { x: 450, y: 260 };
  if (index === 0) return center;
  const angle = (index / 12) * Math.PI * 2;
  const radius = 80 + (index % 4) * 55;
  return { x: center.x + Math.cos(angle) * radius, y: center.y + Math.sin(angle) * radius };
}

function nodeColor(type: string) {
  return {
    disease: "#01696f",
    compound: "#964219",
    article: "#a12c7b",
    author: "#7a39bb",
    mesh: "#006494",
    company: "#437a22",
    trial: "#d19900"
  }[type] ?? "#7a7974";
}

function tabLabel(tab: TabKey) {
  return {
    map: "Competitor Map",
    pipeline: "Pipeline",
    timeline: "Timeline",
    knowledge: "Knowledge Graph",
    evidence: "Evidence",
    exports: "Exports"
  }[tab];
}
