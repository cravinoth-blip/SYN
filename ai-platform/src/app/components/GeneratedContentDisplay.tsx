import { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from './ui/card';
import { Button } from './ui/button';
import { Textarea } from './ui/textarea';
import { Copy, Download, RefreshCw, Loader2, ChevronDown, ChevronUp, BookOpen } from 'lucide-react';
import { toast } from 'sonner';

interface GeneratedContentDisplayProps {
  content: Record<string, string>;
  activeSection: string | null;
  onSectionSelect: (key: string) => void;
}

export function GeneratedContentDisplay({ content: initialContent, activeSection, onSectionSelect }: GeneratedContentDisplayProps) {
  const [content, setContent] = useState(initialContent);
  const [expandedSection, setExpandedSection] = useState<string | null>(null);
  const [contextInputs, setContextInputs] = useState<Record<string, string>>({});
  const [regeneratingSection, setRegeneratingSection] = useState<string | null>(null);

  const handleCopy = () => {
    const text = Object.entries(content)
      .map(([key, value]) => `${key.toUpperCase()}\n${value}`)
      .join('\n\n---\n\n');
    navigator.clipboard.writeText(text);
    toast.success('Content copied to clipboard!');
  };

  const handleDownload = () => {
    const text = Object.entries(content)
      .map(([key, value]) => `${key.toUpperCase()}\n${value}`)
      .join('\n\n---\n\n');
    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `generated-content-${Date.now()}.txt`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success('Content downloaded!');
  };

  const handleToggleSection = (key: string) => {
    setExpandedSection(prev => (prev === key ? null : key));
  };

  const handleRegenerateSection = async (key: string) => {
    setRegeneratingSection(key);
    const additionalContext = contextInputs[key]?.trim() || '';

    // Simulate AI regeneration delay
    await new Promise(resolve => setTimeout(resolve, 1400));

    setContent(prev => {
      const existing = prev[key];
      const contextNote = additionalContext
        ? `${existing}\n\nRefined Perspective (based on: "${additionalContext}"):\n${existing
            .split('\n')
            .slice(0, 4)
            .join('\n')
            .replace(/^•/gm, '→')}`
        : existing
            .split('\n')
            .map(line => line.replace(/^•\s/, '→ '))
            .join('\n');
      return { ...prev, [key]: contextNote };
    });

    setRegeneratingSection(null);
    setExpandedSection(null);
    setContextInputs(prev => ({ ...prev, [key]: '' }));
    toast.success('Section regenerated!');
  };

  const formatLabel = (key: string) =>
    key.replace(/([A-Z])/g, ' $1').trim();

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Generated Content</CardTitle>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={handleCopy}>
              <Copy className="h-4 w-4 mr-2" />
              Copy
            </Button>
            <Button variant="outline" size="sm" onClick={handleDownload}>
              <Download className="h-4 w-4 mr-2" />
              Download
            </Button>
          </div>
        </div>
        <p className="text-xs text-muted-foreground mt-1">Click any section to load its references</p>
      </CardHeader>
      <CardContent className="space-y-4">
        {Object.entries(content).map(([key, value]) => {
          const isExpanded = expandedSection === key;
          const isRegenerating = regeneratingSection === key;
          const isActive = activeSection === key;

          return (
            <div
              key={key}
              className={`rounded-lg border overflow-hidden transition-all duration-200 ${
                isActive
                  ? 'border-primary/50 shadow-sm ring-1 ring-primary/20'
                  : 'border-border hover:border-muted-foreground/30'
              }`}
            >
              {/* Section header — clickable to select */}
              <div
                className={`flex items-center justify-between px-4 py-2 cursor-pointer transition-colors select-none ${
                  isActive
                    ? 'bg-primary/8 border-l-[3px] border-l-primary'
                    : 'bg-muted/40 hover:bg-muted/60 border-l-[3px] border-l-transparent'
                }`}
                onClick={() => onSectionSelect(key)}
              >
                <div className="flex items-center gap-2 min-w-0">
                  <h4 className={`font-semibold text-sm uppercase tracking-wide truncate transition-colors ${
                    isActive ? 'text-primary' : 'text-muted-foreground'
                  }`}>
                    {formatLabel(key)}
                  </h4>
                  {isActive && (
                    <span className="flex items-center gap-1 text-xs text-primary shrink-0 bg-primary/10 px-1.5 py-0.5 rounded-full">
                      <BookOpen className="h-2.5 w-2.5" />
                      References active
                    </span>
                  )}
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 px-2 text-muted-foreground hover:text-foreground gap-1.5 shrink-0 ml-2"
                  onClick={e => { e.stopPropagation(); handleToggleSection(key); }}
                  disabled={isRegenerating}
                >
                  <RefreshCw className="h-3.5 w-3.5" />
                  <span className="text-xs">Regenerate</span>
                  {isExpanded
                    ? <ChevronUp className="h-3.5 w-3.5" />
                    : <ChevronDown className="h-3.5 w-3.5" />}
                </Button>
              </div>

              {/* Section content */}
              <div className="px-4 py-3 bg-background">
                {isRegenerating ? (
                  <div className="flex items-center gap-2 py-2 text-muted-foreground">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span className="text-sm">Regenerating section…</span>
                  </div>
                ) : (
                  <p className="whitespace-pre-wrap text-sm">{value}</p>
                )}
              </div>

              {/* Regenerate panel */}
              {isExpanded && !isRegenerating && (
                <div className="px-4 pb-4 pt-1 border-t border-border bg-muted/20 space-y-3">
                  <p className="text-xs text-muted-foreground">
                    Add context or instructions to guide how this section is rewritten.
                  </p>
                  <Textarea
                    placeholder={`e.g. "Focus more on payer perspective" or "Make it more concise and data-driven"`}
                    value={contextInputs[key] || ''}
                    onChange={e =>
                      setContextInputs(prev => ({ ...prev, [key]: e.target.value }))
                    }
                    rows={3}
                    className="text-sm resize-none"
                  />
                  <div className="flex justify-end gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setExpandedSection(null)}
                    >
                      Cancel
                    </Button>
                    <Button
                      size="sm"
                      onClick={() => handleRegenerateSection(key)}
                    >
                      <RefreshCw className="h-3.5 w-3.5 mr-1.5" />
                      Regenerate Section
                    </Button>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}