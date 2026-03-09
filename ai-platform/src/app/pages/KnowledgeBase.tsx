import { useState } from 'react';
import { useParams, useNavigate } from 'react-router';
import { KnowledgeFile } from '../types/knowledge';
import { knowledgeCategories } from '../data/knowledgeCategories';
import { compounds } from '../data/compounds';
import { FileUploadZone } from '../components/FileUploadZone';
import { FileCard } from '../components/FileCard';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Card, CardContent } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Database, Search, FolderOpen, ArrowLeft, Pill } from 'lucide-react';
import { toast } from 'sonner';

export default function KnowledgeBase() {
  const { compoundId } = useParams<{ compoundId: string }>();
  const navigate = useNavigate();
  const [files, setFiles] = useState<KnowledgeFile[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeTab, setActiveTab] = useState<'internal' | 'external' | 'systems'>('internal');
  const [subcategoryFilter, setSubcategoryFilter] = useState<string>('all');

  const compound = compounds.find(c => c.id === compoundId);

  if (!compound) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-background to-muted/20">
        <div className="container mx-auto px-4 py-8">
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-12">
              <p className="text-muted-foreground">Compound not found</p>
              <Button onClick={() => navigate('/knowledge')} className="mt-4">
                Back to Compound Selection
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  const handleUpload = (uploadedFiles: File[], subcategory: string, tags: string[]) => {
    const newFiles: KnowledgeFile[] = uploadedFiles.map(file => ({
      id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      name: file.name,
      category: activeTab,
      subcategory,
      compoundId: compoundId!,
      size: file.size,
      uploadedAt: Date.now(),
      file,
      tags: tags.length > 0 ? tags : undefined
    }));

    setFiles(prev => [...newFiles, ...prev]);
    toast.success(`${uploadedFiles.length} file${uploadedFiles.length > 1 ? 's' : ''} uploaded successfully!`);
  };

  const handleDelete = (fileId: string) => {
    setFiles(prev => prev.filter(f => f.id !== fileId));
    toast.success('File deleted');
  };

  const filteredFiles = files.filter(file => {
    const matchesCategory = file.category === activeTab;
    const matchesSubcategory = subcategoryFilter === 'all' || file.subcategory === subcategoryFilter;
    const matchesSearch = 
      file.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      file.tags?.some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase()));
    
    return matchesCategory && matchesSubcategory && matchesSearch;
  });

  const activeCategory = knowledgeCategories.find(c => c.id === activeTab);
  const fileCount = files.filter(f => f.category === activeTab).length;

  const getStageColor = (stage: string): string => {
    switch (stage) {
      case 'Discovery':
      case 'Preclinical':
        return 'bg-blue-500/10 text-blue-500 border-blue-500/20';
      case 'Phase I':
      case 'Phase II':
        return 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20';
      case 'Phase III':
        return 'bg-orange-500/10 text-orange-500 border-orange-500/20';
      case 'Approved':
      case 'Marketed':
        return 'bg-green-500/10 text-green-500 border-green-500/20';
      default:
        return 'bg-gray-500/10 text-gray-500 border-gray-500/20';
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-background to-muted/20">
      <div className="container mx-auto px-4 py-8">
        <Button
          variant="ghost"
          onClick={() => navigate('/knowledge')}
          className="mb-6"
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Compound Selection
        </Button>

        <div className="mb-8">
          <div className="flex items-start justify-between mb-4">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <Pill className="h-8 w-8 text-primary" />
                <h1 className="text-4xl">{compound.name}</h1>
              </div>
              <p className="text-lg text-muted-foreground mb-2">{compound.genericName}</p>
              <div className="flex flex-wrap gap-2 mb-2">
                <Badge variant="outline" className={getStageColor(compound.stage)}>
                  {compound.stage}
                </Badge>
                <Badge variant="secondary">{compound.therapeuticArea}</Badge>
              </div>
              <p className="text-sm">
                <span className="font-medium">Indication:</span> {compound.indication}
              </p>
            </div>
          </div>
          <p className="text-muted-foreground">{compound.description}</p>
        </div>

        <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as any)} className="space-y-6">
          <TabsList className="grid w-full grid-cols-3">
            {knowledgeCategories.map(category => (
              <TabsTrigger key={category.id} value={category.id} className="gap-2">
                <span>{category.icon}</span>
                {category.name}
                {files.filter(f => f.category === category.id).length > 0 && (
                  <span className="ml-1 text-xs bg-primary text-primary-foreground rounded-full px-2 py-0.5">
                    {files.filter(f => f.category === category.id).length}
                  </span>
                )}
              </TabsTrigger>
            ))}
          </TabsList>

          {knowledgeCategories.map(category => (
            <TabsContent key={category.id} value={category.id} className="space-y-6">
              <FileUploadZone category={category} onUpload={handleUpload} />

              <div>
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-2xl flex items-center gap-2">
                    <FolderOpen className="h-6 w-6" />
                    Uploaded Files
                    {fileCount > 0 && (
                      <span className="text-muted-foreground text-lg">({fileCount})</span>
                    )}
                  </h2>
                </div>

                {fileCount > 0 && (
                  <div className="mb-6 flex flex-col md:flex-row gap-4">
                    <div className="relative flex-1">
                      <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                      <Input
                        type="text"
                        placeholder="Search files by name or tag..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="pl-10"
                      />
                    </div>
                    <Select value={subcategoryFilter} onValueChange={setSubcategoryFilter}>
                      <SelectTrigger className="w-full md:w-[250px]">
                        <SelectValue placeholder="Filter by type" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All Types</SelectItem>
                        {category.subcategories.map(sub => (
                          <SelectItem key={sub.id} value={sub.id}>
                            {sub.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                )}

                {filteredFiles.length > 0 ? (
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    {filteredFiles.map(file => (
                      <FileCard key={file.id} file={file} onDelete={handleDelete} />
                    ))}
                  </div>
                ) : files.filter(f => f.category === activeTab).length > 0 ? (
                  <Card className="border-dashed">
                    <CardContent className="flex flex-col items-center justify-center py-12">
                      <Search className="h-12 w-12 text-muted-foreground mb-4" />
                      <p className="text-muted-foreground text-center">
                        No files match your search criteria
                      </p>
                    </CardContent>
                  </Card>
                ) : (
                  <Card className="border-dashed">
                    <CardContent className="flex flex-col items-center justify-center py-12">
                      <Database className="h-12 w-12 text-muted-foreground mb-4" />
                      <p className="text-muted-foreground text-center mb-2">
                        No files uploaded yet
                      </p>
                      <p className="text-sm text-muted-foreground text-center">
                        Upload your first {category.name.toLowerCase()} for {compound.name}
                      </p>
                    </CardContent>
                  </Card>
                )}
              </div>
            </TabsContent>
          ))}
        </Tabs>
      </div>
    </div>
  );
}