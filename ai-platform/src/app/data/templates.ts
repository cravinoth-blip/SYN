import { Template } from '../types/template';

export const templates: Template[] = [
  // Strategic Tools
  {
    id: 'situational-analysis',
    name: 'Situational Analysis',
    description: 'Comprehensive analysis of current market position and environment',
    category: 'tools',
    icon: '📊',
    preview: 'Evaluate internal and external factors affecting market strategy',
    fields: [
      { id: 'therapeuticArea', label: 'Therapeutic Area', type: 'text', placeholder: 'e.g., Oncology, Cardiovascular' },
      { id: 'marketContext', label: 'Market Context', type: 'textarea', placeholder: 'Current market landscape and trends' },
      { id: 'keyFactors', label: 'Key Factors to Analyze', type: 'textarea', placeholder: 'List critical factors (competitive, regulatory, clinical)' }
    ]
  },
  {
    id: 'market-shaping-matrix',
    name: 'Market Shaping Matrix',
    description: 'Strategic framework for influencing and shaping market dynamics',
    category: 'tools',
    icon: '🎯',
    preview: 'Identify opportunities to shape market perception and standards',
    fields: [
      { id: 'marketSegment', label: 'Market Segment', type: 'text', placeholder: 'Target market or indication' },
      { id: 'stakeholders', label: 'Key Stakeholders', type: 'textarea', placeholder: 'Payers, physicians, patients, KOLs' },
      { id: 'objectives', label: 'Shaping Objectives', type: 'textarea', placeholder: 'What market changes do you want to drive?' }
    ]
  },
  {
    id: 'stakeholder-matrix',
    name: 'Stakeholder Matrix',
    description: 'Map and prioritize stakeholder relationships and influence',
    category: 'tools',
    icon: '👥',
    preview: 'Analyze stakeholder power, interest, and engagement strategy',
    fields: [
      { id: 'project', label: 'Project/Initiative', type: 'text', placeholder: 'e.g., Product launch, clinical program' },
      { id: 'stakeholderGroups', label: 'Stakeholder Groups', type: 'textarea', placeholder: 'List key stakeholder groups' },
      { id: 'priorities', label: 'Priority Criteria', type: 'text', placeholder: 'How to prioritize stakeholders?' }
    ]
  },
  {
    id: 'stakeholder-pyramid',
    name: 'Stakeholder Pyramid',
    description: 'Hierarchical view of stakeholder importance and engagement',
    category: 'tools',
    icon: '🔺',
    preview: 'Visualize stakeholder hierarchy and engagement levels',
    fields: [
      { id: 'initiative', label: 'Initiative', type: 'text', placeholder: 'Strategic initiative or launch' },
      { id: 'topTier', label: 'Top Tier Stakeholders', type: 'text', placeholder: 'Most critical stakeholders' },
      { id: 'engagementGoals', label: 'Engagement Goals', type: 'textarea', placeholder: 'What outcomes per tier?' }
    ]
  },
  {
    id: 'competitor-mapping',
    name: 'Competitor Mapping',
    description: 'Competitive landscape analysis and positioning',
    category: 'tools',
    icon: '🗺️',
    preview: 'Map competitors by key attributes and market position',
    fields: [
      { id: 'indication', label: 'Indication', type: 'text', placeholder: 'Target indication or disease state' },
      { id: 'competitors', label: 'Key Competitors', type: 'textarea', placeholder: 'List competing products/companies' },
      { id: 'dimensions', label: 'Mapping Dimensions', type: 'text', placeholder: 'e.g., Efficacy vs. Safety, Price vs. Innovation' }
    ]
  },
  {
    id: 'think-feel-do',
    name: 'Think. Feel. Do.',
    description: 'Customer journey mapping focused on cognition, emotion, and behavior',
    category: 'tools',
    icon: '💭',
    preview: 'Understand what stakeholders think, feel, and do at each stage',
    fields: [
      { id: 'audience', label: 'Target Audience', type: 'text', placeholder: 'e.g., Physicians, patients, payers' },
      { id: 'journey', label: 'Journey Stage', type: 'text', placeholder: 'e.g., Awareness, consideration, adoption' },
      { id: 'currentState', label: 'Current State', type: 'textarea', placeholder: 'What is happening now?' }
    ]
  },
  {
    id: 'mindshift-map',
    name: 'Mindshift Map',
    description: 'Strategic framework for changing stakeholder perceptions and behaviors',
    category: 'tools',
    icon: '🧠',
    preview: 'Plan the journey from current to desired mindset',
    fields: [
      { id: 'stakeholder', label: 'Stakeholder Group', type: 'text', placeholder: 'Who needs to shift?' },
      { id: 'currentBelief', label: 'Current Belief/Behavior', type: 'textarea', placeholder: 'What do they think/do now?' },
      { id: 'desiredBelief', label: 'Desired Belief/Behavior', type: 'textarea', placeholder: 'What should they think/do?' }
    ]
  },
  
  // Strategic Deliverables
  {
    id: 'disease-model',
    name: 'Disease Model',
    description: 'Comprehensive overview of disease pathophysiology and progression',
    category: 'deliverables',
    icon: '🔬',
    preview: 'Map disease mechanisms, progression, and clinical manifestations',
    fields: [
      { id: 'disease', label: 'Disease/Condition', type: 'text', placeholder: 'e.g., Type 2 Diabetes, COPD' },
      { id: 'pathophysiology', label: 'Pathophysiology Focus', type: 'textarea', placeholder: 'Key disease mechanisms to highlight' },
      { id: 'clinicalImpact', label: 'Clinical Impact', type: 'textarea', placeholder: 'Patient outcomes and burden' }
    ]
  },
  {
    id: 'clinical-treatment-flow',
    name: 'Clinical Treatment Flow',
    description: 'Treatment pathway and decision-making process in clinical practice',
    category: 'deliverables',
    icon: '⚕️',
    preview: 'Document current standard of care and treatment sequencing',
    fields: [
      { id: 'indication', label: 'Indication', type: 'text', placeholder: 'Treatment indication' },
      { id: 'treatmentLines', label: 'Treatment Lines', type: 'textarea', placeholder: 'First-line, second-line, etc.' },
      { id: 'decisionPoints', label: 'Key Decision Points', type: 'textarea', placeholder: 'When do physicians make treatment changes?' }
    ]
  },
  {
    id: 'patient-journey',
    name: 'Patient Journey',
    description: 'End-to-end patient experience from diagnosis through treatment',
    category: 'deliverables',
    icon: '🚶',
    preview: 'Map patient touchpoints, emotions, and needs throughout care',
    fields: [
      { id: 'condition', label: 'Condition', type: 'text', placeholder: 'Patient condition or disease' },
      { id: 'journeyStages', label: 'Journey Stages', type: 'textarea', placeholder: 'Key stages from symptoms to management' },
      { id: 'painPoints', label: 'Patient Pain Points', type: 'textarea', placeholder: 'Challenges and unmet needs' }
    ]
  },
  {
    id: 'swot',
    name: 'SWOT Analysis',
    description: 'Strengths, Weaknesses, Opportunities, and Threats analysis',
    category: 'deliverables',
    icon: '📋',
    preview: 'Strategic assessment of internal capabilities and external factors',
    fields: [
      { id: 'subject', label: 'Analysis Subject', type: 'text', placeholder: 'Product, strategy, or initiative' },
      { id: 'context', label: 'Strategic Context', type: 'textarea', placeholder: 'Background and scope' },
      { id: 'focus', label: 'Focus Areas', type: 'text', placeholder: 'Which dimensions to emphasize?' }
    ]
  },
  {
    id: 'scientific-focus',
    name: 'Scientific Focus',
    description: 'Prioritized scientific themes and evidence strategy',
    category: 'deliverables',
    icon: '🔎',
    preview: 'Define key scientific messages and evidence needs',
    fields: [
      { id: 'product', label: 'Product', type: 'text', placeholder: 'Product or compound name' },
      { id: 'scientificThemes', label: 'Scientific Themes', type: 'textarea', placeholder: 'Core scientific narratives' },
      { id: 'evidenceGaps', label: 'Evidence Gaps', type: 'textarea', placeholder: 'Areas needing more data' }
    ]
  },
  {
    id: 'target-product-profile',
    name: 'Target Product Profile',
    description: 'Desired product characteristics and performance specifications',
    category: 'deliverables',
    icon: '🎯',
    preview: 'Define ideal product attributes for development and positioning',
    fields: [
      { id: 'productName', label: 'Product Name', type: 'text', placeholder: 'Product or development compound' },
      { id: 'indication', label: 'Target Indication', type: 'text', placeholder: 'Primary indication' },
      { id: 'attributes', label: 'Key Attributes', type: 'textarea', placeholder: 'Efficacy, safety, convenience targets' }
    ]
  },
  {
    id: 'pgmi',
    name: 'PGMI (Payer, Government, Managed Markets, Integrated Systems)',
    description: 'Strategy for market access and reimbursement stakeholders',
    category: 'deliverables',
    icon: '💼',
    preview: 'Develop positioning and evidence for access stakeholders',
    fields: [
      { id: 'product', label: 'Product', type: 'text', placeholder: 'Product name' },
      { id: 'valueStory', label: 'Value Story', type: 'textarea', placeholder: 'Health economic and outcomes value' },
      { id: 'accessBarriers', label: 'Access Barriers', type: 'textarea', placeholder: 'Anticipated reimbursement challenges' }
    ]
  },
  {
    id: 'scientific-strategic-framework',
    name: 'Scientific Strategic Framework',
    description: 'Overarching scientific and medical affairs strategy',
    category: 'deliverables',
    icon: '🏗️',
    preview: 'Integrated framework connecting scientific goals to business objectives',
    fields: [
      { id: 'product', label: 'Product/Portfolio', type: 'text', placeholder: 'Product or portfolio scope' },
      { id: 'objectives', label: 'Strategic Objectives', type: 'textarea', placeholder: 'Scientific and medical goals' },
      { id: 'pillars', label: 'Strategic Pillars', type: 'textarea', placeholder: 'Core themes or workstreams' }
    ]
  },
  {
    id: 'scientific-story',
    name: 'Scientific Story',
    description: 'Compelling narrative of scientific evidence and clinical value',
    category: 'deliverables',
    icon: '📖',
    preview: 'Craft the scientific narrative from data to clinical impact',
    fields: [
      { id: 'product', label: 'Product', type: 'text', placeholder: 'Product name' },
      { id: 'audience', label: 'Target Audience', type: 'text', placeholder: 'e.g., KOLs, investigators, payers' },
      { id: 'keyData', label: 'Key Data Points', type: 'textarea', placeholder: 'Critical evidence to include' }
    ]
  }
];
