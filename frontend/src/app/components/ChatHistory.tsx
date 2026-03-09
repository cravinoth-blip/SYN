import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router';
import {
  MessageSquare, Trash2, Search, ChevronRight,
  Clock, BookOpen, Plus, Calendar,
} from 'lucide-react';

interface HistorySession {
  id: string;
  preview: string;
  messages: { role: string; content: string; sources?: unknown[]; timestamp: string }[];
  ts: string;
}

export function ChatHistory() {
  const navigate = useNavigate();
  const [sessions, setSessions] = useState<HistorySession[]>([]);
  const [search, setSearch] = useState('');
  const [selected, setSelected] = useState<HistorySession | null>(null);

  useEffect(() => {
    const raw = localStorage.getItem('rag_chat_history');
    if (raw) {
      try { setSessions(JSON.parse(raw)); } catch { /* ignore */ }
    }
  }, []);

  const deleteSession = (id: string) => {
    const updated = sessions.filter((s) => s.id !== id);
    setSessions(updated);
    localStorage.setItem('rag_chat_history', JSON.stringify(updated));
    if (selected?.id === id) setSelected(null);
  };

  const clearAll = () => {
    if (!window.confirm('Clear all chat history?')) return;
    setSessions([]);
    localStorage.removeItem('rag_chat_history');
    setSelected(null);
  };

  const openInChat = (session: HistorySession) => {
    const q = session.messages[0]?.content ?? '';
    navigate(`/chat?q=${encodeURIComponent(q)}`);
  };

  const filtered = sessions.filter((s) =>
    !search || s.preview.toLowerCase().includes(search.toLowerCase())
  );

  const summaryStats = {
    total: sessions.length,
    totalMessages: sessions.reduce((sum, s) => sum + s.messages.length, 0),
    withSources: sessions.filter((s) => s.messages.some((m) => (m.sources as unknown[])?.length > 0)).length,
  };

  return (
    <div className="p-6 max-w-[1200px] mx-auto">
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-slate-900">Chat History</h1>
          <p className="text-slate-500 mt-1" style={{ fontSize: '14px' }}>
            Review and revisit your previous research conversations.
          </p>
        </div>
        <button
          onClick={() => navigate('/chat')}
          className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex-shrink-0"
          style={{ fontSize: '14px', fontWeight: 500 }}
        >
          <Plus className="w-4 h-4" />
          New Chat
        </button>
      </div>

      {/* Stats pills */}
      <div className="flex flex-wrap gap-3 mb-5">
        {[
          { label: 'Conversations', value: summaryStats.total, color: 'bg-slate-100 text-slate-700' },
          { label: 'Total Messages', value: summaryStats.totalMessages, color: 'bg-blue-50 text-blue-700' },
          { label: 'With Sources', value: summaryStats.withSources, color: 'bg-violet-50 text-violet-700' },
        ].map(({ label, value, color }) => (
          <div key={label} className={`flex items-center gap-2 px-4 py-2 rounded-lg ${color}`} style={{ fontSize: '13px', fontWeight: 500 }}>
            <span style={{ fontSize: '18px', fontWeight: 700 }}>{value}</span>
            {label}
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
              placeholder="Search conversations..."
              className="flex-1 bg-transparent text-slate-700 placeholder-slate-400 outline-none"
              style={{ fontSize: '13px' }}
            />
          </div>
          {sessions.length > 0 && (
            <button
              onClick={clearAll}
              className="flex items-center gap-2 px-3 py-2 border border-red-200 rounded-lg text-red-600 hover:bg-red-50 transition-colors ml-auto"
              style={{ fontSize: '13px' }}
            >
              <Trash2 className="w-4 h-4" />
              Clear All
            </button>
          )}
        </div>
      </div>

      {sessions.length === 0 ? (
        <div className="bg-white rounded-xl border border-slate-200 text-center py-16">
          <MessageSquare className="w-12 h-12 text-slate-300 mx-auto mb-3" />
          <p className="text-slate-600" style={{ fontSize: '15px', fontWeight: 500 }}>No chat history yet</p>
          <p className="text-slate-400 mt-1 mb-4" style={{ fontSize: '13px' }}>
            Start a conversation to see it appear here.
          </p>
          <button
            onClick={() => navigate('/chat')}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm"
          >
            Start Your First Chat
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
          {/* Session list */}
          <div className="lg:col-span-2 space-y-2">
            {filtered.length === 0 ? (
              <div className="bg-white rounded-xl border border-slate-200 text-center py-10">
                <p className="text-slate-400" style={{ fontSize: '14px' }}>No conversations match your search.</p>
              </div>
            ) : (
              filtered.map((session) => (
                <div
                  key={session.id}
                  className={`bg-white rounded-xl border cursor-pointer transition-all hover:shadow-sm ${selected?.id === session.id ? 'border-blue-400 ring-2 ring-blue-100' : 'border-slate-200 hover:border-slate-300'}`}
                  onClick={() => setSelected(session)}
                >
                  <div className="p-4">
                    <div className="flex items-start gap-3">
                      <div className="w-8 h-8 rounded-lg bg-blue-100 flex items-center justify-center flex-shrink-0">
                        <MessageSquare className="w-4 h-4 text-blue-600" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-slate-700 line-clamp-2" style={{ fontSize: '13px', lineHeight: 1.5 }}>
                          {session.preview || 'Untitled conversation'}
                        </p>
                        <div className="flex items-center gap-3 mt-2">
                          <span className="flex items-center gap-1 text-slate-400" style={{ fontSize: '11px' }}>
                            <Clock className="w-3 h-3" />
                            {new Date(session.ts).toLocaleDateString()}
                          </span>
                          <span className="text-slate-400" style={{ fontSize: '11px' }}>
                            {session.messages.length} msg{session.messages.length !== 1 ? 's' : ''}
                          </span>
                        </div>
                      </div>
                      <button
                        onClick={(e) => { e.stopPropagation(); deleteSession(session.id); }}
                        className="p-1 text-slate-300 hover:text-red-400 transition-colors flex-shrink-0"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Session detail */}
          <div className="lg:col-span-3">
            {!selected ? (
              <div className="bg-white rounded-xl border border-slate-200 flex items-center justify-center h-full min-h-[300px]">
                <div className="text-center p-8">
                  <MessageSquare className="w-10 h-10 text-slate-300 mx-auto mb-3" />
                  <p className="text-slate-500" style={{ fontSize: '14px' }}>Select a conversation to preview it</p>
                </div>
              </div>
            ) : (
              <div className="bg-white rounded-xl border border-slate-200 overflow-hidden flex flex-col" style={{ maxHeight: '70vh' }}>
                <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100">
                  <div>
                    <h3 className="text-slate-800" style={{ fontSize: '14px', fontWeight: 600 }}>Conversation Preview</h3>
                    <p className="text-slate-400 mt-0.5 flex items-center gap-1.5" style={{ fontSize: '12px' }}>
                      <Calendar className="w-3.5 h-3.5" />
                      {new Date(selected.ts).toLocaleString()}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => openInChat(selected)}
                      className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                      style={{ fontSize: '12px' }}
                    >
                      <MessageSquare className="w-3.5 h-3.5" />
                      Re-open
                    </button>
                  </div>
                </div>

                <div className="flex-1 overflow-y-auto p-5 space-y-4">
                  {selected.messages.map((msg, i) => {
                    const isUser = msg.role === 'user';
                    const sources = (msg.sources as Source[] | undefined) ?? [];
                    return (
                      <div key={i} className={`flex gap-2 ${isUser ? 'flex-row-reverse' : ''}`}>
                        <div className={`w-6 h-6 rounded-md flex items-center justify-center flex-shrink-0 ${isUser ? 'bg-blue-600' : 'bg-slate-600'}`} style={{ fontSize: '9px', fontWeight: 700, color: 'white' }}>
                          {isUser ? 'U' : 'AI'}
                        </div>
                        <div className={`max-w-[80%] ${isUser ? 'items-end' : 'items-start'} flex flex-col`}>
                          <div className={`rounded-xl px-3 py-2 ${isUser ? 'bg-blue-600 text-white' : 'bg-slate-50 border border-slate-200 text-slate-700'}`} style={{ fontSize: '13px', lineHeight: 1.5 }}>
                            {msg.content.slice(0, 300)}{msg.content.length > 300 ? '…' : ''}
                          </div>
                          {!isUser && sources.length > 0 && (
                            <p className="text-slate-400 mt-1 flex items-center gap-1" style={{ fontSize: '11px' }}>
                              <BookOpen className="w-3 h-3" />
                              {sources.length} source{sources.length !== 1 ? 's' : ''}
                            </p>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// Just to satisfy TypeScript for the sources array type
interface Source { id: string }
