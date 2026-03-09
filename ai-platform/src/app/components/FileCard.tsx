import { KnowledgeFile } from '../types/knowledge';
import { Card, CardHeader, CardTitle, CardContent } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { FileText, Download, Trash2, Calendar } from 'lucide-react';

interface FileCardProps {
  file: KnowledgeFile;
  onDelete: (fileId: string) => void;
}

export function FileCard({ file, onDelete }: FileCardProps) {
  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  const formatDate = (timestamp: number): string => {
    return new Date(timestamp).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
  };

  const handleDownload = () => {
    const url = URL.createObjectURL(file.file);
    const a = document.createElement('a');
    a.href = url;
    a.download = file.name;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardContent className="pt-6">
        <div className="flex items-start gap-4">
          <div className="bg-primary/10 p-3 rounded-lg">
            <FileText className="h-6 w-6 text-primary" />
          </div>
          
          <div className="flex-1 min-w-0">
            <h4 className="font-medium truncate mb-1">{file.name}</h4>
            
            <div className="flex flex-wrap gap-2 mb-2">
              <Badge variant="outline" className="text-xs">
                {file.subcategory.replace(/-/g, ' ')}
              </Badge>
              {file.tags?.map(tag => (
                <Badge key={tag} variant="secondary" className="text-xs">
                  {tag}
                </Badge>
              ))}
            </div>
            
            <div className="flex items-center gap-4 text-xs text-muted-foreground">
              <span>{formatFileSize(file.size)}</span>
              <span className="flex items-center gap-1">
                <Calendar className="h-3 w-3" />
                {formatDate(file.uploadedAt)}
              </span>
            </div>
          </div>

          <div className="flex gap-1">
            <Button
              variant="ghost"
              size="sm"
              onClick={handleDownload}
              title="Download"
            >
              <Download className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onDelete(file.id)}
              title="Delete"
            >
              <Trash2 className="h-4 w-4 text-destructive" />
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
