export interface KnowledgeFile {
  id: string;
  name: string;
  category: 'internal' | 'external' | 'systems';
  subcategory: string;
  compoundId: string;
  size: number;
  uploadedAt: number;
  file: File;
  tags?: string[];
}

export interface KnowledgeCategory {
  id: 'internal' | 'external' | 'systems';
  name: string;
  description: string;
  icon: string;
  subcategories: {
    id: string;
    name: string;
    description: string;
  }[];
}