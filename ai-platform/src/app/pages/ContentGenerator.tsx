import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router';
import { templates } from '../data/templates';
import { GenerationParams } from '../types/template';
import { generateContent } from '../utils/aiGenerator';
import { ParameterControls } from '../components/ParameterControls';
import { GeneratedContentDisplay } from '../components/GeneratedContentDisplay';
import { ReferencesPanel } from '../components/ReferencesPanel';
import { Button } from '../components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { ArrowLeft, Sparkles, Loader2 } from 'lucide-react';
import { toast } from 'sonner';

export default function ContentGenerator() {
  const navigate = useNavigate();
  const { templateId } = useParams<{ templateId: string }>();
  const template = templates.find(t => t.id === templateId);

  const [inputs, setInputs] = useState<Record<string, string>>({});
  const [params, setParams] = useState<GenerationParams>({
    tone: 'professional',
    length: 'medium',
    style: 'informative'
  });
  const [generatedContent, setGeneratedContent] = useState<Record<string, string> | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [activeSection, setActiveSection] = useState<string | null>(null);

  useEffect(() => {
    if (!template) {
      navigate('/');
    }
  }, [template, navigate]);

  if (!template) {
    return null;
  }

  const handleInputChange = (fieldId: string, value: string) => {
    setInputs(prev => ({ ...prev, [fieldId]: value }));
  };

  const handleGenerate = async () => {
    // Validate inputs
    const missingFields = template.fields.filter(field => !inputs[field.id]);
    if (missingFields.length > 0) {
      toast.error('Please fill in all required fields');
      return;
    }

    setIsGenerating(true);
    try {
      const content = await generateContent(template.id, inputs, params);
      setGeneratedContent(content);
      toast.success('Content generated successfully!');
    } catch (error) {
      toast.error('Failed to generate content');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleRegenerate = () => {
    setGeneratedContent(null);
    setActiveSection(null);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-background to-muted/20">
      <div className="container mx-auto px-4 py-8">
        <Button
          variant="ghost"
          onClick={() => navigate('/')}
          className="mb-6"
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Library
        </Button>

        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <span className="text-4xl">{template.icon}</span>
            <h1 className="text-3xl">{template.name}</h1>
          </div>
          <p className="text-muted-foreground">{template.description}</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Framework Inputs</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {template.fields.map(field => (
                  <div key={field.id} className="space-y-2">
                    <Label htmlFor={field.id}>{field.label}</Label>
                    {field.type === 'text' && (
                      <Input
                        id={field.id}
                        placeholder={field.placeholder}
                        value={inputs[field.id] || ''}
                        onChange={(e) => handleInputChange(field.id, e.target.value)}
                      />
                    )}
                    {field.type === 'textarea' && (
                      <Textarea
                        id={field.id}
                        placeholder={field.placeholder}
                        value={inputs[field.id] || ''}
                        onChange={(e) => handleInputChange(field.id, e.target.value)}
                        rows={3}
                      />
                    )}
                    {field.type === 'select' && field.options && (
                      <Select
                        value={inputs[field.id] || ''}
                        onValueChange={(value) => handleInputChange(field.id, value)}
                      >
                        <SelectTrigger id={field.id}>
                          <SelectValue placeholder={field.placeholder} />
                        </SelectTrigger>
                        <SelectContent>
                          {field.options.map(option => (
                            <SelectItem key={option} value={option}>
                              {option}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    )}
                  </div>
                ))}
              </CardContent>
            </Card>

            {generatedContent ? (
              <GeneratedContentDisplay
                content={generatedContent}
                activeSection={activeSection}
                onSectionSelect={setActiveSection}
              />
            ) : (
              <Card className="border-dashed">
                <CardContent className="flex flex-col items-center justify-center py-12">
                  <Sparkles className="h-12 w-12 text-muted-foreground mb-4" />
                  <p className="text-muted-foreground text-center">
                    Fill in the inputs and adjust parameters, then click generate
                  </p>
                </CardContent>
              </Card>
            )}
          </div>

          <div className="space-y-6">
            {generatedContent ? (
              <>
                <div className="flex flex-col gap-2">
                  <Button
                    onClick={handleRegenerate}
                    variant="outline"
                    className="w-full"
                    disabled={isGenerating}
                  >
                    <Sparkles className="h-4 w-4 mr-2" />
                    Generate New Version
                  </Button>
                </div>
                <ReferencesPanel templateId={template.id} activeSection={activeSection} />
              </>
            ) : (
              <>
                <ParameterControls params={params} onChange={setParams} />

                <div className="space-y-3">
                  <Button
                    onClick={handleGenerate}
                    className="w-full"
                    size="lg"
                    disabled={isGenerating}
                  >
                    {isGenerating ? (
                      <>
                        <Loader2 className="h-5 w-5 mr-2 animate-spin" />
                        Generating...
                      </>
                    ) : (
                      <>
                        <Sparkles className="h-5 w-5 mr-2" />
                        Generate Content
                      </>
                    )}
                  </Button>
                </div>

                <Card className="bg-muted/50">
                  <CardContent className="pt-6">
                    <div className="space-y-2 text-sm">
                      <p className="flex items-center gap-2">
                        <span className="inline-block w-2 h-2 rounded-full bg-green-500"></span>
                        <span className="text-muted-foreground">AI Database Connected</span>
                      </p>
                      <p className="text-xs text-muted-foreground">
                        Using advanced language models for content generation
                      </p>
                    </div>
                  </CardContent>
                </Card>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}