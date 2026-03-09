import { KnowledgeCategory } from '../types/knowledge';

export const knowledgeCategories: KnowledgeCategory[] = [
  {
    id: 'internal',
    name: 'Internal Resources',
    description: 'Proprietary company documents and strategic materials',
    icon: '🏢',
    subcategories: [
      {
        id: 'brand-strategy',
        name: 'Brand Strategy Decks',
        description: 'Strategic planning and positioning documents'
      },
      {
        id: 'medical-plans',
        name: 'Medical Plans',
        description: 'Medical affairs strategies and execution plans'
      },
      {
        id: 'congress-readouts',
        name: 'Congress Readouts',
        description: 'Conference summaries and key learnings'
      },
      {
        id: 'evidence-packs',
        name: 'Evidence Packs',
        description: 'Compiled clinical and scientific evidence'
      },
      {
        id: 'ci-trackers',
        name: 'CI Trackers',
        description: 'Competitive intelligence tracking documents'
      }
    ]
  },
  {
    id: 'external',
    name: 'External Resources',
    description: 'Public domain and third-party information sources',
    icon: '🌐',
    subcategories: [
      {
        id: 'guidelines',
        name: 'Guidelines',
        description: 'Clinical practice guidelines and recommendations'
      },
      {
        id: 'abstracts',
        name: 'Abstracts',
        description: 'Conference abstracts and presentations'
      },
      {
        id: 'publications',
        name: 'Publications',
        description: 'Peer-reviewed journal articles'
      },
      {
        id: 'trial-registries',
        name: 'Trial Registries',
        description: 'Clinical trial registrations and protocols'
      },
      {
        id: 'hta-decisions',
        name: 'HTA Decisions',
        description: 'Health technology assessments and reimbursement decisions'
      },
      {
        id: 'policy-updates',
        name: 'Policy Updates',
        description: 'Regulatory and policy changes'
      }
    ]
  },
  {
    id: 'systems',
    name: 'System Integrations',
    description: 'Connected platforms and data sources',
    icon: '⚙️',
    subcategories: [
      {
        id: 'sharepoint-teams',
        name: 'SharePoint/Teams',
        description: 'Microsoft collaboration platform files'
      },
      {
        id: 'veeva',
        name: 'Veeva',
        description: 'Veeva Vault and CRM documents'
      },
      {
        id: 'data-lakes',
        name: 'Internal Data Lakes',
        description: 'Enterprise data warehouse resources'
      },
      {
        id: 'literature-databases',
        name: 'Literature Databases',
        description: 'PubMed, Embase, and other scientific databases'
      }
    ]
  }
];
