import { createBrowserRouter } from 'react-router';
import { Layout } from './components/Layout';
import { Dashboard } from './components/Dashboard';
import { ChatInterface } from './components/ChatInterface';
import { ChatHistory } from './components/ChatHistory';
import { DocumentLibrary } from './components/DocumentLibrary';
import { UploadPage } from './components/UploadPage';

export const router = createBrowserRouter([
  {
    path: '/',
    Component: Layout,
    children: [
      { index: true, Component: Dashboard },
      { path: 'chat', Component: ChatInterface },
      { path: 'history', Component: ChatHistory },
      { path: 'documents', Component: DocumentLibrary },
      { path: 'upload', Component: UploadPage },
    ],
  },
]);
