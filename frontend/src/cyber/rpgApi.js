import {deployment} from '../config/deploymentConfig.js';
const BASE_URL=deployment.apiBaseUrl;
const SESSION_KEY='prep.shared.session.v1';
let inFlightSession=null,memorySession=null;
function savedSession(){try{return JSON.parse(globalThis.sessionStorage?.getItem(SESSION_KEY)??'null')??memorySession;}catch{return memorySession;}}
async function session(force=false){
  const saved=savedSession();if(saved?.token&&!force)return saved;
  if(inFlightSession)return inFlightSession;
  inFlightSession=(async()=>{
    const response=await fetch(BASE_URL+'/session',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(force?{}:{token:saved?.token})});
    const data=await response.json();if(!data.ok)throw new Error('Sessão indisponível.');
    memorySession={token:data.token,actorId:data.actorId};
    try{globalThis.sessionStorage?.setItem(SESSION_KEY,JSON.stringify(memorySession));}catch{/* Session remains in memory. */}
    return memorySession;
  })();
  try{return await inFlightSession;}finally{inFlightSession=null;}
}
async function request(path,{method='GET',body,binary=false}={},retry=true){
  if(!BASE_URL)return {ok:false,status:503,message:'O serviço compartilhado ainda não está disponível nesta publicação. A exploração local continua disponível.'};
  try{
    const current=await session();
    const response=await fetch(BASE_URL+path,{method,cache:'no-store',headers:{Authorization:`Bearer ${current.token}`,...(body?{'Content-Type':'application/json'}:{})},...(body?{body:JSON.stringify(body)}:{})});
    if(response.status===401&&retry){await session(true);return request(path,{method,body,binary},false);}
    if(binary&&response.ok){const blob=await response.blob();return {ok:true,url:URL.createObjectURL(blob)};}
    const data=await response.json();return {...data,status:response.status};
  }catch{return {ok:false,status:0,message:'Não foi possível acessar o serviço do PREPARATÓRIO.'};}
}
export const askJarvis=(question,npcId='jarvis')=>request('/rpg/ask',{method:'POST',body:{question,npcId}});
export const claimOwner=ownerToken=>request('/rpg/owner/claim',{method:'POST',body:{ownerToken}});
export const unlockHome=password=>request('/rpg/home/unlock',{method:'POST',body:{password}});
export const getPrivateHomeLayout=()=>request('/rpg/home/layout');
// Callers must revoke the temporary URL when closing the private scene. Passwords
// and owner codes only travel in authenticated POST bodies; neither is persisted.
export const getPrivateHomeAsset=()=>request('/rpg/home/asset',{binary:true});
