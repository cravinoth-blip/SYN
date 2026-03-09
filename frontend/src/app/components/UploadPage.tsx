import { useState, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router';
import { API_BASE } from '../../lib/api';
import {
  Upload, X, CheckCircle2, AlertCircle, FileText,
  Loader2, ArrowRight, BookOpen, Info,
  ChevronRight,
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

interface UploadResult {
  file: File;
  status: 'uploading' | 'done' | 'error';
  progress: number;
  step: string;
  message: string;
  title?: string;
  summary?: string;
  chunksAdded?: number;
  chunksSkipped?: number;
  error?: string;
}

const ALLOWED_EXTS = ['.pdf', '.docx', '.doc', '.txt', '.json', '.xlsx', '.xls'];

function UploadCard({ result, onRemove }: { result: UploadResult; onRemove: () => void }) {
  const isDone = result.status === 'done';
  const isError = result.status === 'error';
  const isUploading = result.status === 'uploading';

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className={`bg-white rounded-xl border overflow-hidden ${isError ? 'border-red-200' : isDone ? 'border-emerald-200' : 'border-slate-200'}`}
    >
      <div className="p-4">
        <div className="flex items-start gap-3">
          <div className={`w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 ${isError ? 'bg-red-100' : isDone ? 'bg-emerald-100' : 'bg-blue-100'}`}>
            {isError ? <AlertCircle className="w-5 h-5 text-red-500" /> :
             isDone ? <CheckCircle2 className="w-5 h-5 text-emerald-500" /> :
             <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-slate-800 font-semibold truncate" style={{ fontSize: '13px' }}>
              {result.file.name}
            </p>
            <p className={`mt-0.5 ${isError ? 'text-red-600' : 'text-slate-500'}`} style={{ fontSize: '12px' }}>
              {isError ? result.error : result.message}
            </p>

            {/* Progress bar */}
            {isUploading && (
              <div className="mt-2 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                <motion.div
                  className="h-full bg-blue-500 rounded-full"
                  animate={{ width: `${result.progress}%` }}
                  transition={{ duration: 0.4 }}
                />
              </div>
            )}

            {/* Result details */}
            {isDone && (
              <div className="mt-2 space-y-1">
                {result.title && (
                  <p className="text-slate-600 text-xs">
                    <span className="font-semibold">Title:</span> {result.title}
                  </p>
                )}
                <div className="flex items-center gap-3">
                  {result.chunksAdded !== undefined && (
                    <span className="text-emerald-600 text-xs font-semibold">+{result.chunksAdded} chunks added</span>
                  )}
                  {result.chunksSkipped !== undefined && result.chunksSkipped > 0 && (
                    <span className="text-slate-400 text-xs">{result.chunksSkipped} already existed</span>
                  )}
                </div>
                {result.summary && (
                  <p className="text-slate-400 text-xs line-clamp-2 mt-1">{result.summary}</p>
                )}
              </div>
            )}
          </div>
          {(isDone || isError) && (
            <button onClick={onRemove} className="text-slate-300 hover:text-slate-500 flex-shrink-0">
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
    </motion.div>
  );
}

export function UploadPage() {
  const navigate = useNavigate();
  const [results, setResults] = useState<UploadResult[]>([]);
  const [dragging, setDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const processFile = async (file: File) => {
    const ext = '.' + file.name.split('.').pop()?.toLowerCase();
    if (!ALLOWED_EXTS.includes(ext)) {
      setResults((prev) => [...prev, {
        file, status: 'error', progress: 0, step: '', message: '', error: `Unsupported file type: ${ext}`,
      }]);
      return;
    }

    const id = Date.now() + Math.random();
    const initialResult: UploadResult = {
      file, status: 'uploading', progress: 2, step: 'start', message: 'Uploading…',
    };

    setResults((prev) => [...prev, initialResult]);

    try {
      const fd = new FormData();
      fd.append('file', file);

      const response = await fetch(`${API_BASE}/upload/stream`, { method: 'POST', body: fd });
      if (!response.ok) throw new Error(`Server error: ${response.status}`);

      const reader = response.body!.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const raw = decoder.decode(value, { stream: true });
        for (const line of raw.split('\n')) {
          if (!line.startsWith('data: ')) continue;
          try {
            const evt = JSON.parse(line.slice(6));
            if (evt.type === 'progress') {
              setResults((prev) => prev.map((r) =>
                r.file === file
                  ? { ...r, status: 'uploading', progress: evt.pct ?? r.progress, step: evt.step, message: evt.message }
                  : r
              ));
            } else if (evt.type === 'done') {
              setResults((prev) => prev.map((r) =>
                r.file === file
                  ? {
                      ...r,
                      status: 'done',
                      progress: 100,
                      message: evt.message,
                      title: evt.title,
                      summary: evt.summary,
                      chunksAdded: evt.chunks_added,
                      chunksSkipped: evt.chunks_skipped,
                    }
                  : r
              ));
            } else if (evt.type === 'error') {
              setResults((prev) => prev.map((r) =>
                r.file === file ? { ...r, status: 'error', progress: 0, message: '', error: evt.message } : r
              ));
            }
          } catch { /* skip */ }
        }
      }
    } catch (err) {
      setResults((prev) => prev.map((r) =>
        r.file === file ? { ...r, status: 'error', progress: 0, message: '', error: (err as Error).message } : r
      ));
    }
  };

  const handleFiles = (files: FileList | null) => {
    if (!files) return;
    Array.from(files).forEach(processFile);
  };

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    handleFiles(e.dataTransfer.files);
  }, []);

  const removeResult = (file: File) => {
    setResults((prev) => prev.filter((r) => r.file !== file));
  };

  const doneCount = results.filter((r) => r.status === 'done').length;
  const hasResults = results.length > 0;

  return (
    <div className="p-6 max-w-[900px] mx-auto">
      <div className="mb-6">
        <h1 className="text-slate-900">Upload Documents</h1>
        <p className="text-slate-500 mt-1" style={{ fontSize: '14px' }}>
          Add new documents to your RAG knowledge base. Files are extracted, chunked, and embedded automatically.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Upload zone */}
        <div className="lg:col-span-2 space-y-4">
          {/* Drop zone */}
          <div
            className={`rounded-xl border-2 border-dashed transition-all cursor-pointer ${dragging ? 'border-blue-400 bg-blue-50' : 'border-slate-300 bg-white hover:border-blue-300 hover:bg-slate-50'}`}
            style={{ minHeight: 200 }}
            onClick={() => fileInputRef.current?.click()}
            onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
          >
            <div className="flex flex-col items-center justify-center p-10 text-center">
              <div className={`w-14 h-14 rounded-2xl flex items-center justify-center mb-4 transition-colors ${dragging ? 'bg-blue-100' : 'bg-slate-100'}`}>
                <Upload className={`w-7 h-7 transition-colors ${dragging ? 'text-blue-600' : 'text-slate-400'}`} />
              </div>
              <p className="text-slate-700 font-semibold" style={{ fontSize: '15px' }}>
                {dragging ? 'Drop files here' : 'Click or drag files to upload'}
              </p>
              <p className="text-slate-400 mt-1" style={{ fontSize: '13px' }}>
                PDF, DOCX, DOC, TXT, JSON, XLSX, XLS
              </p>
              <p className="text-slate-300 mt-1" style={{ fontSize: '12px' }}>Multiple files supported</p>
            </div>
          </div>

          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept={ALLOWED_EXTS.join(',')}
            className="hidden"
            onChange={(e) => handleFiles(e.target.files)}
          />

          {/* Upload results */}
          <AnimatePresence>
            {hasResults && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-3">
                <div className="flex items-center justify-between">
                  <p className="text-slate-600" style={{ fontSize: '13px', fontWeight: 600 }}>
                    {results.length} file{results.length !== 1 ? 's' : ''} · {doneCount} complete
                  </p>
                  {doneCount > 0 && (
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => navigate('/documents')}
                        className="flex items-center gap-1.5 text-blue-600 hover:text-blue-700"
                        style={{ fontSize: '13px' }}
                      >
                        View library <ArrowRight className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  )}
                </div>
                {results.map((result) => (
                  <UploadCard
                    key={result.file.name + result.file.size}
                    result={result}
                    onRemove={() => removeResult(result.file)}
                  />
                ))}
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Info panel */}
        <div className="space-y-4">
          {/* What happens */}
          <div className="bg-white rounded-xl border border-slate-200 p-5">
            <div className="flex items-center gap-2 mb-4">
              <Info className="w-4 h-4 text-blue-600" />
              <h3 className="text-slate-800" style={{ fontSize: '14px' }}>Processing Pipeline</h3>
            </div>
            <div className="space-y-3">
              {[
                { step: '1', label: 'Text Extraction', desc: 'PDF/DOCX text and tables extracted' },
                { step: '2', label: 'DOI Lookup', desc: 'Crossref metadata fetched for PDFs' },
                { step: '3', label: 'AI Enrichment', desc: 'Title & summary generated via GPT-4o-mini' },
                { step: '4', label: 'Chunking', desc: 'Split into 1000-1500 char chunks' },
                { step: '5', label: 'Embedding', desc: 'text-embedding-3-small (1536 dims)' },
                { step: '6', label: 'Indexing', desc: 'Stored in ChromaDB vector database' },
              ].map(({ step, label, desc }) => (
                <div key={step} className="flex items-start gap-3">
                  <div className="w-6 h-6 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center flex-shrink-0" style={{ fontSize: '11px', fontWeight: 700 }}>
                    {step}
                  </div>
                  <div>
                    <p className="text-slate-700" style={{ fontSize: '12px', fontWeight: 600 }}>{label}</p>
                    <p className="text-slate-400" style={{ fontSize: '11px' }}>{desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Quick links */}
          <div className="bg-blue-50 border border-blue-100 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-3">
              <BookOpen className="w-4 h-4 text-blue-600" />
              <span className="text-blue-800" style={{ fontSize: '13px', fontWeight: 600 }}>After uploading</span>
            </div>
            <div className="space-y-2">
              <button
                onClick={() => navigate('/documents')}
                className="w-full text-left flex items-center gap-2 text-blue-600 hover:text-blue-700"
                style={{ fontSize: '13px' }}
              >
                <ChevronRight className="w-3.5 h-3.5" />
                Browse document library
              </button>
              <button
                onClick={() => navigate('/chat')}
                className="w-full text-left flex items-center gap-2 text-blue-600 hover:text-blue-700"
                style={{ fontSize: '13px' }}
              >
                <ChevronRight className="w-3.5 h-3.5" />
                Start chatting with your documents
              </button>
            </div>
          </div>

          {/* Supported types */}
          <div className="bg-white rounded-xl border border-slate-200 p-4">
            <h4 className="text-slate-700 mb-3" style={{ fontSize: '13px', fontWeight: 600 }}>Supported Formats</h4>
            <div className="flex flex-wrap gap-2">
              {ALLOWED_EXTS.map((ext) => (
                <span key={ext} className="flex items-center gap-1 px-2 py-1 bg-slate-100 rounded text-slate-600" style={{ fontSize: '12px' }}>
                  <FileText className="w-3 h-3" />
                  {ext.slice(1).toUpperCase()}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
