import { Template } from '../types/template';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { ArrowRight } from 'lucide-react';

interface TemplateCardProps {
  template: Template;
  onSelect: (templateId: string) => void;
}

export function TemplateCard({ template, onSelect }: TemplateCardProps) {
  const getCategoryLabel = (category: string) => {
    return category === 'tools' ? 'Strategic Tool' : 'Deliverable';
  };

  return (
    <Card className="hover:shadow-lg transition-shadow cursor-pointer group">
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="text-4xl mb-2">{template.icon}</div>
          <Badge variant="secondary">{getCategoryLabel(template.category)}</Badge>
        </div>
        <CardTitle>{template.name}</CardTitle>
        <CardDescription>{template.description}</CardDescription>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground mb-4">{template.preview}</p>
        <Button 
          onClick={() => onSelect(template.id)} 
          className="w-full group-hover:bg-primary group-hover:text-primary-foreground"
          variant="outline"
        >
          Use Framework
          <ArrowRight className="ml-2 h-4 w-4" />
        </Button>
      </CardContent>
    </Card>
  );
}