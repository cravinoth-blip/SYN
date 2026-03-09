import { useState } from 'react';
import { useNavigate } from 'react-router';
import { templates } from '../data/templates';
import { TemplateCard } from '../components/TemplateCard';
import { Input } from '../components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Search, Sparkles } from 'lucide-react';
import { Button } from '../components/ui/button';

export default function TemplateLibrary() {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');

  const categories = [
    { value: 'all', label: 'All Frameworks', icon: '📚' },
    { value: 'tools', label: 'Strategic Tools', icon: '🔧' },
    { value: 'deliverables', label: 'Deliverables', icon: '📄' }
  ];

  const filteredTemplates = templates.filter(template => {
    const matchesSearch = template.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         template.description.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory = categoryFilter === 'all' || template.category === categoryFilter;
    return matchesSearch && matchesCategory;
  });

  const handleSelectTemplate = (templateId: string) => {
    navigate(`/generate/${templateId}`);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-background to-muted/20">
      <div className="container mx-auto px-4 py-8">
        <div className="mb-8">
          <h1 className="text-4xl mb-2">Strategic Frameworks</h1>
          <p className="text-muted-foreground">
            Select a strategic tool or deliverable framework and let AI generate professional content
          </p>
        </div>

        <div className="mb-8 flex flex-col md:flex-row gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              type="text"
              placeholder="Search frameworks..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
          
          <div className="flex gap-2">
            {categories.map(cat => (
              <Button
                key={cat.value}
                variant={categoryFilter === cat.value ? 'default' : 'outline'}
                onClick={() => setCategoryFilter(cat.value)}
              >
                <span className="mr-2">{cat.icon}</span>
                {cat.label}
              </Button>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredTemplates.map(template => (
            <TemplateCard
              key={template.id}
              template={template}
              onSelect={handleSelectTemplate}
            />
          ))}
        </div>

        {filteredTemplates.length === 0 && (
          <div className="text-center py-12">
            <p className="text-muted-foreground">No frameworks found matching your criteria</p>
          </div>
        )}
      </div>
    </div>
  );
}