import {apiUrl} from '../config/deploymentConfig.js';
import {useCallback,useEffect,useState} from 'react';
import {createServerClockAnchor,readClockAnchor} from './clockSync.js';

const HEALTH_URL=apiUrl('/health');

export function useServerClock(config) {
  const [anchor,setAnchor]=useState(()=>({wallMs:Date.now(),monotonicMs:performance.now()}));
  const [status,setStatus]=useState(HEALTH_URL?'connecting':'unavailable');
  useEffect(()=>{
    if(!HEALTH_URL)return;
    let active=true,request=null,timeout=null,hadSync=false;
    async function synchronize() {
      if(request)return;
      const controller=new AbortController();request=controller;
      const startedAt=performance.now();
      timeout=window.setTimeout(()=>controller.abort(),6000);
      try {
        const response=await fetch(HEALTH_URL,{cache:'no-store',signal:controller.signal});
        const data=await response.json(),receivedAt=performance.now();
        const next=response.ok&&createServerClockAnchor(data.serverTimeMs,startedAt,receivedAt);
        if(!next)throw new Error('Relógio do servidor indisponível.');
        if(active){hadSync=true;setAnchor(next);setStatus('synced');}
      } catch {
        if(active)setStatus(hadSync?'stale':'unavailable');
      } finally {
        window.clearTimeout(timeout);request=null;
      }
    }
    synchronize();
    const interval=window.setInterval(synchronize,30000);
    return()=>{active=false;window.clearInterval(interval);window.clearTimeout(timeout);request?.abort();};
  },[]);
  const getClockConfig=useCallback(()=>({...config,clockMode:'server-wall',timeZone:'America/Sao_Paulo',nowMs:readClockAnchor(anchor,performance.now())}),[anchor,config]);
  return {getClockConfig,status};
}
