import { useState, useRef } from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from './ui/card';
import { Button } from './ui/button';
import { Label } from './ui/label';
import { Input } from './ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Badge } from './ui/badge';
import { Upload, X, FileText } from 'lucide-react';
import { KnowledgeCategory } from '../types/knowledge';

interface FileUploadZoneProps {
  category: KnowledgeCategory;
  onUpload: (files: File[], subcategory: string, tags: string[]) => void;
}

export function FileUploadZone({ category, onUpload }: FileUploadZoneProps) {
  const [selectedSubcategory, setSelectedSubcategory] = useState<string>('');
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [tags, setTags] = useState<string>('');
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = (files: FileList | null) => {
    if (files) {
      setSelectedFiles(prev => [...prev, ...Array.from(files)]);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    handleFileSelect(e.dataTransfer.files);
  };

  const removeFile = (index: number) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const handleUpload = () => {
    if (selectedFiles.length > 0 && selectedSubcategory) {
      const tagArray = tags.split(',').map(t => t.trim()).filter(t => t);
      onUpload(selectedFiles, selectedSubcategory, tagArray);
      setSelectedFiles([]);
      setTags('');
      setSelectedSubcategory('');
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <span className="text-2xl">{category.icon}</span>
          <div>
            <CardTitle>{category.name}</CardTitle>
            <CardDescription>{category.description}</CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor={`subcategory-${category.id}`}>Document Type</Label>
          <Select value={selectedSubcategory} onValueChange={setSelectedSubcategory}>
            <SelectTrigger id={`subcategory-${category.id}`}>
              <SelectValue placeholder="Select document type..." />
            </SelectTrigger>
            <SelectContent>
              {category.subcategories.map(sub => (
                <SelectItem key={sub.id} value={sub.id}>
                  {sub.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {selectedSubcategory && (
            <p className="text-xs text-muted-foreground">
              {category.subcategories.find(s => s.id === selectedSubcategory)?.description}
            </p>
          )}
        </div>

        <div
          className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
            isDragging ? 'border-primary bg-primary/5' : 'border-muted'
          }`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          <Upload className="h-10 w-10 mx-auto mb-4 text-muted-foreground" />
          <p className="text-sm mb-2">Drag and drop files here, or</p>
          <Button
            variant="outline"
            onClick={() => fileInputRef.current?.click()}
            type="button"
          >
            Browse Files
          </Button>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            className="hidden"
            onChange={(e) => handleFileSelect(e.target.files)}
            accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.csv"
          />
          <p className="text-xs text-muted-foreground mt-2">
            Supported: PDF, Word, Excel, PowerPoint, Text, CSV
          </p>
        </div>

        {selectedFiles.length > 0 && (
          <div className="space-y-2">
            <Label>Selected Files ({selectedFiles.length})</Label>
            <div className="space-y-2 max-h-40 overflow-y-auto">
              {selectedFiles.map((file, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between p-2 bg-muted rounded-lg"
                >
                  <div className="flex items-center gap-2 flex-1 min-w-0">
                    <FileText className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                    <span className="text-sm truncate">{file.name}</span>
                    <span className="text-xs text-muted-foreground flex-shrink-0">
                      {formatFileSize(file.size)}
                    </span>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => removeFile(index)}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="space-y-2">
          <Label htmlFor={`tags-${category.id}`}>Tags (optional)</Label>
          <Input
            id={`tags-${category.id}`}
            placeholder="Enter tags separated by commas"
            value={tags}
            onChange={(e) => setTags(e.target.value)}
          />
          {tags && (
            <div className="flex flex-wrap gap-1">
              {tags.split(',').map((tag, i) => (
                tag.trim() && <Badge key={i} variant="secondary">{tag.trim()}</Badge>
              ))}
            </div>
          )}
        </div>

        <Button
          onClick={handleUpload}
          disabled={selectedFiles.length === 0 || !selectedSubcategory}
          className="w-full"
        >
          <Upload className="h-4 w-4 mr-2" />
          Upload {selectedFiles.length > 0 ? `${selectedFiles.length} File${selectedFiles.length > 1 ? 's' : ''}` : 'Files'}
        </Button>
      </CardContent>
    </Card>
  );
}
