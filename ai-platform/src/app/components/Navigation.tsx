import { useNavigate, useLocation } from 'react-router';
import { Button } from './ui/button';
import { Sparkles, Database, GitCompare } from 'lucide-react';

export function Navigation() {
  const navigate = useNavigate();
  const location = useLocation();

  const isGeneratorActive = location.pathname === '/' || location.pathname.startsWith('/generate');
  const isKnowledgeActive = location.pathname.startsWith('/knowledge');
  const isPptxActive = location.pathname.startsWith('/pptx-compare');

  return (
    <div className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 sticky top-0 z-50">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center gap-2">
            <Sparkles className="h-6 w-6 text-primary" />
            <span className="text-xl">AI Content Platform - Powered by SYN10X</span>
          </div>
          
          <nav className="flex gap-2">
            <Button
              variant={isGeneratorActive ? 'default' : 'ghost'}
              onClick={() => navigate('/')}
            >
              <Sparkles className="h-4 w-4 mr-2" />
              Content Generator
            </Button>
            <Button
              variant={isKnowledgeActive ? 'default' : 'ghost'}
              onClick={() => navigate('/knowledge')}
            >
              <Database className="h-4 w-4 mr-2" />
              Knowledge Base
            </Button>
            <Button
              variant={isPptxActive ? 'default' : 'ghost'}
              onClick={() => navigate('/pptx-compare')}
            >
              <GitCompare className="h-4 w-4 mr-2" />
              PPTX Comparator
            </Button>
          </nav>
        </div>
      </div>
    </div>
  );
}