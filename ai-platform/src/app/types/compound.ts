export interface Compound {
  id: string;
  name: string;
  genericName: string;
  therapeuticArea: string;
  indication: string;
  stage: 'Discovery' | 'Preclinical' | 'Phase I' | 'Phase II' | 'Phase III' | 'Approved' | 'Marketed';
  description: string;
}
