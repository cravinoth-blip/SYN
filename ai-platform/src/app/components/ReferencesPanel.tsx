import { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from './ui/card';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from './ui/dialog';
import { BookOpen, Search, Plus, Check, Loader2, X, Telescope, SlidersHorizontal } from 'lucide-react';

export interface Reference {
  id: string;
  title: string;
  authors: string;
  source: string;
  year: number;
  type: 'Clinical Trial' | 'Meta-Analysis' | 'Review' | 'Guidelines' | 'Market Report' | 'Health Economics' | 'Observational Study' | 'Consensus Statement';
}

// ─── All template references ────────────────────────────────────────────────
const allRefs: Record<string, Reference> = {
  'sa-1': { id: 'sa-1', title: 'Global Market Dynamics in Specialty Pharmaceuticals: A Strategic Assessment', authors: 'Chen W, Patel R, Morrison K', source: 'Journal of Pharmaceutical Strategy', year: 2023, type: 'Review' },
  'sa-2': { id: 'sa-2', title: 'Competitive Landscape Analysis Methods for Biopharmaceutical Companies', authors: 'Alvarez J, Thompson D', source: 'Health Economics & Outcomes Research', year: 2022, type: 'Market Report' },
  'sa-3': { id: 'sa-3', title: 'Value-Based Healthcare: Implications for Market Access Strategy', authors: 'Singh A, Bergman F, Dupont M', source: 'Value in Health', year: 2023, type: 'Review' },
  'sa-4': { id: 'sa-4', title: 'Regulatory Intelligence as a Strategic Asset in Drug Development', authors: 'Yamamoto T, Costa L', source: 'Regulatory Affairs Journal', year: 2022, type: 'Observational Study' },
  'ms-1': { id: 'ms-1', title: 'Market Shaping Strategies in Pharmaceutical Innovation: Evidence from Rare Disease Markets', authors: 'Williams R, Fontaine S, Kaur N', source: 'Nature Reviews Drug Discovery', year: 2023, type: 'Review' },
  'ms-2': { id: 'ms-2', title: 'Payer Engagement Frameworks for Innovative Therapies: A Systematic Review', authors: 'Okonkwo E, Larsson P', source: 'PharmacoEconomics', year: 2023, type: 'Meta-Analysis' },
  'ms-3': { id: 'ms-3', title: 'Shaping Clinical Practice Through Evidence-Based Medical Education', authors: 'Reyes C, Andersen B, Liu X', source: 'Medical Education', year: 2022, type: 'Observational Study' },
  'ms-4': { id: 'ms-4', title: 'Treatment Paradigm Evolution: Drivers and Strategic Levers', authors: 'Müller H, Nakamura K', source: 'Journal of Market Access & Health Policy', year: 2023, type: 'Market Report' },
  'ms-5': { id: 'ms-5', title: 'KOL Engagement and Scientific Leadership in Specialty Care', authors: "Tran V, O'Brien S, Kowalski J", source: 'Medical Science Monitor', year: 2022, type: 'Review' },
  'sm-1': { id: 'sm-1', title: 'Stakeholder Mapping in Healthcare: A Framework for Strategic Planning', authors: 'Johansson L, Fernandez P', source: 'Health Policy and Planning', year: 2023, type: 'Review' },
  'sm-2': { id: 'sm-2', title: 'Multi-Stakeholder Engagement Models for Pharmaceutical Product Launches', authors: 'Kim J, Decker A, Rousseau M', source: 'Journal of Managed Care & Specialty Pharmacy', year: 2022, type: 'Observational Study' },
  'sm-3': { id: 'sm-3', title: 'Power-Interest Grid Applications in Healthcare Policy Environments', authors: 'Santos F, Blake E', source: 'Healthcare Management Review', year: 2023, type: 'Market Report' },
  'sp-1': { id: 'sp-1', title: 'Tiered KOL Engagement: Maximizing Scientific Impact Across Influence Levels', authors: 'Erikson G, Park J, Ndiaye A', source: 'Journal of Medical Affairs', year: 2023, type: 'Review' },
  'sp-2': { id: 'sp-2', title: 'Resource Allocation in Stakeholder Engagement Programs: Evidence-Based Approaches', authors: 'Hoffman B, Sanchez T', source: 'PharmacoEconomics', year: 2022, type: 'Observational Study' },
  'sp-3': { id: 'sp-3', title: 'Advocacy Network Development in Rare Disease: Lessons Learned', authors: 'Petrov I, McCarthy D, Zhao L', source: 'Orphanet Journal of Rare Diseases', year: 2023, type: 'Review' },
  'cm-1': { id: 'cm-1', title: 'Competitive Intelligence in Biopharmaceuticals: Methods and Strategic Applications', authors: 'Abrams K, Lindqvist C', source: 'Drug Discovery Today', year: 2023, type: 'Review' },
  'cm-2': { id: 'cm-2', title: 'Head-to-Head Clinical Trials as Competitive Differentiation Tools', authors: 'Vasquez M, Thomsen R, Puri S', source: 'The Lancet', year: 2022, type: 'Meta-Analysis' },
  'cm-3': { id: 'cm-3', title: 'Biosimilar Market Entry: Competitive Strategies for Innovator Products', authors: 'Weber N, Ishikawa Y', source: 'BioDrugs', year: 2023, type: 'Market Report' },
  'cm-4': { id: 'cm-4', title: 'Real-World Evidence as a Competitive Moat: Post-Authorization Studies', authors: 'Coleman R, Bergström A', source: 'JAMA Internal Medicine', year: 2022, type: 'Observational Study' },
  'tfd-1': { id: 'tfd-1', title: "Physician Decision-Making in Specialty Prescribing: Cognitive and Emotional Drivers", authors: 'Huang Y, Foster J, Petit C', source: 'BMJ Open', year: 2023, type: 'Observational Study' },
  'tfd-2': { id: 'tfd-2', title: 'Behavioral Economics Applications in Healthcare Professional Engagement', authors: 'Nguyen P, Steiner W', source: 'Health Affairs', year: 2022, type: 'Review' },
  'tfd-3': { id: 'tfd-3', title: 'Patient Activation and Treatment Adherence: A Think-Feel-Do Framework Analysis', authors: 'Martin E, Collins H, Osei A', source: 'Patient Education and Counseling', year: 2023, type: 'Meta-Analysis' },
  'mm-1': { id: 'mm-1', title: 'Change Management in Clinical Practice: Evidence-Based Frameworks for Belief Transformation', authors: 'Larsen T, Adekunle B, Sato M', source: 'Implementation Science', year: 2023, type: 'Review' },
  'mm-2': { id: 'mm-2', title: 'Scientific Narrative Strategies for Shifting Treatment Paradigms', authors: 'Garnier F, Prokop W', source: 'Medical Science Monitor', year: 2022, type: 'Review' },
  'mm-3': { id: 'mm-3', title: 'Adoption Curve Dynamics in Novel Therapeutic Categories', authors: 'Bishop L, Tanaka H, Ferreira R', source: 'Journal of Health Economics', year: 2023, type: 'Observational Study' },
  'dm-1': { id: 'dm-1', title: 'Pathophysiological Modeling in Drug Development: From Bench to Strategic Positioning', authors: 'Keller A, Ivanova O', source: 'Nature Medicine', year: 2023, type: 'Review' },
  'dm-2': { id: 'dm-2', title: 'Global Disease Burden Analysis: Epidemiology, Costs and Unmet Needs', authors: 'Moreno J, Stein R, Fujimoto K', source: 'The Lancet Global Health', year: 2023, type: 'Observational Study' },
  'dm-3': { id: 'dm-3', title: 'Biomarker-Driven Patient Segmentation in Complex Diseases', authors: 'Hassan N, Brandt U', source: 'Journal of Translational Medicine', year: 2022, type: 'Review' },
  'dm-4': { id: 'dm-4', title: 'Patient-Reported Burden in Chronic Disease: Qualitative and Quantitative Measures', authors: 'Park S, Dupuis A, Mendez L', source: 'Quality of Life Research', year: 2023, type: 'Meta-Analysis' },
  'ctf-1': { id: 'ctf-1', title: 'Treatment Algorithm Development: Evidence Synthesis for Clinical Practice Guidelines', authors: 'Werner K, Alabi M, Cho S', source: 'Annals of Internal Medicine', year: 2023, type: 'Guidelines' },
  'ctf-2': { id: 'ctf-2', title: 'Real-World Treatment Patterns and Clinical Sequencing in Specialty Care', authors: 'Torres V, Henriksen P', source: 'Clinical Pharmacology & Therapeutics', year: 2022, type: 'Observational Study' },
  'ctf-3': { id: 'ctf-3', title: 'Decision Support Tools in Complex Therapeutic Areas: A Systematic Review', authors: 'Ahmad I, Bauer C, Suarez D', source: 'JAMA Network Open', year: 2023, type: 'Meta-Analysis' },
  'ctf-4': { id: 'ctf-4', title: 'Multidisciplinary Care Models and Outcomes in Chronic Disease Management', authors: 'Laurent M, Ito N', source: 'BMJ Quality & Safety', year: 2022, type: 'Review' },
  'pj-1': { id: 'pj-1', title: 'Mapping Patient Journeys in Specialty Medicine: Qualitative and Quantitative Approaches', authors: 'Coleman S, Dufour L, Yamada T', source: 'Patient', year: 2023, type: 'Review' },
  'pj-2': { id: 'pj-2', title: 'Diagnostic Delay and Its Impact on Long-Term Outcomes: A Retrospective Cohort Study', authors: 'Obasi C, Nielsen E, Romero F', source: 'JAMA Internal Medicine', year: 2022, type: 'Observational Study' },
  'pj-3': { id: 'pj-3', title: 'Caregiver Burden in Chronic Disease: Financial and Emotional Impact Assessment', authors: 'Sterling J, Kovács P', source: 'Value in Health', year: 2023, type: 'Health Economics' },
  'pj-4': { id: 'pj-4', title: 'Patient Activation Measures as Predictors of Treatment Outcomes', authors: 'Goldstein R, Peralta N, Tamura H', source: 'Patient Education and Counseling', year: 2023, type: 'Clinical Trial' },
  'sw-1': { id: 'sw-1', title: 'Strategic Planning in Pharmaceutical Portfolio Management: SWOT and Beyond', authors: 'Holt A, Pfeifer R', source: 'Journal of Pharmaceutical Policy and Practice', year: 2023, type: 'Review' },
  'sw-2': { id: 'sw-2', title: 'Competitive Threats from Pipeline Assets: Proactive Strategic Response Frameworks', authors: 'Mwangi E, Söderström K', source: 'Drug Discovery Today', year: 2022, type: 'Market Report' },
  'sf-1': { id: 'sf-1', title: 'Medical Affairs Scientific Strategy: Aligning Evidence Generation with Unmet Medical Needs', authors: 'Hoffman T, Obi C, Larsson M', source: 'Therapeutic Innovation & Regulatory Science', year: 2023, type: 'Review' },
  'sf-2': { id: 'sf-2', title: 'Evidence Hierarchy in Pharmaceutical Strategy: RCTs, RWE, and Scientific Credibility', authors: 'Brennan K, Sugimoto Y', source: 'Clinical Evidence', year: 2022, type: 'Meta-Analysis' },
  'sf-3': { id: 'sf-3', title: 'Data Gap Analysis in Pre-Launch and Post-Launch Phases', authors: 'Vance D, Henning A, Rao S', source: 'Journal of Medical Affairs', year: 2023, type: 'Observational Study' },
  'tpp-1': { id: 'tpp-1', title: 'Target Product Profile Frameworks in Drug Development: FDA and EMA Perspectives', authors: 'Barrett W, Schäfer L', source: 'Regulatory Toxicology and Pharmacology', year: 2023, type: 'Guidelines' },
  'tpp-2': { id: 'tpp-2', title: 'Market-Informed Target Product Profiles: Integrating Commercial and Clinical Objectives', authors: 'Nair V, Gustafsson B, Adeyemi T', source: 'Drug Discovery Today', year: 2022, type: 'Review' },
  'tpp-3': { id: 'tpp-3', title: 'Ideal vs. Minimum TPP Benchmarks: Evidence from Successful Launch Programs', authors: 'Fujiwara S, Reinhardt K', source: 'Value in Health', year: 2023, type: 'Observational Study' },
  'pg-1': { id: 'pg-1', title: 'PGMI Framework in Medical Affairs: Prioritization, Gap Analysis, and Implementation', authors: 'Walsh J, Erickson C, Bamba A', source: 'Journal of Medical Affairs', year: 2023, type: 'Review' },
  'pg-2': { id: 'pg-2', title: 'Strategic Prioritization in Resource-Constrained Medical Affairs Teams', authors: 'Leblanc F, Hashimoto D', source: 'Therapeutic Innovation & Regulatory Science', year: 2022, type: 'Observational Study' },
  'ssf-1': { id: 'ssf-1', title: 'Integrated Scientific Platform Development for Biopharmaceutical Assets', authors: 'Christensen B, Kapoor M, Ihejirika O', source: 'Nature Reviews Drug Discovery', year: 2023, type: 'Review' },
  'ssf-2': { id: 'ssf-2', title: 'Medical Strategy Frameworks: Evidence-Based Approaches for Pre-Launch Programs', authors: 'Goldberg A, Villanueva P', source: 'Drug Discovery Today', year: 2022, type: 'Market Report' },
  'ssf-3': { id: 'ssf-3', title: 'Cross-Functional Strategic Alignment in Pharmaceutical Product Strategy', authors: 'Nakagawa R, Hudson E, Mekonnen L', source: 'Journal of Pharmaceutical Strategy', year: 2023, type: 'Observational Study' },
  'ss-1': { id: 'ss-1', title: 'Scientific Storytelling in Medical Communications: Principles and Best Practices', authors: 'Pham D, Reinstein J, Amara S', source: 'Medical Writing', year: 2023, type: 'Review' },
  'ss-2': { id: 'ss-2', title: 'Narrative Medicine and Clinical Data Presentation: Impact on HCP Perception', authors: 'Olsson K, Mensah A', source: 'Medical Education', year: 2022, type: 'Observational Study' },
  'ss-3': { id: 'ss-3', title: 'Strategic Messaging Architecture for Pharmaceutical Brands', authors: 'Fitzpatrick M, Zhou W', source: 'Journal of Medical Affairs', year: 2023, type: 'Review' },
};

// ─── Section-to-reference map ────────────────────────────────────────────────
// templateId → sectionKey → referenceIds[]
const sectionRefMap: Record<string, Record<string, string[]>> = {
  'situational-analysis': {
    executiveSummary:  ['sa-1', 'sa-2'],
    marketOverview:    ['sa-2', 'sa-3'],
    internalFactors:   ['sa-1', 'sa-4'],
    externalFactors:   ['sa-2', 'sa-3'],
    criticalFactors:   ['sa-3', 'sa-4'],
    recommendations:   ['sa-1', 'sa-4'],
  },
  'market-shaping-matrix': {
    overview:              ['ms-1', 'ms-4'],
    currentState:          ['ms-3', 'ms-4'],
    shapingOpportunities:  ['ms-1', 'ms-2'],
    stakeholderStrategies: ['ms-3', 'ms-5'],
    tactics:               ['ms-2', 'ms-5'],
    objectives:            ['ms-1', 'ms-4'],
    timeline:              ['ms-2', 'ms-3'],
  },
  'stakeholder-matrix': {
    overview:                ['sm-1', 'sm-2'],
    stakeholderSegmentation: ['sm-1', 'sm-3'],
    powerInterestMatrix:     ['sm-1', 'sm-2'],
    engagementStrategy:      ['sm-2', 'sm-3'],
    prioritization:          ['sm-1', 'sm-3'],
    actionPlan:              ['sm-2', 'sm-3'],
    riskMitigation:          ['sm-1', 'sm-2'],
  },
  'stakeholder-pyramid': {
    overview:          ['sp-1', 'sp-2'],
    tier1TopPriority:  ['sp-1', 'sp-3'],
    tier2HighPriority: ['sp-1', 'sp-2'],
    tier3Medium:       ['sp-2', 'sp-3'],
    tier4Broad:        ['sp-2', 'sp-3'],
    objectives:        ['sp-1', 'sp-3'],
    movementStrategy:  ['sp-2', 'sp-3'],
    resourceAllocation:['sp-2', 'sp-3'],
  },
  'competitor-mapping': {
    overview:                ['cm-1', 'cm-3'],
    competitiveSet:          ['cm-1', 'cm-3'],
    productComparison:       ['cm-2', 'cm-4'],
    marketPositioning:       ['cm-3', 'cm-4'],
    clinicalDifferentiation: ['cm-2', 'cm-4'],
    strategicPositioning:    ['cm-1', 'cm-3'],
    competitiveThreats:      ['cm-2', 'cm-3'],
    recommendations:         ['cm-1', 'cm-4'],
  },
  'think-feel-do': {
    overview:             ['tfd-1', 'tfd-2'],
    currentState:         ['tfd-1', 'tfd-3'],
    thinkCognitive:       ['tfd-2', 'tfd-3'],
    feelEmotional:        ['tfd-1', 'tfd-2'],
    doBehavioral:         ['tfd-1', 'tfd-3'],
    interventionStrategy: ['tfd-2', 'tfd-3'],
    journeyOptimization:  ['tfd-1', 'tfd-2'],
  },
  'mindshift-map': {
    overview:        ['mm-1', 'mm-2'],
    currentMindset:  ['mm-1', 'mm-3'],
    desiredMindset:  ['mm-2', 'mm-3'],
    mindshiftPath:   ['mm-1', 'mm-2'],
    barriers:        ['mm-1', 'mm-3'],
    enablers:        ['mm-2', 'mm-3'],
    tactics:         ['mm-1', 'mm-2'],
    successMetrics:  ['mm-2', 'mm-3'],
  },
  'disease-model': {
    overview:               ['dm-1', 'dm-2'],
    diseaseBackground:      ['dm-2', 'dm-4'],
    pathophysiology:        ['dm-1', 'dm-3'],
    progression:            ['dm-1', 'dm-2'],
    clinicalManifestations: ['dm-3', 'dm-4'],
    patientBurden:          ['dm-2', 'dm-4'],
    unmetNeeds:             ['dm-1', 'dm-3'],
    treatmentRationale:     ['dm-1', 'dm-2'],
  },
  'clinical-treatment-flow': {
    overview:            ['ctf-1', 'ctf-2'],
    diagnosis:           ['ctf-1', 'ctf-3'],
    treatmentAlgorithm:  ['ctf-1', 'ctf-2'],
    decisionCriteria:    ['ctf-3', 'ctf-4'],
    monitoring:          ['ctf-2', 'ctf-4'],
    specialPopulations:  ['ctf-1', 'ctf-3'],
    adjunctiveTherapies: ['ctf-2', 'ctf-4'],
    referralPathways:    ['ctf-3', 'ctf-4'],
  },
  'patient-journey': {
    overview:           ['pj-1', 'pj-2'],
    preSymptoms:        ['pj-1', 'pj-4'],
    symptomsEmergence:  ['pj-2', 'pj-3'],
    diagnosisWorkup:    ['pj-1', 'pj-2'],
    treatmentInitiation:['pj-3', 'pj-4'],
    ongoingManagement:  ['pj-2', 'pj-4'],
    patientExperience:  ['pj-1', 'pj-3'],
  },
  'swot': {
    overview:        ['sw-1', 'sw-2'],
    strengths:       ['sw-1', 'sw-2'],
    weaknesses:      ['sw-1', 'sw-2'],
    opportunities:   ['sw-1', 'sw-2'],
    threats:         ['sw-2'],
    strategicActions:['sw-1', 'sw-2'],
  },
  'scientific-focus': {
    overview:           ['sf-1', 'sf-2'],
    evidenceGaps:       ['sf-2', 'sf-3'],
    researchPriorities: ['sf-1', 'sf-3'],
    dataStrategy:       ['sf-1', 'sf-2'],
    publications:       ['sf-2', 'sf-3'],
    medicalEducation:   ['sf-1', 'sf-3'],
  },
  'target-product-profile': {
    overview:        ['tpp-1', 'tpp-2'],
    idealProfile:    ['tpp-2', 'tpp-3'],
    minimumProfile:  ['tpp-1', 'tpp-3'],
    clinicalEndpoints:['tpp-1', 'tpp-2'],
    safetyProfile:   ['tpp-2', 'tpp-3'],
    marketAccess:    ['tpp-1', 'tpp-3'],
  },
  'pgmi': {
    overview:       ['pg-1', 'pg-2'],
    priorities:     ['pg-1', 'pg-2'],
    gaps:           ['pg-1', 'pg-2'],
    monitoring:     ['pg-1', 'pg-2'],
    improvements:   ['pg-1', 'pg-2'],
  },
  'scientific-strategic-framework': {
    overview:             ['ssf-1', 'ssf-2'],
    scientificPlatform:   ['ssf-1', 'ssf-3'],
    evidenceGeneration:   ['ssf-1', 'ssf-2'],
    stakeholderStrategy:  ['ssf-2', 'ssf-3'],
    communicationPlan:    ['ssf-1', 'ssf-3'],
    resourceAllocation:   ['ssf-2', 'ssf-3'],
  },
  'scientific-story': {
    overview:          ['ss-1', 'ss-2'],
    coreNarrative:     ['ss-1', 'ss-3'],
    clinicalEvidence:  ['ss-2', 'ss-3'],
    patientImpact:     ['ss-1', 'ss-2'],
    messagingPillars:  ['ss-1', 'ss-3'],
    disseminationPlan: ['ss-2', 'ss-3'],
  },
};

// ─── Fallback for templates with no section mapping ──────────────────────────
const templateDefaultRefs: Record<string, string[]> = {
  'situational-analysis': ['sa-1','sa-2','sa-3','sa-4'],
  'market-shaping-matrix': ['ms-1','ms-2','ms-3','ms-4','ms-5'],
  'stakeholder-matrix': ['sm-1','sm-2','sm-3'],
  'stakeholder-pyramid': ['sp-1','sp-2','sp-3'],
  'competitor-mapping': ['cm-1','cm-2','cm-3','cm-4'],
  'think-feel-do': ['tfd-1','tfd-2','tfd-3'],
  'mindshift-map': ['mm-1','mm-2','mm-3'],
  'disease-model': ['dm-1','dm-2','dm-3','dm-4'],
  'clinical-treatment-flow': ['ctf-1','ctf-2','ctf-3','ctf-4'],
  'patient-journey': ['pj-1','pj-2','pj-3','pj-4'],
  'swot': ['sw-1','sw-2'],
  'scientific-focus': ['sf-1','sf-2','sf-3'],
  'target-product-profile': ['tpp-1','tpp-2','tpp-3'],
  'pgmi': ['pg-1','pg-2'],
  'scientific-strategic-framework': ['ssf-1','ssf-2','ssf-3'],
  'scientific-story': ['ss-1','ss-2','ss-3'],
};

// ─── Explore pool ─────────────────────────────────────────────────────────────
const explorePool: Reference[] = [
  { id: 'ep-1',  title: 'Precision Medicine and Biomarker-Driven Patient Selection in Specialty Care', authors: 'Huang M, Kovacs Z, Adichie N', source: 'New England Journal of Medicine', year: 2024, type: 'Clinical Trial' },
  { id: 'ep-2',  title: 'Health Technology Assessment Frameworks: International Comparative Analysis', authors: 'Drummond M, O\'Brien B', source: 'Value in Health', year: 2023, type: 'Review' },
  { id: 'ep-3',  title: 'Payer Decision-Making in Specialty Pharmacy: A Qualitative Study', authors: 'Stern L, Fujita K', source: 'Journal of Managed Care & Specialty Pharmacy', year: 2023, type: 'Observational Study' },
  { id: 'ep-4',  title: 'Real-World Evidence Generation: Methods, Standards, and Regulatory Expectations', authors: 'Wang Y, Albers C, Mensah P', source: 'Clinical Pharmacology & Therapeutics', year: 2023, type: 'Guidelines' },
  { id: 'ep-5',  title: 'Patient Advocacy Groups as Strategic Partners in Drug Development', authors: 'McCarthy R, Bello E', source: 'Orphanet Journal of Rare Diseases', year: 2022, type: 'Review' },
  { id: 'ep-6',  title: 'Cost-Effectiveness of Novel Biologics vs Standard of Care: Systematic Review', authors: 'Lindqvist H, Nakamura S', source: 'PharmacoEconomics', year: 2023, type: 'Health Economics' },
  { id: 'ep-7',  title: 'Digital Health Technologies in Clinical Trial Design and Patient Monitoring', authors: 'Osei T, Bergmann F, Kimura Y', source: 'npj Digital Medicine', year: 2024, type: 'Review' },
  { id: 'ep-8',  title: 'Treatment Persistence and Adherence in Chronic Disease: Meta-Analytic Evidence', authors: 'Rosario L, Park A', source: 'Annals of Internal Medicine', year: 2022, type: 'Meta-Analysis' },
  { id: 'ep-9',  title: 'International Pricing and Reimbursement Strategies for Specialty Products', authors: 'Wagner D, Tremblay C', source: 'Health Policy', year: 2023, type: 'Market Report' },
  { id: 'ep-10', title: 'Consensus Recommendations on Outcomes Research in Specialty Care', authors: 'ISPOR Special Interest Group', source: 'Value in Health', year: 2023, type: 'Consensus Statement' },
  { id: 'ep-11', title: 'Phase III–IV Evidence Translation to Clinical Practice: Bridging the Gap', authors: 'Nielsen C, Okonkwo A, Stein M', source: 'The Lancet', year: 2022, type: 'Review' },
  { id: 'ep-12', title: 'Medical Education Impact on Treatment Adoption Rates: A Longitudinal Study', authors: 'Gómez R, Tanaka E', source: 'Academic Medicine', year: 2023, type: 'Observational Study' },
  { id: 'ep-13', title: 'Integrated Evidence Planning in Late-Stage Clinical Development', authors: 'Shah P, Reinholt N, Abubakar K', source: 'Drug Discovery Today', year: 2024, type: 'Review' },
  { id: 'ep-14', title: 'Unmet Medical Needs in Rare Oncology: Systematic Gap Analysis', authors: 'Ferreira L, Blanc A', source: 'Journal of Clinical Oncology', year: 2023, type: 'Meta-Analysis' },
  { id: 'ep-15', title: 'Formulary Management and Access Barriers for Specialty Biologics', authors: 'Novak J, Sato Y, Bernhardt C', source: 'American Journal of Managed Care', year: 2023, type: 'Health Economics' },
  { id: 'ep-16', title: 'Scientific Platform Development: Lessons from Major Launch Programs', authors: 'Ernst B, Mensah D', source: 'Journal of Pharmaceutical Strategy', year: 2024, type: 'Market Report' },
  { id: 'ep-17', title: 'Patient Journey Optimization Through Cross-Functional Collaboration', authors: 'Petersen G, Adebayo O', source: 'Patient', year: 2022, type: 'Observational Study' },
  { id: 'ep-18', title: 'HEOR Communication to Payers: Best Practice Guidelines', authors: 'Global HEOR Collaborative', source: 'PharmacoEconomics', year: 2023, type: 'Guidelines' },
];

const TYPE_COLORS: Record<Reference['type'], string> = {
  'Clinical Trial':       'bg-blue-100 text-blue-700',
  'Meta-Analysis':        'bg-purple-100 text-purple-700',
  'Review':               'bg-teal-100 text-teal-700',
  'Guidelines':           'bg-orange-100 text-orange-700',
  'Market Report':        'bg-amber-100 text-amber-700',
  'Health Economics':     'bg-green-100 text-green-700',
  'Observational Study':  'bg-slate-100 text-slate-700',
  'Consensus Statement':  'bg-rose-100 text-rose-700',
};

const ALL_TYPES: Reference['type'][] = [
  'Clinical Trial','Meta-Analysis','Review','Guidelines',
  'Market Report','Health Economics','Observational Study','Consensus Statement',
];

function formatSectionLabel(key: string) {
  return key.replace(/([A-Z])/g, ' $1').trim();
}

interface ReferencesPanelProps {
  templateId: string;
  activeSection: string | null;
}

export function ReferencesPanel({ templateId, activeSection }: ReferencesPanelProps) {
  // Pinned refs added by user (persist across section changes)
  const [pinnedIds, setPinnedIds] = useState<Set<string>>(new Set());
  // Explore dialog state
  const [exploreOpen, setExploreOpen] = useState(false);
  const [exploreQuery, setExploreQuery]   = useState('');
  const [exploreType, setExploreType]     = useState<Reference['type'] | 'All'>('All');
  const [exploreYear, setExploreYear]     = useState<'All' | '2024' | '2023' | '2022'>('All');
  const [addedToPanel, setAddedToPanel]   = useState<Set<string>>(new Set());

  // Derive visible refs for the panel
  const sectionIds: string[] = activeSection
    ? (sectionRefMap[templateId]?.[activeSection] ?? templateDefaultRefs[templateId] ?? [])
    : (templateDefaultRefs[templateId] ?? []);

  // Merge section refs + pinned refs (deduplicated)
  const visibleRefs: Reference[] = [
    ...sectionIds.map(id => allRefs[id]).filter(Boolean),
    ...[...pinnedIds]
      .filter(id => !sectionIds.includes(id))
      .map(id => allRefs[id] ?? explorePool.find(r => r.id === id))
      .filter((r): r is Reference => Boolean(r)),
  ];

  // Reset explore search when dialog closes
  useEffect(() => {
    if (!exploreOpen) {
      setExploreQuery('');
      setExploreType('All');
      setExploreYear('All');
    }
  }, [exploreOpen]);

  const handlePinRef = (id: string) => {
    setPinnedIds(prev => new Set(prev).add(id));
    setAddedToPanel(prev => new Set(prev).add(id));
  };

  const handleRemoveRef = (id: string) => {
    setPinnedIds(prev => { const s = new Set(prev); s.delete(id); return s; });
  };

  // Explore pool filtering
  const filteredExplore = explorePool.filter(r => {
    if (addedToPanel.has(r.id) || visibleRefs.find(v => v.id === r.id)) return false;
    const matchType = exploreType === 'All' || r.type === exploreType;
    const matchYear = exploreYear === 'All' || r.year === Number(exploreYear);
    const q = exploreQuery.toLowerCase();
    const matchQ = !q || r.title.toLowerCase().includes(q) || r.authors.toLowerCase().includes(q) || r.source.toLowerCase().includes(q);
    return matchType && matchYear && matchQ;
  });

  const isPinned = (id: string) => pinnedIds.has(id);
  const isFromSection = (id: string) => sectionIds.includes(id);

  return (
    <>
      <Card className="flex flex-col">
        {/* Header */}
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2 min-w-0">
              <BookOpen className="h-4 w-4 text-muted-foreground shrink-0" />
              <CardTitle className="text-base truncate">References</CardTitle>
              <span className="text-xs text-muted-foreground bg-muted rounded-full px-2 py-0.5 shrink-0">
                {visibleRefs.length}
              </span>
            </div>
            <Button
              size="sm"
              className="h-8 px-3 shrink-0 gap-1.5"
              onClick={() => setExploreOpen(true)}
            >
              <Telescope className="h-3.5 w-3.5" />
              Explore
            </Button>
          </div>

          {/* Active section indicator */}
          <div className={`text-xs transition-all duration-200 ${activeSection ? 'text-primary' : 'text-muted-foreground'}`}>
            {activeSection
              ? <>Showing refs for: <span className="font-medium">{formatSectionLabel(activeSection)}</span></>
              : 'Click a section to load its references'}
          </div>
        </CardHeader>

        <CardContent className="flex flex-col gap-2 overflow-y-auto max-h-[560px] pr-1">
          {visibleRefs.length === 0 ? (
            <p className="text-xs text-muted-foreground text-center py-6">No references for this section.</p>
          ) : (
            visibleRefs.map((ref, i) => (
              <div
                key={ref.id}
                className={`group relative rounded-lg border p-3 text-sm transition-colors ${
                  isPinned(ref.id) && !isFromSection(ref.id)
                    ? 'border-primary/30 bg-primary/5'
                    : 'border-border bg-background'
                }`}
              >
                {/* Remove pinned ref */}
                {isPinned(ref.id) && !isFromSection(ref.id) && (
                  <button
                    onClick={() => handleRemoveRef(ref.id)}
                    className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground hover:text-destructive"
                  >
                    <X className="h-3 w-3" />
                  </button>
                )}
                <div className="flex items-start gap-2">
                  <span className="shrink-0 text-xs font-mono text-muted-foreground w-4 mt-0.5">{i + 1}.</span>
                  <div className="flex-1 min-w-0">
                    <p className="leading-snug mb-1 pr-3">{ref.title}</p>
                    <p className="text-xs text-muted-foreground">{ref.authors}</p>
                    <div className="flex items-center gap-1.5 mt-1.5 flex-wrap">
                      <span className="text-xs text-muted-foreground italic truncate max-w-[110px]">{ref.source}</span>
                      <span className="text-xs text-muted-foreground">·</span>
                      <span className="text-xs text-muted-foreground">{ref.year}</span>
                      <span className={`text-xs px-1.5 py-0.5 rounded-full font-medium ${TYPE_COLORS[ref.type]}`}>
                        {ref.type}
                      </span>
                      {isPinned(ref.id) && !isFromSection(ref.id) && (
                        <span className="text-xs px-1.5 py-0.5 rounded-full bg-primary/10 text-primary font-medium">Added</span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))
          )}
        </CardContent>
      </Card>

      {/* ─── EXPLORE Dialog ────────────────────────────────────────────────── */}
      <Dialog open={exploreOpen} onOpenChange={setExploreOpen}>
        <DialogContent className="max-w-2xl max-h-[85vh] flex flex-col gap-0 p-0 overflow-hidden">
          <DialogHeader className="px-6 pt-6 pb-4 border-b border-border shrink-0">
            <div className="flex items-center gap-2">
              <Telescope className="h-5 w-5 text-primary" />
              <DialogTitle>Explore References</DialogTitle>
            </div>
            <p className="text-sm text-muted-foreground mt-1">
              Browse and add sources to your reference panel
            </p>
          </DialogHeader>

          {/* Filters */}
          <div className="px-6 py-4 border-b border-border shrink-0 space-y-3">
            <div className="flex gap-2">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
                <Input
                  placeholder="Search by title, author, journal…"
                  value={exploreQuery}
                  onChange={e => setExploreQuery(e.target.value)}
                  className="pl-8 h-9 text-sm"
                />
              </div>
              <div className="flex items-center gap-1.5">
                <SlidersHorizontal className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                {(['All', '2024', '2023', '2022'] as const).map(y => (
                  <button
                    key={y}
                    onClick={() => setExploreYear(y)}
                    className={`text-xs px-2 py-1 rounded-full border transition-colors ${
                      exploreYear === y
                        ? 'bg-primary text-primary-foreground border-primary'
                        : 'border-border text-muted-foreground hover:border-primary/50'
                    }`}
                  >
                    {y}
                  </button>
                ))}
              </div>
            </div>

            {/* Type chips */}
            <div className="flex flex-wrap gap-1.5">
              {(['All', ...ALL_TYPES] as const).map(t => (
                <button
                  key={t}
                  onClick={() => setExploreType(t)}
                  className={`text-xs px-2.5 py-1 rounded-full border transition-colors ${
                    exploreType === t
                      ? 'bg-primary text-primary-foreground border-primary'
                      : 'border-border text-muted-foreground hover:border-primary/40'
                  }`}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>

          {/* Results list */}
          <div className="flex-1 overflow-y-auto px-6 py-4 space-y-2">
            {filteredExplore.length === 0 ? (
              <div className="text-center py-10 text-sm text-muted-foreground">
                No results match your filters.
              </div>
            ) : (
              filteredExplore.map(ref => {
                const added = addedToPanel.has(ref.id);
                return (
                  <div key={ref.id} className="flex items-start gap-3 rounded-lg border border-border bg-background p-3 hover:border-primary/30 transition-colors">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm leading-snug mb-0.5">{ref.title}</p>
                      <p className="text-xs text-muted-foreground">{ref.authors}</p>
                      <div className="flex items-center gap-1.5 mt-1.5 flex-wrap">
                        <span className="text-xs text-muted-foreground italic truncate max-w-[140px]">{ref.source}</span>
                        <span className="text-xs text-muted-foreground">·</span>
                        <span className="text-xs text-muted-foreground">{ref.year}</span>
                        <span className={`text-xs px-1.5 py-0.5 rounded-full font-medium ${TYPE_COLORS[ref.type]}`}>
                          {ref.type}
                        </span>
                      </div>
                    </div>
                    <Button
                      size="sm"
                      variant={added ? 'secondary' : 'outline'}
                      className="h-8 px-3 shrink-0 gap-1.5"
                      disabled={added}
                      onClick={() => handlePinRef(ref.id)}
                    >
                      {added ? <Check className="h-3.5 w-3.5" /> : <Plus className="h-3.5 w-3.5" />}
                      {added ? 'Added' : 'Add'}
                    </Button>
                  </div>
                );
              })
            )}
          </div>

          <div className="px-6 py-3 border-t border-border shrink-0 flex justify-between items-center">
            <p className="text-xs text-muted-foreground">{filteredExplore.length} sources available</p>
            <Button variant="outline" size="sm" onClick={() => setExploreOpen(false)}>Done</Button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
