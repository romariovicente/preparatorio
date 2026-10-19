import react from '@vitejs/plugin-react';
import {defineConfig,loadEnv} from 'vite';

export default defineConfig(({mode})=>{
  const env=loadEnv(mode,globalThis.process.cwd(),'VITE_');
  return {
    base:env.VITE_BASE_PATH||'/',
    plugins:[react()],
    // The cloud artifact contains JS/CSS only; binary models live on asset shards.
    // Local builds keep public/ for the existing desktop launch workflow.
    build:{copyPublicDir:env.VITE_EXTERNAL_ASSETS_ONLY!=='true'},
  };
});
