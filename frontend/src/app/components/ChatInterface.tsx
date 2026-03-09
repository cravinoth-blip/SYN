import { useState, useRef, useEffect } from 'react';
import { useSearchParams } from 'react-router';
import { API_BASE } from '../../lib/api';
import {
  Send, Loader2, BookOpen, ExternalLink, RotateCcw,
  ChevronDown, ChevronUp, Sparkles, Upload, X,
  CheckCircle2, AlertCircle, FileText, Paperclip,
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

interface Source {
  id: string;
  text: string;
  similarity: number;
  source_file: string;
  title: string;
  authors: string;
  published: string;
  doi: string;
  page_reference: string;
  summary: string;
}

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  sources?: Source[];
  timestamp: string;
}

function SourceCard({ source, index }: { source: Source; index: number }) {
  const [expanded, setExpanded] = useState(false);
  const simPct = Math.round(source.similarity * 100);
  const simColor = simPct >= 80 ? '#10b981' : simPct >= 60 ? '#3b82f6' : '#f59e0b';

  return (
    <div className="border border-slate-200 rounded-lg overflow-hidden">
      <div
        className="flex items-start gap-3 px-4 py-3 cursor-pointer hover:bg-slate-50 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div
          className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 text-white"
          style={{ fontSize: '11px', fontWeight: 700, backgroundColor: simColor }}
        >
          {index + 1}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-slate-800 font-semibold truncate" style={{ fontSize: '12px' }}>
            {source.title || source.source_file}
          </p>
          {source.authors && (
            <p className="text-slate-400 truncate mt-0.5" style={{ fontSize: '11px' }}>{source.authors}</p>
          )}
          <div className="flex items-center gap-3 mt-1">
            {source.published && (
              <span className="text-slate-400" style={{ fontSize: '11px' }}>{source.published}</span>
            )}
            {source.page_reference && (
              <span className="text-slate-400" style={{ fontSize: '11px' }}>{source.page_reference}</span>
            )}
            <div className="flex items-center gap-1 ml-auto">
              <div className="w-12 h-1 bg-slate-100 rounded-full overflow-hidden">
                <div className="h-full rounded-full" style={{ width: `${simPct}%`, backgroundColor: simColor }} />
              </div>
              <span style={{ fontSize: '11px', fontWeight: 700, color: simColor }}>{simPct}%</span>
            </div>
          </div>
        </div>
        {expanded ? <ChevronUp className="w-4 h-4 text-slate-400 flex-shrink-0 mt-0.5" /> : <ChevronDown className="w-4 h-4 text-slate-400 flex-shrink-0 mt-0.5" />}
      </div>

      {expanded && (
        <div className="px-4 pb-3 border-t border-slate-100 bg-slate-50">
          <p className="text-slate-600 mt-3" style={{ fontSize: '12px', lineHeight: 1.7 }}>
            {source.text.length > 500 ? source.text.slice(0, 500) + '…' : source.text}
          </p>
          {source.doi && (
            <div className="mt-2 flex items-center gap-2">
              <span className="text-slate-400" style={{ fontSize: '11px' }}>DOI: {source.doi}</span>
              <button className="flex items-center gap-0.5 text-blue-600 hover:text-blue-700" style={{ fontSize: '11px' }}>
                <ExternalLink className="w-3 h-3" />
                Open
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function MessageBubble({ msg }: { msg: ChatMessage }) {
  const isUser = msg.role === 'user';

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''}`}
    >
      {/* Avatar */}
      <div
        className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${isUser ? 'bg-blue-600' : 'bg-slate-700'}`}
        style={{ fontSize: '11px', fontWeight: 700, color: 'white' }}
      >
        {isUser ? 'You' : 'AI'}
      </div>

      <div className={`flex-1 max-w-[85%] ${isUser ? 'items-end' : 'items-start'} flex flex-col`}>
        {/* Bubble */}
        <div
          className={`rounded-2xl px-4 py-3 ${isUser
            ? 'bg-blue-600 text-white rounded-tr-sm'
            : 'bg-white border border-slate-200 text-slate-800 rounded-tl-sm'
          }`}
          style={{ fontSize: '14px', lineHeight: 1.6 }}
        >
          {isUser ? (
            <p>{msg.content}</p>
          ) : (
            <div
              className="prose-chat"
              dangerouslySetInnerHTML={{ __html: renderMarkdown(msg.content) }}
            />
          )}
        </div>

        {/* Sources */}
        {!isUser && msg.sources && msg.sources.length > 0 && (
          <div className="mt-3 w-full space-y-2">
            <p className="text-slate-500 flex items-center gap-1.5" style={{ fontSize: '12px', fontWeight: 600 }}>
              <BookOpen className="w-3.5 h-3.5" />
              {msg.sources.length} source{msg.sources.length !== 1 ? 's' : ''} retrieved
            </p>
            {msg.sources.map((s, i) => (
              <SourceCard key={s.id} source={s} index={i} />
            ))}
          </div>
        )}

        <p className="text-slate-400 mt-1" style={{ fontSize: '11px' }}>
          {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </p>
      </div>
    </motion.div>
  );
}

function StreamingBubble({ text }: { text: string }) {
  return (
    <div className="flex gap-3">
      <div className="w-8 h-8 rounded-lg bg-slate-700 flex items-center justify-center flex-shrink-0" style={{ fontSize: '11px', fontWeight: 700, color: 'white' }}>
        AI
      </div>
      <div className="flex-1 max-w-[85%]">
        <div className="bg-white border border-slate-200 rounded-2xl rounded-tl-sm px-4 py-3" style={{ fontSize: '14px', lineHeight: 1.6 }}>
          {text ? (
            <div className="prose-chat" dangerouslySetInnerHTML={{ __html: renderMarkdown(text) }} />
          ) : (
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
              <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
              <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// Simple markdown renderer (no dependency needed)
function renderMarkdown(text: string): string {
  return text
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    .replace(/^\- (.+)$/gm, '<li>$1</li>')
    .replace(/(<li>.*<\/li>\n?)+/g, (m) => `<ul>${m}</ul>`)
    .replace(/\n\n/g, '</p><p>')
    .replace(/\n/g, '<br/>')
    .replace(/^(.+)$/, '<p>$1</p>');
}

const EXAMPLE_QUERIES = [
  'What is the global stroke incidence rate?',
  'Summarize evidence on Factor XIa inhibitors.',
  'What are major adverse cardiovascular events (MACE) risk factors?',
  'Compare anticoagulation strategies for AF patients.',
];

const TOP_K_OPTIONS = [4, 6, 8, 12, 16];

export function ChatInterface() {
  const [searchParams] = useSearchParams();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [topK, setTopK] = useState(8);
  const [streaming, setStreaming] = useState(false);
  const [streamText, setStreamText] = useState('');
  const [streamSources, setStreamSources] = useState<Source[]>([]);
  const [showExamples, setShowExamples] = useState(false);
  const [attachedFile, setAttachedFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Load from URL param on mount
  useEffect(() => {
    const q = searchParams.get('q');
    if (q) { setInput(q); }
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages, streamText]);

  // Save history to localStorage whenever messages change
  useEffect(() => {
    if (messages.length > 0) {
      const sessions: { id: string; preview: string; messages: ChatMessage[]; ts: string }[] =
        JSON.parse(localStorage.getItem('rag_chat_history') || '[]');
      const sessionId = Date.now().toString();
      const preview = messages[0]?.content.slice(0, 80) ?? '';
      const existing = sessions.find(s => s.messages[0]?.content === messages[0]?.content);
      if (existing) {
        existing.messages = messages;
        existing.ts = new Date().toISOString();
      } else {
        sessions.unshift({ id: sessionId, preview, messages, ts: new Date().toISOString() });
      }
      localStorage.setItem('rag_chat_history', JSON.stringify(sessions.slice(0, 30)));
    }
  }, [messages]);

  const send = async (queryText?: string) => {
    const text = (queryText ?? input).trim();
    if (!text || streaming) return;

    setError(null);
    setInput('');
    setShowExamples(false);

    const userMsg: ChatMessage = { role: 'user', content: text, timestamp: new Date().toISOString() };
    setMessages((prev) => [...prev, userMsg]);
    setStreaming(true);
    setStreamText('');
    setStreamSources([]);

    const history = messages.map(m => ({ role: m.role, content: m.content }));
    abortRef.current = new AbortController();

    try {
      let response: Response;

      if (attachedFile) {
        const fd = new FormData();
        fd.append('file', attachedFile);
        fd.append('message', text);
        fd.append('history', JSON.stringify(history));
        fd.append('top_k', String(topK));
        response = await fetch(`${API_BASE}/chat/analyze`, { method: 'POST', body: fd, signal: abortRef.current.signal });
        setAttachedFile(null);
      } else {
        response = await fetch(`${API_BASE}/chat/stream`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: text, history, top_k: topK }),
          signal: abortRef.current.signal,
        });
      }

      if (!response.ok) throw new Error(`Server error: ${response.status}`);

      const reader = response.body!.getReader();
      const decoder = new TextDecoder();
      let accumulated = '';
      let currentSources: Source[] = [];

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const raw = decoder.decode(value, { stream: true });
        const lines = raw.split('\n');
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          try {
            const evt = JSON.parse(line.slice(6));
            if (evt.type === 'sources') {
              currentSources = evt.sources;
              setStreamSources(evt.sources);
            } else if (evt.type === 'chunk') {
              accumulated += evt.text;
              setStreamText(accumulated);
            } else if (evt.type === 'done') {
              const aiMsg: ChatMessage = {
                role: 'assistant',
                content: accumulated,
                sources: currentSources,
                timestamp: new Date().toISOString(),
              };
              setMessages((prev) => [...prev, aiMsg]);
              setStreamText('');
              setStreamSources([]);
              setStreaming(false);
            } else if (evt.type === 'error') {
              throw new Error(evt.message);
            }
          } catch (parseErr) {
            // skip malformed lines
          }
        }
      }
    } catch (err: unknown) {
      if ((err as Error).name !== 'AbortError') {
        setError((err as Error).message || 'An error occurred');
      }
      setStreaming(false);
      setStreamText('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  const stopStreaming = () => {
    abortRef.current?.abort();
    setStreaming(false);
    if (streamText) {
      setMessages((prev) => [...prev, {
        role: 'assistant',
        content: streamText + ' *(stopped)*',
        sources: streamSources,
        timestamp: new Date().toISOString(),
      }]);
    }
    setStreamText('');
  };

  const reset = () => {
    abortRef.current?.abort();
    setMessages([]);
    setStreamText('');
    setStreaming(false);
    setError(null);
    setAttachedFile(null);
  };

  const isEmpty = messages.length === 0 && !streaming;

  return (
    <div className="flex h-full">
      {/* Settings panel */}
      <aside className="hidden xl:flex flex-col w-64 border-r border-slate-200 bg-white flex-shrink-0">
        <div className="p-4 border-b border-slate-100">
          <h3 className="text-slate-800">Chat Settings</h3>
        </div>
        <div className="p-4 space-y-5 flex-1 overflow-y-auto">
          {/* Top-K */}
          <div>
            <label className="block text-slate-700 mb-2" style={{ fontSize: '13px', fontWeight: 600 }}>
              Sources to Retrieve
            </label>
            <div className="flex flex-wrap gap-2">
              {TOP_K_OPTIONS.map((k) => (
                <button
                  key={k}
                  onClick={() => setTopK(k)}
                  className={`px-3 py-1.5 rounded-lg border transition-all ${topK === k ? 'bg-blue-600 text-white border-blue-600' : 'bg-slate-50 text-slate-600 border-slate-200 hover:border-blue-300'}`}
                  style={{ fontSize: '13px', fontWeight: 500 }}
                >
                  {k}
                </button>
              ))}
            </div>
            <p className="text-slate-400 mt-2" style={{ fontSize: '11px' }}>
              Number of document chunks to retrieve per query.
            </p>
          </div>

          {/* File attachment */}
          <div>
            <label className="block text-slate-700 mb-2" style={{ fontSize: '13px', fontWeight: 600 }}>
              Attach Document
            </label>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,.doc,.txt,.json,.xlsx,.xls"
              className="hidden"
              onChange={(e) => setAttachedFile(e.target.files?.[0] ?? null)}
            />
            {attachedFile ? (
              <div className="flex items-center gap-2 px-3 py-2 bg-blue-50 border border-blue-200 rounded-lg">
                <FileText className="w-4 h-4 text-blue-600 flex-shrink-0" />
                <span className="text-blue-700 text-xs truncate flex-1">{attachedFile.name}</span>
                <button onClick={() => setAttachedFile(null)} className="text-blue-400 hover:text-blue-600">
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            ) : (
              <button
                onClick={() => fileInputRef.current?.click()}
                className="w-full flex items-center gap-2 px-3 py-2.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-600 hover:bg-slate-100 transition-colors"
                style={{ fontSize: '13px' }}
              >
                <Paperclip className="w-4 h-4" />
                Attach & analyze file
              </button>
            )}
            {attachedFile && (
              <p className="text-slate-400 mt-1" style={{ fontSize: '11px' }}>
                The file will be extracted and cross-referenced against the library.
              </p>
            )}
          </div>

          {/* Example queries */}
          <div>
            <label className="block text-slate-700 mb-2" style={{ fontSize: '13px', fontWeight: 600 }}>
              Example Queries
            </label>
            <div className="space-y-1.5">
              {EXAMPLE_QUERIES.map((q) => (
                <button
                  key={q}
                  onClick={() => send(q)}
                  disabled={streaming}
                  className="w-full text-left px-3 py-2 bg-slate-50 border border-slate-100 rounded-lg text-slate-600 hover:bg-blue-50 hover:border-blue-200 hover:text-blue-700 transition-colors disabled:opacity-50"
                  style={{ fontSize: '12px', lineHeight: 1.5 }}
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Reset */}
        {messages.length > 0 && (
          <div className="p-4 border-t border-slate-100">
            <button
              onClick={reset}
              className="w-full flex items-center justify-center gap-2 px-3 py-2 border border-slate-200 rounded-lg text-slate-600 hover:bg-slate-50 transition-colors"
              style={{ fontSize: '13px' }}
            >
              <RotateCcw className="w-3.5 h-3.5" />
              New conversation
            </button>
          </div>
        )}
      </aside>

      {/* Chat area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <div className="bg-white border-b border-slate-200 px-5 py-3 flex items-center justify-between flex-shrink-0">
          <div>
            <h3 className="text-slate-800">Research Chat</h3>
            <p className="text-slate-400" style={{ fontSize: '12px' }}>
              Ask questions about your document library · top-{topK} sources
            </p>
          </div>
          <div className="flex items-center gap-2">
            {attachedFile && (
              <span className="flex items-center gap-1 px-2 py-1 bg-blue-50 text-blue-700 rounded-lg border border-blue-100" style={{ fontSize: '12px' }}>
                <Paperclip className="w-3 h-3" />
                {attachedFile.name.slice(0, 20)}{attachedFile.name.length > 20 ? '…' : ''}
              </span>
            )}
            {messages.length > 0 && (
              <button
                onClick={reset}
                className="xl:hidden flex items-center gap-1.5 px-3 py-1.5 border border-slate-200 rounded-lg text-slate-600 hover:bg-slate-50"
                style={{ fontSize: '12px' }}
              >
                <RotateCcw className="w-3.5 h-3.5" />
                Reset
              </button>
            )}
          </div>
        </div>

        {/* Messages */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 lg:px-8 py-6 space-y-6">
          {/* Welcome screen */}
          {isEmpty && (
            <div className="flex flex-col items-center justify-center h-full min-h-[300px] text-center">
              <div className="w-16 h-16 rounded-2xl bg-blue-100 flex items-center justify-center mb-4">
                <Sparkles className="w-8 h-8 text-blue-600" />
              </div>
              <h3 className="text-slate-700 mb-2">Ask Anything About Your Library</h3>
              <p className="text-slate-400 max-w-md" style={{ fontSize: '14px', lineHeight: 1.7 }}>
                Type a research question below. The system retrieves the most relevant document passages and generates a grounded, cited response.
              </p>

              <div className="mt-6 flex flex-wrap gap-2 justify-center max-w-xl">
                {EXAMPLE_QUERIES.map((q) => (
                  <button
                    key={q}
                    onClick={() => send(q)}
                    className="px-3 py-2 bg-white border border-slate-200 rounded-full text-slate-600 hover:border-blue-300 hover:text-blue-700 hover:bg-blue-50 transition-all"
                    style={{ fontSize: '12px' }}
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Messages */}
          {messages.map((msg, i) => (
            <MessageBubble key={i} msg={msg} />
          ))}

          {/* Streaming */}
          <AnimatePresence>
            {streaming && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                <StreamingBubble text={streamText} />
              </motion.div>
            )}
          </AnimatePresence>

          {/* Error */}
          {error && (
            <div className="flex items-start gap-3 px-4 py-3 bg-red-50 border border-red-200 rounded-xl">
              <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-red-700" style={{ fontSize: '13px', fontWeight: 600 }}>Error</p>
                <p className="text-red-600 mt-0.5" style={{ fontSize: '13px' }}>{error}</p>
              </div>
              <button onClick={() => setError(null)} className="ml-auto text-red-400 hover:text-red-600">
                <X className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>

        {/* Input area */}
        <div className="bg-white border-t border-slate-200 p-4 flex-shrink-0">
          {/* Examples toggle (mobile) */}
          <div className="xl:hidden mb-3">
            <button
              onClick={() => setShowExamples(!showExamples)}
              className="flex items-center gap-1.5 text-blue-600 hover:text-blue-700"
              style={{ fontSize: '12px' }}
            >
              <Sparkles className="w-3.5 h-3.5" />
              {showExamples ? 'Hide examples' : 'Show examples'}
            </button>
            {showExamples && (
              <div className="mt-2 flex flex-wrap gap-2">
                {EXAMPLE_QUERIES.map((q) => (
                  <button
                    key={q}
                    onClick={() => { setInput(q); setShowExamples(false); }}
                    className="px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-600 hover:border-blue-300 text-xs"
                  >
                    {q.slice(0, 45)}{q.length > 45 ? '…' : ''}
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="flex gap-3 items-end">
            {/* File attach button (mobile) */}
            <button
              onClick={() => fileInputRef.current?.click()}
              className="xl:hidden p-2.5 border border-slate-200 rounded-lg text-slate-500 hover:bg-slate-50 flex-shrink-0"
            >
              <Paperclip className="w-4 h-4" />
            </button>

            <div className="flex-1 relative">
              <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask a research question... (Enter to send, Shift+Enter for new line)"
                rows={2}
                disabled={streaming}
                className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-slate-700 placeholder-slate-400 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100 resize-none transition-all"
                style={{ fontSize: '14px', lineHeight: 1.6 }}
              />
              <p className="absolute bottom-2 right-3 text-slate-300" style={{ fontSize: '11px' }}>
                {input.length}
              </p>
            </div>

            {streaming ? (
              <button
                onClick={stopStreaming}
                className="flex items-center gap-2 px-4 py-3 bg-red-500 text-white rounded-xl hover:bg-red-600 transition-colors flex-shrink-0"
                style={{ fontSize: '14px', fontWeight: 500 }}
              >
                <X className="w-4 h-4" />
                Stop
              </button>
            ) : (
              <button
                onClick={() => send()}
                disabled={!input.trim()}
                className="flex items-center gap-2 px-4 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed transition-all flex-shrink-0"
                style={{ fontSize: '14px', fontWeight: 500 }}
              >
                <Send className="w-4 h-4" />
                Send
              </button>
            )}
          </div>

          <p className="text-slate-400 mt-2 text-center" style={{ fontSize: '11px' }}>
            Responses are grounded in your document library via vector similarity search.
          </p>
        </div>
      </div>
    </div>
  );
}
