import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router';
import { API_BASE } from '../../lib/api';
import {
  Search, BookOpen, ExternalLink, RefreshCw,
  ChevronDown, Trash2, MessageSquare, Upload,
  FileText, Calendar, Users, Hash, AlertCircle,
  CheckCircle2, Loader2,
} from 'lucide-react';

interface Document {
  source_file: string;
  title: string;
  authors: string;
  published: string;
  doi: string;
  summary: string;
  file_type: string;
  chunk_count: number;
}

const FILE_TYPE_COLORS: Record<string, string> = {
  pdf: 'bg-red-100 text-red-700',
  docx: 'bg-blue-100 text-blue-700',
  doc: 'bg-blue-100 text-blue-700',
  txt: 'bg-slate-100 text-slate-600',
  json: 'bg-amber-100 text-amber-700',
  xlsx: 'bg-emerald-100 text-emerald-700',
  xls: 'bg-emerald-100 text-emerald-700',
};

function DocCard({
  doc,
  onDelete,
  onChat,
  expanded,
  onToggle,
}: {
  doc: Document;
  onDelete: (sf: string) => void;
  onChat: (sf: string) => void;
  expanded: boolean;
  onToggle: () => void;
}) {
  const [deleting, setDeleting] = useState(false);
  const ftColor = FILE_TYPE_COLORS[doc.file_type] || 'bg-slate-100 text-slate-600';

  const handleDelete = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!window.confirm(`Remove "${doc.title || doc.source_file}" from the index?`)) return;
    setDeleting(true);
    try {
      const res = await fetch(`${API_BASE}/documents/${encodeURIComponent(doc.source_file)}`, { method: 'DELETE' });
      if (!res.ok) throw new Error(`Delete failed: ${res.status}`);
      onDelete(doc.source_file);
    } catch (err) {
      alert((err as Error).message);
      setDeleting(false);
    }
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden hover:shadow-sm transition-shadow">
      <div className="p-5">
        <div className="flex items-start gap-3">
          {/* File type badge */}
          <div className={`w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 ${ftColor}`} style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase' }}>
            {doc.file_type || 'doc'}
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-3">
              <h3
                className="text-slate-800 cursor-pointer hover:text-blue-600 transition-colors"
                style={{ fontSize: '14px', lineHeight: 1.4, fontWeight: 600 }}
                onClick={onToggle}
              >
                {doc.title || doc.source_file}
              </h3>
              <div className="flex items-center gap-1 flex-shrink-0">
                <button
                  onClick={(e) => { e.stopPropagation(); onChat(doc.source_file); }}
                  title="Chat about this document"
                  className="p-1.5 rounded-lg hover:bg-blue-50 text-slate-400 hover:text-blue-600 transition-colors"
                >
                  <MessageSquare className="w-4 h-4" />
                </button>
                <button
                  onClick={handleDelete}
                  disabled={deleting}
                  title="Remove from index"
                  className="p-1.5 rounded-lg hover:bg-red-50 text-slate-400 hover:text-red-500 transition-colors disabled:opacity-40"
                >
                  {deleting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {doc.source_file !== doc.title && doc.title && (
              <p className="text-slate-400 mt-0.5 truncate" style={{ fontSize: '12px' }}>{doc.source_file}</p>
            )}

            {doc.authors && (
              <p className="text-slate-500 mt-1 flex items-center gap-1.5" style={{ fontSize: '12px' }}>
                <Users className="w-3.5 h-3.5 flex-shrink-0 text-slate-400" />
                <span className="truncate">{doc.authors}</span>
              </p>
            )}

            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-2">
              {doc.published && (
                <span className="flex items-center gap-1 text-slate-400" style={{ fontSize: '12px' }}>
                  <Calendar className="w-3.5 h-3.5" />
                  {doc.published}
                </span>
              )}
              <span className="flex items-center gap-1 text-slate-400" style={{ fontSize: '12px' }}>
                <Hash className="w-3.5 h-3.5" />
                {doc.chunk_count} chunks indexed
              </span>
              {doc.doi && (
                <a
                  href={`https://doi.org/${doc.doi}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={(e) => e.stopPropagation()}
                  className="flex items-center gap-1 text-blue-600 hover:text-blue-700"
                  style={{ fontSize: '12px' }}
                >
                  <ExternalLink className="w-3 h-3" />
                  DOI
                </a>
              )}
              <button
                onClick={onToggle}
                className="text-blue-600 hover:text-blue-700 ml-auto"
                style={{ fontSize: '12px' }}
              >
                {expanded ? 'Hide summary ↑' : 'Show summary ↓'}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Expanded summary */}
      {expanded && doc.summary && (
        <div className="px-5 pb-5 border-t border-slate-100 pt-4 bg-slate-50">
          <h4 className="text-slate-600 mb-2" style={{ fontSize: '11px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>AI Summary</h4>
          <p className="text-slate-600" style={{ fontSize: '13px', lineHeight: 1.7 }}>{doc.summary}</p>
        </div>
      )}
    </div>
  );
}

const FILE_TYPES = ['All Types', 'pdf', 'docx', 'txt', 'xlsx', 'json'];

export function DocumentLibrary() {
  const navigate = useNavigate();
  const [docs, setDocs] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [fileType, setFileType] = useState('All Types');
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const fetchDocs = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/documents`);
      if (!res.ok) throw new Error(`Failed to load documents: ${res.status}`);
      const data = await res.json();
      setDocs(data.documents);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchDocs(); }, [fetchDocs]);

  const handleDelete = (sf: string) => {
    setDocs((prev) => prev.filter((d) => d.source_file !== sf));
  };

  const handleChat = (sf: string) => {
    navigate(`/chat?q=${encodeURIComponent(`Tell me about the document: ${sf}`)}`);
  };

  const filtered = docs.filter((d) => {
    const q = search.toLowerCase();
    const matchSearch = !q
      || d.title.toLowerCase().includes(q)
      || d.source_file.toLowerCase().includes(q)
      || d.authors.toLowerCase().includes(q)
      || d.summary.toLowerCase().includes(q);
    const matchType = fileType === 'All Types' || d.file_type === fileType;
    return matchSearch && matchType;
  });

  const totalChunks = docs.reduce((s, d) => s + d.chunk_count, 0);
  const level1Docs = docs.filter((d) => d.doi).length;

  return (
    <div className="p-6 max-w-[1200px] mx-auto">
      <div className="mb-6">
        <h1 className="text-slate-900">Document Library</h1>
        <p className="text-slate-500 mt-1" style={{ fontSize: '14px' }}>
          Browse and manage all documents indexed in your RAG knowledge base.
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-5">
        {[
          { label: 'Total Documents', value: docs.length, icon: FileText, color: 'text-blue-600' },
          { label: 'With DOI', value: level1Docs, icon: ExternalLink, color: 'text-emerald-600' },
          { label: 'Total Chunks', value: totalChunks.toLocaleString(), icon: Hash, color: 'text-violet-600' },
          { label: 'Avg Chunks', value: docs.length ? Math.round(totalChunks / docs.length) : 0, icon: BookOpen, color: 'text-amber-600' },
        ].map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="bg-white rounded-xl border border-slate-200 p-4">
            <div className={`w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center mb-2 ${color}`}>
              <Icon className="w-4 h-4" />
            </div>
            <p className="text-slate-800" style={{ fontSize: '20px', fontWeight: 700 }}>{value}</p>
            <p className="text-slate-400 mt-0.5" style={{ fontSize: '12px' }}>{label}</p>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl border border-slate-200 p-4 mb-4">
        <div className="flex flex-wrap gap-3">
          <div className="flex-1 min-w-52 flex items-center gap-2 bg-slate-50 rounded-lg px-3 py-2 border border-slate-200">
            <Search className="w-4 h-4 text-slate-400 flex-shrink-0" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by title, author, or content..."
              className="flex-1 bg-transparent text-slate-700 placeholder-slate-400 outline-none"
              style={{ fontSize: '13px' }}
            />
          </div>

          <div className="relative">
            <select
              value={fileType}
              onChange={(e) => setFileType(e.target.value)}
              className="bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-slate-700 outline-none appearance-none pr-8 cursor-pointer"
              style={{ fontSize: '13px' }}
            >
              {FILE_TYPES.map((t) => <option key={t} value={t}>{t === 'All Types' ? 'All File Types' : t.toUpperCase()}</option>)}
            </select>
            <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
          </div>

          <button
            onClick={fetchDocs}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-2 border border-slate-200 rounded-lg text-slate-600 hover:bg-slate-50 transition-colors"
            style={{ fontSize: '13px' }}
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>

          <button
            onClick={() => navigate('/upload')}
            className="flex items-center gap-2 px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors ml-auto"
            style={{ fontSize: '13px', fontWeight: 500 }}
          >
            <Upload className="w-4 h-4" />
            Upload Document
          </button>
        </div>
      </div>

      {/* Content */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="text-center">
            <Loader2 className="w-10 h-10 text-blue-500 animate-spin mx-auto mb-3" />
            <p className="text-slate-500" style={{ fontSize: '14px' }}>Loading document library...</p>
          </div>
        </div>
      ) : error ? (
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-red-700" style={{ fontSize: '14px', fontWeight: 600 }}>Failed to load documents</p>
            <p className="text-red-600 mt-1" style={{ fontSize: '13px' }}>{error}</p>
            <button onClick={fetchDocs} className="mt-3 px-3 py-1.5 bg-red-600 text-white rounded-lg text-sm hover:bg-red-700">
              Retry
            </button>
          </div>
        </div>
      ) : filtered.length === 0 ? (
        <div className="bg-white rounded-xl border border-slate-200 text-center py-16">
          <BookOpen className="w-12 h-12 text-slate-300 mx-auto mb-3" />
          <p className="text-slate-600" style={{ fontSize: '15px', fontWeight: 500 }}>
            {docs.length === 0 ? 'No documents indexed yet' : 'No documents match your search'}
          </p>
          <p className="text-slate-400 mt-1 mb-4" style={{ fontSize: '13px' }}>
            {docs.length === 0
              ? 'Upload PDF, DOCX, or TXT files to get started.'
              : 'Try adjusting your search or filters.'}
          </p>
          {docs.length === 0 && (
            <button
              onClick={() => navigate('/upload')}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm"
            >
              Upload Your First Document
            </button>
          )}
        </div>
      ) : (
        <div className="space-y-3">
          <p className="text-slate-500" style={{ fontSize: '13px' }}>
            Showing {filtered.length} of {docs.length} document{docs.length !== 1 ? 's' : ''}
          </p>
          {filtered.map((doc) => (
            <DocCard
              key={doc.source_file}
              doc={doc}
              onDelete={handleDelete}
              onChat={handleChat}
              expanded={expandedId === doc.source_file}
              onToggle={() => setExpandedId(expandedId === doc.source_file ? null : doc.source_file)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
