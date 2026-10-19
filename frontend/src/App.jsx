import {relativeApplicationPath} from './config/deploymentConfig.js';
import { lazy, Suspense } from 'react';
import WorldShell from './world/WorldShell.jsx';

const HospitalPreview = lazy(() => import('./hospital/HospitalPreview.jsx'));

export default function App() {
  if ((relativeApplicationPath(window.location.pathname).replace(/\/+$/, '') === '/hospital-preview'||new URLSearchParams(window.location.search).get('view')==='hospital')) {
    return <Suspense fallback={<div role="status" style={{ padding: 32 }}>Abrindo a prévia do módulo hospitalar…</div>}><HospitalPreview /></Suspense>;
  }
  return <WorldShell />;
}
