import {useGLTF} from '@react-three/drei';
import manifest from '../config/cloudAssetManifest.json' with {type:'json'};
import {assetUrl} from '../config/deploymentConfig.js';

const modelPath=value=>typeof value==='string'&&/\.(?:glb|gltf)$/i.test(value);
const safeModelUrl=value=>{
  if(!modelPath(value)||/[\s?#]/.test(value))return false;
  if(value.startsWith('/')&&!value.startsWith('//'))return true;
  try{const url=new URL(value);return url.protocol==='https:'&&!url.username&&!url.password;}catch{return false;}
};
export function createAssetRetryResolver({assetManifest=manifest,resolveUrl=assetUrl,locationHref=globalThis.location?.href}={}){
  const approvedKeys=new Map();
  for(const [path,remote]of Object.entries(assetManifest)){
    // Withheld entries remain excluded in development as well as production.
    if(remote===null||!modelPath(path))continue;
    let resolved;try{resolved=resolveUrl(path);}catch{continue;}
    if(!safeModelUrl(resolved))continue;
    approvedKeys.set(path,resolved);approvedKeys.set(resolved,resolved);
    if(safeModelUrl(remote))approvedKeys.set(remote,remote);
    if(locationHref)approvedKeys.set(new URL(resolved,locationHref).href,resolved);
  }
  return (urls,error)=>{
    const explicit=Array.isArray(urls)?urls:typeof urls==='string'?[urls]:[];
    const candidates=explicit.length?explicit:(String(error?.message??'').match(/(?:https?:\/\/|\/assets\/)[^\s"'<>]+/g)??[])
      .map(value=>value.replace(/[:),.;]+$/,''));
    return [...new Set(candidates.map(value=>approvedKeys.get(value)).filter(Boolean))];
  };
}
export const resolveAssetRetryUrls=createAssetRetryResolver();

export function createAssetRecoveryStore({resolveUrls=resolveAssetRetryUrls,clearCache=url=>useGLTF.clear(url)}={}){
  const failures=new Map(),listeners=new Set();
  const emit=()=>{for(const listener of listeners)listener();};
  const subscribe=listener=>{listeners.add(listener);return()=>listeners.delete(listener);};
  const getSnapshot=()=>failures.size;
  const getServerSnapshot=()=>0;
  function register({key,error,urls,retry}){
    const safeUrls=resolveUrls(urls,error);
    if(!safeUrls.length||typeof retry!=='function')return()=>{};
    const entry={key,urls:safeUrls,retry};
    const previousSize=failures.size;failures.set(key,entry);
    if(failures.size!==previousSize)emit();
    return()=>{
      if(failures.get(key)===entry){failures.delete(key);emit();}
    };
  }
  function retryFailed(){
    const pending=[...failures.values()],cleared=new Set(),blocked=new Set();
    // Clear every failed cache key before remounting any subtree. Shared URLs
    // are cleared once, and successful models outside these failures stay cached.
    for(const entry of pending)for(const url of entry.urls){
      if(cleared.has(url)||blocked.has(url))continue;
      try{clearCache(url);cleared.add(url);}catch{blocked.add(url);}
    }
    const ready=pending.filter(entry=>!entry.urls.some(url=>blocked.has(url)));
    for(const entry of ready)if(failures.get(entry.key)===entry)failures.delete(entry.key);
    if(ready.length)emit();
    for(const entry of ready){
      try{entry.retry();}catch{failures.set(entry.key,entry);emit();}
    }
    return ready.length;
  }
  return {subscribe,getSnapshot,getServerSnapshot,register,retryFailed};
}

export const assetRecoveryStore=createAssetRecoveryStore();
