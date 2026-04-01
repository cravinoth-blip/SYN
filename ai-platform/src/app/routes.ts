import { createBrowserRouter } from 'react-router';
import Layout from './pages/Layout';
import TemplateLibrary from './pages/TemplateLibrary';
import ContentGenerator from './pages/ContentGenerator';
import CompoundSelection from './pages/CompoundSelection';
import KnowledgeBase from './pages/KnowledgeBase';
import PptxComparator from './pages/PptxComparator';

export const router = createBrowserRouter([
  {
    path: '/',
    Component: Layout,
    children: [
      {
        index: true,
        Component: TemplateLibrary,
      },
      {
        path: 'generate/:templateId',
        Component: ContentGenerator,
      },
      {
        path: 'knowledge',
        Component: CompoundSelection,
      },
      {
        path: 'knowledge/:compoundId',
        Component: KnowledgeBase,
      },
      {
        path: 'pptx-compare',
        Component: PptxComparator,
      },
    ],
  },
]);