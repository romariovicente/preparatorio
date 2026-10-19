import {deployment} from '../config/deploymentConfig.js';
const SERVER_URL = deployment.apiBaseUrl;
const SESSION_KEY = 'prep.shared.session.v1';

export function createSharedTransport({onSnapshot,onStatus,storage = globalThis.sessionStorage,baseUrl = SERVER_URL} = {}) {
  let session,room,controller,closed=true,ready=false,running=null,retryTimer,retryWake;
  function disconnected() {
    if(closed)return;
    ready=false;onStatus?.('offline',session?.actorId);controller?.abort();
  }
  async function request(path,body) {
    const requestSession=session;
    const response = await fetch(`${baseUrl}${path}`,{method:'POST',headers:{'Content-Type':'application/json',...(requestSession ? {Authorization:`Bearer ${requestSession.token}`} : {})},body:JSON.stringify(body)});
    const data = await response.json();
    const stillCurrent=!requestSession || requestSession.token===session?.token;
    if(response.status===401 && stillCurrent)disconnected();
    if(data.state && !closed && stillCurrent)onSnapshot?.({...data,actorId:session?.actorId});
    if(path!=='/session' && !stillCurrent)return {ok:false,message:'A conexão mudou. Selecione o objeto novamente.'};
    return data;
  }
  async function waitToRetry(delay) {
    await new Promise(resolve=>{retryWake=resolve;retryTimer=setTimeout(resolve,delay);});
    retryWake=null;retryTimer=null;
  }
  async function runConnection() {
    let failures=0;
    try {
      while(!closed) {
        onStatus?.('connecting',session?.actorId);
        try {
          let saved;
          try { saved=JSON.parse(storage?.getItem(SESSION_KEY) ?? 'null'); } catch { /* Malformed storage is replaced by a new session. */ }
          const nextSession=await request('/session',{token:saved?.token});
          if(!nextSession.ok)throw new Error(nextSession.message);
          if(closed)break;
          session=nextSession;
          try { storage?.setItem(SESSION_KEY,JSON.stringify({token:session.token,actorId:session.actorId})); } catch { /* Session still works in memory. */ }
          controller=new AbortController();
          const response=await fetch(`${baseUrl}/events?room=${encodeURIComponent(room)}`,{headers:{Authorization:`Bearer ${session.token}`},signal:controller.signal});
          if(!response.ok || !response.body)throw new Error('O serviço compartilhado está indisponível.');
          if(closed){controller.abort();break;}
          ready=true;failures=0;onStatus?.('connected',session.actorId);
          const reader=response.body.getReader(),decoder=new TextDecoder();let buffer='';
          while(!closed) {
            const {value,done}=await reader.read();if(done)break;
            buffer+=decoder.decode(value,{stream:true});
            let boundary;
            while((boundary=buffer.indexOf('\n\n'))>=0) {
              const block=buffer.slice(0,boundary);buffer=buffer.slice(boundary+2);
              const data=block.split('\n').find(line=>line.startsWith('data: '));
              if(data)onSnapshot?.({...JSON.parse(data.slice(6)),actorId:session.actorId});
            }
          }
        } catch { /* Failed requests and ended streams share the same bounded retry path. */ }
        ready=false;
        if(!closed) {
          onStatus?.('offline',session?.actorId);
          await waitToRetry(Math.min(8000,1000*2**failures));failures=Math.min(failures+1,3);
        }
      }
    } finally { ready=false;running=null; }
  }
  function connect(nextRoom) {
    if(!baseUrl){onStatus?.('offline');return Promise.resolve();}
    if(running)return running;
    room=nextRoom;closed=false;running=runConnection();return running;
  }
  async function action(command) {
    if (!session || closed || !ready) return {ok:false,message:'O serviço compartilhado não está conectado.'};
    try { return await request('/action',{...command,room,eventId:command.eventId ?? globalThis.crypto.randomUUID()}); }
    catch { disconnected();return {ok:false,message:'Conexão perdida. A ação não foi confirmada.'}; }
  }
  async function publishPosition(position,extra={}) {
    if(!session || closed || !ready)return {ok:false};
    try { return await request('/position',{room,position,...extra}); }
    catch { disconnected();return {ok:false}; }
  }
  async function door(doorId,open){
    if(!session||closed||!ready)return {ok:false,message:'O serviço compartilhado não está conectado.'};
    try{return await request('/door',{room,doorId,open});}
    catch{disconnected();return {ok:false,message:'Conexão perdida. A abertura não foi confirmada.'};}
  }
  function close() { closed=true;ready=false;controller?.abort();clearTimeout(retryTimer);retryWake?.(); }
  return {connect,action,publishPosition,door,close};
}
