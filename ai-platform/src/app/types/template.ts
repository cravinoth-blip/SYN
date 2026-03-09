export interface TemplateField {
  id: string;
  label: string;
  type: 'text' | 'textarea' | 'number' | 'select';
  placeholder?: string;
  options?: string[];
  maxLength?: number;
}

export interface Template {
  id: string;
  name: string;
  description: string;
  category: 'tools' | 'deliverables';
  icon: string;
  preview: string;
  fields: TemplateField[];
}

export interface GeneratedContent {
  templateId: string;
  content: Record<string, string>;
  timestamp: number;
}

export interface GenerationParams {
  tone: 'professional' | 'casual' | 'friendly' | 'formal' | 'creative';
  length: 'short' | 'medium' | 'long';
  style: 'descriptive' | 'concise' | 'persuasive' | 'informative';
}