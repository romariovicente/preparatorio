import cloudAssetManifest from './cloudAssetManifest.json' with {type:'json'};

const loopback=hostname=>['localhost','127.0.0.1','[::1]','::1'].includes(hostname);
function pathBase(value='/') {
  if(typeof value!=='string'||!value.startsWith('/')||value.startsWith('//')||/[?#\\]/.test(value)||value.split('/').includes('..'))throw new Error('Base do aplicativo inválida.');
  return value.replace(/\/*$/,'/');
}
function serviceBase(value,development) {
  if(!value)return null;
  const url=new URL(value);
  if(url.username||url.password||url.search||url.hash||(!development&&url.protocol!=='https:')||(development&&!['http:','https:'].includes(url.protocol)))throw new Error('O serviço requer uma URL HTTPS sem credenciais.');
  if(!development&&loopback(url.hostname))throw new Error('O site público não pode usar um serviço localhost.');
  return url.href.replace(/\/$/,'');
}

export function createDeploymentConfig({basePath='/',assetBaseUrl='',apiBaseUrl='',development=false,hostname='',manifest={}}={}) {
  const base=pathBase(basePath),assets=assetBaseUrl?serviceBase(assetBaseUrl,development)+'/':base+'assets/';
  const api=serviceBase(apiBaseUrl,development)??(development&&(!hostname||loopback(hostname))?'http://127.0.0.1:5180':null);
  function assetUrl(value) {
    if(typeof value!=='string'||!value.startsWith('/assets/'))return value;
    const suffixAt=value.search(/[?#]/);
    const path=suffixAt<0?value:value.slice(0,suffixAt);
    const suffix=suffixAt<0?'':value.slice(suffixAt);
    if(!development&&Object.hasOwn(manifest,path)) {
      const mapped=manifest[path];
      // null explicitly withholds a file whose public distribution is unapproved.
      return mapped===null?null:serviceBase(mapped,false)+suffix;
    }
    return assets+value.slice('/assets/'.length);
  }
  function resolveAssetReferences(value) {
    if(Array.isArray(value))return value.map(resolveAssetReferences);
    if(value&&typeof value==='object')return Object.fromEntries(Object.entries(value).map(([key,item])=>[key,resolveAssetReferences(item)]));
    return assetUrl(value);
  }
  const apiUrl=path=>api?api+'/'+String(path).replace(/^\//,''):null;
  const applicationPath=path=>base+String(path??'').replace(/^\//,'');
  const relativeApplicationPath=path=>path.startsWith(base)?'/'+path.slice(base.length):path;
  return {basePath:base,apiBaseUrl:api,assetUrl,resolveAssetReferences,apiUrl,applicationPath,relativeApplicationPath};
}

const env=import.meta.env??{};
export const deployment=createDeploymentConfig({basePath:env.BASE_URL??'/',assetBaseUrl:env.VITE_ASSET_BASE_URL,apiBaseUrl:env.VITE_API_BASE_URL,development:env.DEV??true,hostname:globalThis.location?.hostname??'',manifest:cloudAssetManifest});
export const {assetUrl,resolveAssetReferences,apiUrl,applicationPath,relativeApplicationPath}=deployment;
