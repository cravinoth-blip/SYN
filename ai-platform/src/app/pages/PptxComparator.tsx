import { useRef, useState } from 'react';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Badge } from '../components/ui/badge';
import { Progress } from '../components/ui/progress';
import { Skeleton } from '../components/ui/skeleton';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '../components/ui/collapsible';
import { Textarea } from '../components/ui/textarea';
import {
  FileText,
  GitCompare,
  Download,
  Sparkles,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
} from 'lucide-react';
import { toast } from 'sonner';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ShapeData {
  shape_id: number;
  shape_name: string;
  text: string;
}

interface SlideData {
  slide_idx: number;
  shapes: ShapeData[];
}

interface SlidesResponse {
  slide_count_a: number;
  slide_count_b: number;
  slides_a: SlideData[];
  slides_b: SlideData[];
}

interface Difference {
  aspect: string;
  slide_a: string;
  slide_b: string;
}

interface Suggestion {
  shape_name: string;
  original_text: string;
  suggested_text: string;
  reason: string;
}

interface AIResult {
  summary: string;
  differences: Difference[];
  suggestions: Suggestion[];
  overall_assessment: string;
}

interface EditEntry {
  slide_idx: number;
  shape_name: string;
  new_text: string;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const API_BASE = (import.meta as { env: Record<string, string> }).env.VITE_API_URL ?? 'http://localhost:8000';

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function DropZone({
  label,
  file,
  onFile,
}: {
  label: string;
  file: File | null;
  onFile: (f: File) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped && dropped.name.endsWith('.pptx')) {
      onFile(dropped);
    } else {
      toast.error('Please drop a .pptx file.');
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    if (selected) onFile(selected);
  };

  return (
    <div
      className={`flex flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed p-8 transition-colors cursor-pointer
        ${dragging ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/50 hover:bg-muted/30'}`}
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      onClick={() => inputRef.current?.click()}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".pptx"
        className="hidden"
        onChange={handleChange}
      />
      <FileText className={`h-10 w-10 ${file ? 'text-primary' : 'text-muted-foreground'}`} />
      <div className="text-center">
        <p className="text-sm font-medium">{label}</p>
        {file ? (
          <Badge variant="secondary" className="mt-1 max-w-[200px] truncate text-xs">
            {file.name}
          </Badge>
        ) : (
          <p className="text-xs text-muted-foreground mt-1">
            Drag &amp; drop or click to select
          </p>
        )}
      </div>
    </div>
  );
}

function ShapeCard({ shape }: { shape: ShapeData }) {
  return (
    <div className="rounded-lg border bg-card p-3 space-y-1">
      <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide truncate">
        {shape.shape_name}
      </p>
      <p className="text-sm whitespace-pre-wrap leading-relaxed">
        {shape.text || <span className="text-muted-foreground italic">— empty —</span>}
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function PptxComparator() {
  // Files
  const [fileA, setFileA] = useState<File | null>(null);
  const [fileB, setFileB] = useState<File | null>(null);

  // Slides data
  const [slidesData, setSlidesData] = useState<SlidesResponse | null>(null);
  const [currentSlide, setCurrentSlide] = useState(0);

  // AI
  const [aiResults, setAiResults] = useState<Record<number, AIResult>>({});
  const [analyzingSlide, setAnalyzingSlide] = useState(false);
  const [analyzingAll, setAnalyzingAll] = useState(false);
  const [analyzeProgress, setAnalyzeProgress] = useState(0);

  // Edits
  const [edits, setEdits] = useState<EditEntry[]>([]);
  const [editDraft, setEditDraft] = useState<Record<string, string>>({});
  const [editPanelOpen, setEditPanelOpen] = useState(false);

  // Loading
  const [loadingSlides, setLoadingSlides] = useState(false);
  const [downloading, setDownloading] = useState(false);

  // ---------------------------------------------------------------------------
  // Handlers
  // ---------------------------------------------------------------------------

  const loadSlides = async (fA: File, fB: File) => {
    setLoadingSlides(true);
    setSlidesData(null);
    setAiResults({});
    setEdits([]);
    setEditDraft({});
    setCurrentSlide(0);
    try {
      const form = new FormData();
      form.append('file_a', fA);
      form.append('file_b', fB);
      const res = await fetch(`${API_BASE}/pptx/slides`, { method: 'POST', body: form });
      if (!res.ok) throw new Error(await res.text());
      const data: SlidesResponse = await res.json();
      setSlidesData(data);
      toast.success(`Loaded ${data.slide_count_a} slides (A) and ${data.slide_count_b} slides (B)`);
    } catch (err) {
      toast.error(`Failed to load slides: ${(err as Error).message}`);
    } finally {
      setLoadingSlides(false);
    }
  };

  const handleFileA = (f: File) => {
    setFileA(f);
    if (fileB) loadSlides(f, fileB);
  };

  const handleFileB = (f: File) => {
    setFileB(f);
    if (fileA) loadSlides(fileA, f);
  };

  const analyzeSlide = async (idx: number) => {
    if (!fileA || !fileB) return;
    setAnalyzingSlide(true);
    try {
      const form = new FormData();
      form.append('file_a', fileA);
      form.append('file_b', fileB);
      form.append('slide_idx', String(idx));
      form.append('model', 'gpt-4o');
      const res = await fetch(`${API_BASE}/pptx/compare-slide`, { method: 'POST', body: form });
      if (!res.ok) throw new Error(await res.text());
      const data: AIResult = await res.json();
      setAiResults((prev) => ({ ...prev, [idx]: data }));
      toast.success('Analysis complete');
    } catch (err) {
      toast.error(`Analysis failed: ${(err as Error).message}`);
    } finally {
      setAnalyzingSlide(false);
    }
  };

  const analyzeAll = async () => {
    if (!fileA || !fileB || !slidesData) return;
    const total = Math.min(slidesData.slide_count_a, slidesData.slide_count_b);
    setAnalyzingAll(true);
    setAnalyzeProgress(0);
    const results: Record<number, AIResult> = { ...aiResults };
    for (let i = 0; i < total; i++) {
      try {
        const form = new FormData();
        form.append('file_a', fileA);
        form.append('file_b', fileB);
        form.append('slide_idx', String(i));
        form.append('model', 'gpt-4o');
        const res = await fetch(`${API_BASE}/pptx/compare-slide`, { method: 'POST', body: form });
        if (res.ok) {
          results[i] = await res.json();
        }
      } catch {
        // Continue on individual failures
      }
      setAnalyzeProgress(Math.round(((i + 1) / total) * 100));
    }
    setAiResults(results);
    setAnalyzingAll(false);
    toast.success(`Analyzed ${total} slides`);
  };

  const applySuggestion = (suggestion: Suggestion) => {
    const entry: EditEntry = {
      slide_idx: currentSlide,
      shape_name: suggestion.shape_name,
      new_text: suggestion.suggested_text,
    };
    setEdits((prev) => {
      const filtered = prev.filter(
        (e) => !(e.slide_idx === entry.slide_idx && e.shape_name === entry.shape_name)
      );
      return [...filtered, entry];
    });
    setEditDraft((prev) => ({
      ...prev,
      [`${currentSlide}::${suggestion.shape_name}`]: suggestion.suggested_text,
    }));
    toast.success(`Edit queued for "${suggestion.shape_name}"`);
  };

  const saveEdits = () => {
    const newEntries: EditEntry[] = [];
    for (const [key, text] of Object.entries(editDraft)) {
      const [slideIdxStr, ...nameParts] = key.split('::');
      newEntries.push({
        slide_idx: parseInt(slideIdxStr, 10),
        shape_name: nameParts.join('::'),
        new_text: text,
      });
    }
    setEdits((prev) => {
      const merged = [...prev];
      for (const entry of newEntries) {
        const idx = merged.findIndex(
          (e) => e.slide_idx === entry.slide_idx && e.shape_name === entry.shape_name
        );
        if (idx !== -1) {
          merged[idx] = entry;
        } else {
          merged.push(entry);
        }
      }
      return merged;
    });
    toast.success(`${newEntries.length} edits saved to queue`);
  };

  const handleDownload = async () => {
    if (!fileA) return;
    if (edits.length === 0) {
      toast.error('No edits to apply. Make some edits first.');
      return;
    }
    setDownloading(true);
    try {
      const form = new FormData();
      form.append('file_a', fileA);
      form.append('edits', JSON.stringify(edits));
      const res = await fetch(`${API_BASE}/pptx/edit`, { method: 'POST', body: form });
      if (!res.ok) throw new Error(await res.text());
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = fileA.name.replace('.pptx', '') + '_edited.pptx';
      a.click();
      URL.revokeObjectURL(url);
      toast.success('Download started');
    } catch (err) {
      toast.error(`Download failed: ${(err as Error).message}`);
    } finally {
      setDownloading(false);
    }
  };

  // ---------------------------------------------------------------------------
  // Derived state
  // ---------------------------------------------------------------------------

  const slideA = slidesData?.slides_a[currentSlide] ?? null;
  const slideB = slidesData?.slides_b[currentSlide] ?? null;
  const currentResult = aiResults[currentSlide] ?? null;
  const maxSlides = slidesData
    ? Math.max(slidesData.slide_count_a, slidesData.slide_count_b)
    : 0;

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <div className="min-h-screen bg-gradient-to-br from-background to-muted/20">
      <div className="container mx-auto px-4 py-8 space-y-6 max-w-7xl">

        {/* Header */}
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <GitCompare className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">PPTX AI Comparator</h1>
            <p className="text-sm text-muted-foreground">
              Upload two PowerPoint files to compare, analyse and edit with AI
            </p>
          </div>
          {edits.length > 0 && (
            <Badge variant="secondary" className="ml-auto">
              {edits.length} pending edit{edits.length !== 1 ? 's' : ''}
            </Badge>
          )}
        </div>

        {/* File Upload */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">1. Upload Presentations</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <DropZone label="Presentation A (Base)" file={fileA} onFile={handleFileA} />
              <DropZone label="Presentation B (Reference)" file={fileB} onFile={handleFileB} />
            </div>
            {loadingSlides && (
              <div className="mt-4 space-y-2">
                <Skeleton className="h-4 w-3/4" />
                <Skeleton className="h-4 w-1/2" />
              </div>
            )}
          </CardContent>
        </Card>

        {slidesData && (
          <>
            {/* Slide Navigator */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center justify-between">
                  <span>2. Slide Navigator</span>
                  <span className="text-sm font-normal text-muted-foreground">
                    A: {slidesData.slide_count_a} slides &nbsp;|&nbsp; B: {slidesData.slide_count_b} slides
                  </span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                {/* Thumbnail strip */}
                <div className="flex gap-2 overflow-x-auto pb-2">
                  {Array.from({ length: maxSlides }).map((_, i) => (
                    <button
                      key={i}
                      onClick={() => setCurrentSlide(i)}
                      className={`flex-shrink-0 h-12 w-16 rounded border text-xs font-medium transition-all
                        ${currentSlide === i
                          ? 'border-primary bg-primary text-primary-foreground shadow'
                          : 'border-border bg-card text-muted-foreground hover:border-primary/50 hover:text-foreground'
                        }`}
                    >
                      {i + 1}
                    </button>
                  ))}
                </div>

                {/* Prev / Next */}
                <div className="flex items-center justify-between mt-3">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={currentSlide === 0}
                    onClick={() => setCurrentSlide((s) => s - 1)}
                  >
                    <ChevronLeft className="h-4 w-4 mr-1" />
                    Previous
                  </Button>
                  <span className="text-sm text-muted-foreground">
                    Slide {currentSlide + 1} of {maxSlides}
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={currentSlide >= maxSlides - 1}
                    onClick={() => setCurrentSlide((s) => s + 1)}
                  >
                    Next
                    <ChevronRight className="h-4 w-4 ml-1" />
                  </Button>
                </div>
              </CardContent>
            </Card>

            {/* Side-by-side Slide Content */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">3. Slide Content — Slide {currentSlide + 1}</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
                  {/* Slide A */}
                  <div className="space-y-3">
                    <div className="flex items-center gap-2">
                      <Badge>A</Badge>
                      <span className="text-sm font-medium truncate">{fileA?.name}</span>
                    </div>
                    {slideA ? (
                      slideA.shapes.length > 0 ? (
                        slideA.shapes.map((shape) => (
                          <ShapeCard key={shape.shape_id} shape={shape} />
                        ))
                      ) : (
                        <p className="text-sm text-muted-foreground italic">No text shapes on this slide.</p>
                      )
                    ) : (
                      <p className="text-sm text-muted-foreground italic">Slide not available in Presentation A.</p>
                    )}
                  </div>

                  {/* Slide B */}
                  <div className="space-y-3">
                    <div className="flex items-center gap-2">
                      <Badge variant="secondary">B</Badge>
                      <span className="text-sm font-medium truncate">{fileB?.name}</span>
                    </div>
                    {slideB ? (
                      slideB.shapes.length > 0 ? (
                        slideB.shapes.map((shape) => (
                          <ShapeCard key={shape.shape_id} shape={shape} />
                        ))
                      ) : (
                        <p className="text-sm text-muted-foreground italic">No text shapes on this slide.</p>
                      )
                    ) : (
                      <p className="text-sm text-muted-foreground italic">Slide not available in Presentation B.</p>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* AI Analysis */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex flex-wrap items-center gap-3">
                  <span>4. AI Analysis</span>
                  <Button
                    size="sm"
                    onClick={() => analyzeSlide(currentSlide)}
                    disabled={analyzingSlide || analyzingAll}
                  >
                    <Sparkles className="h-4 w-4 mr-1.5" />
                    {analyzingSlide ? 'Analysing…' : 'Analyse this slide'}
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={analyzeAll}
                    disabled={analyzingSlide || analyzingAll}
                  >
                    <Sparkles className="h-4 w-4 mr-1.5" />
                    {analyzingAll ? `Analysing… ${analyzeProgress}%` : 'Analyse all slides'}
                  </Button>
                </CardTitle>
              </CardHeader>
              <CardContent>
                {analyzingAll && (
                  <div className="mb-4 space-y-1">
                    <p className="text-xs text-muted-foreground">
                      Analysing slide by slide… {analyzeProgress}%
                    </p>
                    <Progress value={analyzeProgress} className="h-2" />
                  </div>
                )}

                {analyzingSlide && !currentResult && (
                  <div className="space-y-2">
                    <Skeleton className="h-4 w-full" />
                    <Skeleton className="h-4 w-5/6" />
                    <Skeleton className="h-4 w-3/4" />
                  </div>
                )}

                {currentResult ? (
                  <div className="space-y-4">
                    {currentResult.summary && (
                      <p className="text-sm leading-relaxed text-muted-foreground border-l-2 border-primary pl-3">
                        {currentResult.summary}
                      </p>
                    )}

                    <Tabs defaultValue="differences">
                      <TabsList>
                        <TabsTrigger value="differences">
                          Differences
                          {currentResult.differences.length > 0 && (
                            <Badge variant="secondary" className="ml-1.5 text-xs">
                              {currentResult.differences.length}
                            </Badge>
                          )}
                        </TabsTrigger>
                        <TabsTrigger value="suggestions">
                          Suggestions
                          {currentResult.suggestions.length > 0 && (
                            <Badge variant="secondary" className="ml-1.5 text-xs">
                              {currentResult.suggestions.length}
                            </Badge>
                          )}
                        </TabsTrigger>
                        <TabsTrigger value="assessment">Assessment</TabsTrigger>
                      </TabsList>

                      {/* Differences */}
                      <TabsContent value="differences" className="mt-4 space-y-3">
                        {currentResult.differences.length === 0 ? (
                          <p className="text-sm text-muted-foreground">No differences identified.</p>
                        ) : (
                          currentResult.differences.map((diff, i) => (
                            <div key={i} className="rounded-lg border bg-card overflow-hidden">
                              <div className="bg-muted/50 px-3 py-1.5">
                                <p className="text-xs font-semibold uppercase tracking-wide">{diff.aspect}</p>
                              </div>
                              <div className="grid grid-cols-2 divide-x">
                                <div className="p-3">
                                  <p className="text-xs font-medium text-muted-foreground mb-1">Slide A</p>
                                  <p className="text-sm">{diff.slide_a || '—'}</p>
                                </div>
                                <div className="p-3">
                                  <p className="text-xs font-medium text-muted-foreground mb-1">Slide B</p>
                                  <p className="text-sm">{diff.slide_b || '—'}</p>
                                </div>
                              </div>
                            </div>
                          ))
                        )}
                      </TabsContent>

                      {/* Suggestions */}
                      <TabsContent value="suggestions" className="mt-4 space-y-3">
                        {currentResult.suggestions.length === 0 ? (
                          <p className="text-sm text-muted-foreground">No suggestions generated.</p>
                        ) : (
                          currentResult.suggestions.map((sug, i) => (
                            <div key={i} className="rounded-lg border bg-card p-4 space-y-2">
                              <div className="flex items-start justify-between gap-2">
                                <Badge variant="outline" className="text-xs shrink-0">
                                  {sug.shape_name}
                                </Badge>
                                <Button
                                  size="sm"
                                  variant="secondary"
                                  onClick={() => applySuggestion(sug)}
                                  className="shrink-0"
                                >
                                  Apply
                                </Button>
                              </div>
                              <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                                <div>
                                  <p className="text-xs font-medium text-muted-foreground mb-1">Original</p>
                                  <p className="text-sm line-through text-muted-foreground">
                                    {sug.original_text || '—'}
                                  </p>
                                </div>
                                <div>
                                  <p className="text-xs font-medium text-muted-foreground mb-1">Suggested</p>
                                  <p className="text-sm text-emerald-600 dark:text-emerald-400">
                                    {sug.suggested_text || '—'}
                                  </p>
                                </div>
                              </div>
                              {sug.reason && (
                                <p className="text-xs text-muted-foreground italic">{sug.reason}</p>
                              )}
                            </div>
                          ))
                        )}
                      </TabsContent>

                      {/* Assessment */}
                      <TabsContent value="assessment" className="mt-4">
                        {currentResult.overall_assessment ? (
                          <p className="text-sm leading-relaxed">{currentResult.overall_assessment}</p>
                        ) : (
                          <p className="text-sm text-muted-foreground">No assessment available.</p>
                        )}
                      </TabsContent>
                    </Tabs>
                  </div>
                ) : (
                  !analyzingSlide && !analyzingAll && (
                    <p className="text-sm text-muted-foreground">
                      Click "Analyse this slide" to run AI comparison for slide {currentSlide + 1}.
                    </p>
                  )
                )}
              </CardContent>
            </Card>

            {/* Edit Panel */}
            <Card>
              <Collapsible open={editPanelOpen} onOpenChange={setEditPanelOpen}>
                <CollapsibleTrigger asChild>
                  <CardHeader className="cursor-pointer hover:bg-muted/30 transition-colors rounded-t-lg">
                    <CardTitle className="text-base flex items-center justify-between">
                      <span>5. Edit Panel — Slide {currentSlide + 1} (A)</span>
                      <ChevronDown
                        className={`h-4 w-4 text-muted-foreground transition-transform ${editPanelOpen ? 'rotate-180' : ''}`}
                      />
                    </CardTitle>
                  </CardHeader>
                </CollapsibleTrigger>
                <CollapsibleContent>
                  <CardContent className="pt-0 space-y-4">
                    {slideA && slideA.shapes.length > 0 ? (
                      <>
                        {slideA.shapes.map((shape) => {
                          const key = `${currentSlide}::${shape.shape_name}`;
                          const value = editDraft[key] ?? shape.text;
                          return (
                            <div key={shape.shape_id} className="space-y-1">
                              <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                                {shape.shape_name}
                              </label>
                              <Textarea
                                value={value}
                                rows={3}
                                onChange={(e) =>
                                  setEditDraft((prev) => ({ ...prev, [key]: e.target.value }))
                                }
                                className="text-sm resize-y"
                              />
                            </div>
                          );
                        })}
                        <Button onClick={saveEdits} size="sm">
                          Save edits to queue
                        </Button>
                      </>
                    ) : (
                      <p className="text-sm text-muted-foreground">
                        No editable text shapes on this slide in Presentation A.
                      </p>
                    )}
                  </CardContent>
                </CollapsibleContent>
              </Collapsible>
            </Card>

            {/* Download */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">6. Download Edited Presentation</CardTitle>
              </CardHeader>
              <CardContent className="flex items-center gap-4 flex-wrap">
                <Button
                  onClick={handleDownload}
                  disabled={downloading || !fileA || edits.length === 0}
                >
                  <Download className="h-4 w-4 mr-2" />
                  {downloading ? 'Preparing…' : 'Download Presentation A (edited)'}
                </Button>
                {edits.length > 0 ? (
                  <p className="text-sm text-muted-foreground">
                    {edits.length} edit{edits.length !== 1 ? 's' : ''} will be applied across{' '}
                    {new Set(edits.map((e) => e.slide_idx)).size} slide
                    {new Set(edits.map((e) => e.slide_idx)).size !== 1 ? 's' : ''}.
                  </p>
                ) : (
                  <p className="text-sm text-muted-foreground">
                    No edits queued yet. Use the Edit Panel or apply AI suggestions above.
                  </p>
                )}
              </CardContent>
            </Card>
          </>
        )}

        {!slidesData && !loadingSlides && (
          <div className="flex flex-col items-center justify-center py-16 text-center text-muted-foreground gap-3">
            <GitCompare className="h-12 w-12 opacity-30" />
            <p className="text-sm">Upload both presentations above to get started.</p>
          </div>
        )}
      </div>
    </div>
  );
}
