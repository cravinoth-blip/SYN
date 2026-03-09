import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router';
import { API_BASE } from '../../lib/api';
import {
  MessageSquare, BookOpen, Upload, Activity,
  CheckCircle2, AlertCircle, ChevronRight, TrendingUp,
  Database, FileText, Cpu, Search,
} from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';

interface StatusData {
  status: 'ok' | 'error';
  chunks?: number;
  collection?: string;
  error?: string;
}

const EXAMPLE_QUERIES = [
  'What is the stroke incidence rate in Europe?',
  'Summarize the evidence on Factor XIa inhibitors for stroke prevention.',
  'What are the key findings from recent MACE outcome trials?',
  'Compare anticoagulation strategies in atrial fibrillation patients.',
];

const USAGE_DATA = [
  { day: 'Mon', queries: 12 },
  { day: 'Tue', queries: 18 },
  { day: 'Wed', queries: 15 },
  { day: 'Thu', queries: 22 },
  { day: 'Fri', queries: 19 },
  { day: 'Sat', queries: 8 },
  { day: 'Sun', queries: 6 },
];

export function Dashboard() {
  const navigate = useNavigate();
  const [status, setStatus] = useState<StatusData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_BASE}/status`)
      .then((r) => r.json())
      .then((d) => { setStatus(d); setLoading(false); })
      .catch(() => { setStatus({ status: 'error', error: 'Backend unreachable' }); setLoading(false); });
  }, []);

  const isOk = status?.status === 'ok';

  const stats = [
    {
      label: 'Indexed Chunks',
      value: loading ? '...' : (status?.chunks?.toLocaleString() ?? '—'),
      change: 'Vector embeddings stored',
      positive: true,
      icon: Database,
      color: 'bg-blue-500',
    },
    {
      label: 'Backend Status',
      value: loading ? '...' : (isOk ? 'Online' : 'Offline'),
      change: loading ? 'Checking...' : (isOk ? 'All systems operational' : status?.error ?? 'Connection failed'),
      positive: isOk,
      icon: isOk ? CheckCircle2 : AlertCircle,
      color: isOk ? 'bg-emerald-500' : 'bg-red-500',
    },
    {
      label: 'Collection',
      value: loading ? '...' : (status?.collection ?? '—'),
      change: 'ChromaDB collection name',
      positive: true,
      icon: Cpu,
      color: 'bg-violet-500',
    },
    {
      label: 'Document Types',
      value: 'PDF · DOCX · TXT',
      change: 'Supported upload formats',
      positive: true,
      icon: FileText,
      color: 'bg-amber-500',
    },
  ];

  return (
    <div className="p-6 max-w-[1400px] mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-slate-900">Welcome back</h1>
          <p className="text-slate-500 mt-0.5" style={{ fontSize: '14px' }}>
            Your RAG research assistant is ready. Ask questions about your document library.
          </p>
        </div>
        <button
          onClick={() => navigate('/chat')}
          className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex-shrink-0"
          style={{ fontSize: '14px', fontWeight: 500 }}
        >
          <MessageSquare className="w-4 h-4" />
          Start Chatting
        </button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <div key={stat.label} className="bg-white rounded-xl border border-slate-200 p-5">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-slate-500" style={{ fontSize: '13px' }}>{stat.label}</p>
                  <p className="text-slate-900 mt-1" style={{ fontSize: '22px', fontWeight: 700, lineHeight: 1.2 }}>{stat.value}</p>
                </div>
                <div className={`w-10 h-10 rounded-lg ${stat.color} flex items-center justify-center flex-shrink-0`}>
                  <Icon className="w-5 h-5 text-white" />
                </div>
              </div>
              <p className={`mt-3 flex items-center gap-1 ${stat.positive ? 'text-emerald-600' : 'text-red-500'}`} style={{ fontSize: '12px' }}>
                <TrendingUp className="w-3.5 h-3.5" />
                {stat.change}
              </p>
            </div>
          );
        })}
      </div>

      {/* Main content row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Usage chart */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-slate-800">Query Activity</h3>
              <p className="text-slate-400 mt-0.5" style={{ fontSize: '12px' }}>Queries this week (demo)</p>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={USAGE_DATA} barCategoryGap="40%">
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
              <XAxis dataKey="day" tick={{ fontSize: 12, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 12, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ borderRadius: 8, border: '1px solid #e2e8f0', fontSize: 12 }} cursor={{ fill: '#f8fafc' }} />
              <Bar dataKey="queries" fill="#3b82f6" radius={[4, 4, 0, 0]} name="Queries" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Quick actions + example queries */}
        <div className="bg-white rounded-xl border border-slate-200">
          <div className="px-5 py-4 border-b border-slate-100">
            <h3 className="text-slate-800">Quick Actions</h3>
            <p className="text-slate-400 mt-0.5" style={{ fontSize: '12px' }}>Jump right in</p>
          </div>
          <div className="p-4 space-y-2">
            {[
              { label: 'Start a new chat', icon: MessageSquare, path: '/chat', color: 'bg-blue-50 text-blue-700 hover:bg-blue-100' },
              { label: 'Browse documents', icon: BookOpen, path: '/documents', color: 'bg-violet-50 text-violet-700 hover:bg-violet-100' },
              { label: 'Upload new documents', icon: Upload, path: '/upload', color: 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100' },
            ].map(({ label, icon: Icon, path, color }) => (
              <button
                key={label}
                onClick={() => navigate(path)}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${color}`}
                style={{ fontSize: '13px', fontWeight: 500 }}
              >
                <Icon className="w-4 h-4 flex-shrink-0" />
                {label}
                <ChevronRight className="w-3.5 h-3.5 ml-auto" />
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Example queries */}
      <div className="bg-white rounded-xl border border-slate-200">
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100">
          <h3 className="text-slate-800">Example Research Queries</h3>
          <button
            onClick={() => navigate('/chat')}
            className="flex items-center gap-1 text-blue-600 hover:text-blue-700 transition-colors"
            style={{ fontSize: '13px', fontWeight: 500 }}
          >
            Open Chat <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>
        <div className="divide-y divide-slate-50">
          {EXAMPLE_QUERIES.map((q) => (
            <div
              key={q}
              className="px-5 py-3.5 hover:bg-slate-50 cursor-pointer transition-colors flex items-center gap-3"
              onClick={() => navigate(`/chat?q=${encodeURIComponent(q)}`)}
            >
              <Search className="w-4 h-4 text-slate-400 flex-shrink-0" />
              <p className="text-slate-700 flex-1" style={{ fontSize: '13px' }}>{q}</p>
              <ChevronRight className="w-4 h-4 text-slate-300 flex-shrink-0" />
            </div>
          ))}
        </div>
      </div>

      {/* How it works */}
      <div className="bg-blue-50 border border-blue-100 rounded-xl p-5">
        <div className="flex items-start gap-3">
          <div className="w-8 h-8 rounded-lg bg-blue-100 flex items-center justify-center flex-shrink-0 mt-0.5">
            <Activity className="w-4 h-4 text-blue-600" />
          </div>
          <div>
            <p className="text-blue-800" style={{ fontSize: '14px', fontWeight: 600 }}>How it works</p>
            <p className="text-blue-600 mt-1" style={{ fontSize: '13px', lineHeight: 1.6 }}>
              Type a question in the Chat. The system embeds your query using OpenAI <code className="bg-blue-100 px-1 rounded text-xs">text-embedding-3-small</code>, retrieves the most relevant document chunks from ChromaDB via cosine similarity, then generates a grounded answer with GPT-4o-mini citing specific sources.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
