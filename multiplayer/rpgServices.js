import {createHash,randomBytes,scrypt,scryptSync,timingSafeEqual} from 'node:crypto';
import {readFileSync,statSync} from 'node:fs';
import {isAbsolute,relative,resolve,sep} from 'node:path';
import {fileURLToPath} from 'node:url';
import {promisify} from 'node:util';

const deriveKey=promisify(scrypt);
const PROJECT=resolve(fileURLToPath(new URL('..',import.meta.url)));
const PUBLIC=resolve(PROJECT,'frontend/public');
const readJson=path=>JSON.parse(readFileSync(path,'utf8'));
const outside=(path,root)=>{const rel=relative(root,path);return rel==='..'||rel.startsWith('..'+sep)||isAbsolute(rel);};
const normalize=value=>String(value??'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[^a-z0-9]+/g,' ').trim();
const stopWords=new Set(['como','qual','quais','quanto','onde','que','uma','para','sobre','com','dos','das','por','tem','me','ajude','quero','jarvis','falar','explique','preciso']);
const npcNames={jarvis:'JARVIS',nurse:'Professora de enfermagem',guide:'Guia do campus'};

export function createPasswordVerifier(password){
  if(typeof password!=='string'||!password.length)throw new Error('Uma senha é necessária para criar o verificador.');
  const salt=randomBytes(24),N=16384,r=8,p=1,keyLength=64;
  return {algorithm:'scrypt',salt:salt.toString('base64'),hash:scryptSync(password,salt,keyLength,{N,r,p,maxmem:64*1024*1024}).toString('base64'),N,r,p,keyLength};
}
export const hashOwnerToken=token=>createHash('sha256').update(token).digest('hex');
function validVerifier(v){
  return v?.algorithm==='scrypt'&&v.keyLength===64&&[16384,32768,65536].includes(v.N)&&v.r===8&&v.p===1&&typeof v.salt==='string'&&Buffer.from(v.salt,'base64').length>=16&&Buffer.from(v.salt,'base64').length<=64&&typeof v.hash==='string'&&Buffer.from(v.hash,'base64').length===64;
}
export async function verifyPassword(password,verifier){
  if(typeof password!=='string'||password.length>1024||!validVerifier(verifier))return false;
  const actual=await deriveKey(password,Buffer.from(verifier.salt,'base64'),verifier.keyLength,{N:verifier.N,r:verifier.r,p:verifier.p,maxmem:128*1024*1024});
  return timingSafeEqual(actual,Buffer.from(verifier.hash,'base64'));
}
function loadConfig(configPath){
  if(!configPath)return null;
  const path=resolve(configPath);
  if(!outside(path,PROJECT))throw new Error('A configuração privada deve ficar fora do projeto.');
  const config=readJson(path);
  if(config.version!==1||!validVerifier(config.password)||!/^[a-f0-9]{64}$/i.test(config.ownerClaim?.tokenSha256??''))throw new Error('Configuração privada inválida.');
  if(config.assetPath&&(!isAbsolute(config.assetPath)||!outside(resolve(config.assetPath),PUBLIC)||!outside(resolve(config.assetPath),PROJECT)))throw new Error('O modelo privado deve ficar fora do projeto e dos assets públicos.');
  if(config.layout&&(typeof config.layout!=='object'||Array.isArray(config.layout)||JSON.stringify(config.layout).length>65536))throw new Error('Layout privado inválido.');
  return config;
}

export function createRpgServices({configPath=process.env.PREP_PRIVATE_HOME_CONFIG??(process.env.LOCALAPPDATA?resolve(process.env.LOCALAPPDATA,'PREPARATORIO/private-home.json'):null),book,drive,now=()=>Date.now(),unlockDurationMs=20*60*1000}={}){
  const studyBook=book??readJson(new URL('../frontend/src/config/studyBook.json',import.meta.url));
  const knowledge=drive??readJson(new URL('../frontend/src/config/knowledgeSources.json',import.meta.url));
  let config=null;
  try{config=loadConfig(configPath);}catch{/* Missing or malformed private config fails closed without logging paths or secrets. */}
  let ownerActorId=null;
  const unlocked=new Map(),attempts=new Map();
  const unavailable=()=>({ok:false,status:503,message:'O acesso privado ainda não foi configurado neste computador.'});
  const denied=()=>({ok:false,status:403,message:'Esta área pertence ao criador. A sessão não está autorizada.'});
  function throttle(actorId){
    const previous=attempts.get(actorId),time=now();
    const window=previous&&time-previous.since<60000?previous:{since:time,count:0};
    window.count++;attempts.set(actorId,window);return window.count<=8;
  }
  function authorization(session){
    if(!config)return unavailable();
    if(session.actorId!==ownerActorId)return denied();
    const expiresAt=unlocked.get(session.actorId)??0;
    if(now()>=expiresAt)return {ok:false,status:403,message:'Desbloqueie a área privada nesta sessão antes de entrar.'};
    return {ok:true,expiresAt};
  }
  function ask(question,npcId='jarvis'){
    if(typeof question!=='string'||!question.trim()||question.length>800)return {ok:false,status:400,message:'Escreva uma pergunta com até 800 caracteres.'};
    const clean=normalize(question),words=[...new Set(clean.split(' ').filter(w=>w.length>2&&!stopWords.has(w)))];
    if(/senha|password|ownertoken|token de acesso|chave secreta/.test(clean))return {ok:true,mode:'local-index',npc:{id:'jarvis',name:npcNames.jarvis},answer:'Use o formulário de acesso privado para senhas e códigos do criador. Essas informações não devem ser enviadas como perguntas nem pesquisas na web.',sources:[],links:[],scope:'Proteção de dados de acesso',clinicalReview:false};
    const score=text=>{const title=normalize(text);return words.reduce((value,w)=>value+(title.includes(w)?1:0),0);};
    const lessons=studyBook.lessons.map(lesson=>({lesson,score:score(lesson.title)*2+score(lesson.category)+(normalize(lesson.quiz?.question)===clean?20:0)})).filter(x=>x.score>0).sort((a,b)=>b.score-a.score||a.lesson.page-b.lesson.page).slice(0,5);
    const sources=lessons.map(({lesson})=>({type:'lesson',id:lesson.id,title:lesson.title,page:lesson.page,url:`${studyBook.url}#page=${lesson.page}`,scope:'indexed-title'}));
    const driveMatches=knowledge.items.map(item=>({item,score:score(item.title)})).filter(x=>x.score>0).sort((a,b)=>b.score-a.score).slice(0,5);
    for(const {item}of driveMatches)sources.push({type:'drive',id:item.id,title:item.title,url:item.url,scope:'indexed-title'});
    const clinical=/medicamento|medicacao|dosagem|prescrev|dose|diagnostic|tratamento|injec|gotejamento|paciente/.test(clean);
    const safeExercise=lessons.find(({lesson})=>lesson.category==='Matemática'&&lesson.quiz);
    let answer=sources.length?`Encontrei referências no acervo: ${sources.slice(0,5).map(s=>`${s.title}${s.page?` (página ${s.page})`:''}`).join('; ')}.`:'Não encontrei uma referência correspondente nos títulos indexados. Use a biblioteca ou as buscas abaixo para continuar a pesquisa.';
    if(safeExercise&&!clinical){const {lesson}=safeExercise;answer+=` Exercício de matemática do guia: ${lesson.quiz.question} Resposta: ${lesson.quiz.options[lesson.quiz.answer]}. ${lesson.quiz.explanation}`;sources.find(s=>s.id===lesson.id).scope='reviewed-math-exercise';}
    if(clinical)answer+=' Para uma questão clínica, leia a fonte com orientação docente e consulte protocolos atualizados; este índice não gera prescrição, diagnóstico ou instruções de procedimento.';
    answer+=' Sou um assistente de consulta ao índice local. Os títulos não substituem a leitura integral das fontes.';
    return {ok:true,mode:'local-index',npc:{id:npcNames[npcId]?npcId:'jarvis',name:npcNames[npcId]??npcNames.jarvis},answer,sources,links:[{title:'Pesquisar a pergunta na web',url:`https://www.google.com/search?q=${encodeURIComponent(question.trim())}`},{title:'Pesquisar em fontes públicas de saúde',url:`https://www.google.com/search?q=${encodeURIComponent(`${question.trim()} site:gov.br OR site:who.int`)}`}],scope:`${studyBook.lessons.length} títulos de aulas; ${studyBook.lessons.filter(l=>l.quiz).length} exercícios de matemática; ${knowledge.items.length} títulos do Drive. Textos clínicos não foram integralmente revisados.`,clinicalReview:false};
  }
  function claimOwner(session,ownerToken){
    if(!config)return unavailable();
    if(!throttle(session.actorId))return {ok:false,status:429,message:'Aguarde um minuto antes de tentar novamente.'};
    const valid=typeof ownerToken==='string'&&ownerToken.length>=32&&ownerToken.length<=512&&timingSafeEqual(Buffer.from(hashOwnerToken(ownerToken),'hex'),Buffer.from(config.ownerClaim.tokenSha256,'hex'));
    if(!valid)return denied();
    if(ownerActorId&&ownerActorId!==session.actorId)return {ok:false,status:409,message:'O acesso do criador já está vinculado a outra sessão deste servidor.'};
    ownerActorId=session.actorId;
    return {ok:true,ownerName:config.ownerName??'Romário',message:'Sessão do criador identificada. A senha ainda é necessária para abrir a área privada.'};
  }
  async function unlockHome(session,password){
    if(!config)return unavailable();
    if(!throttle(session.actorId))return {ok:false,status:429,message:'Aguarde um minuto antes de tentar novamente.'};
    if(!await verifyPassword(password,config.password))return {ok:false,status:403,message:'Senha incorreta. A área privada continua bloqueada.'};
    // The password proves creator access. Bind only the authenticated session,
    // never a player id supplied in a request body or the first person online.
    if(ownerActorId&&ownerActorId!==session.actorId&&(unlocked.get(ownerActorId)??0)>now())return {ok:false,status:409,message:'A casa do criador já está aberta em outra sessão. Feche essa sessão ou aguarde o fim do acesso.'};
    if(ownerActorId!==session.actorId)unlocked.clear();
    ownerActorId=session.actorId;
    const expiresAt=now()+unlockDurationMs;unlocked.set(session.actorId,expiresAt);
    return {ok:true,ownerName:config.ownerName??'Romário',expiresAt,message:'Área privada desbloqueada para esta sessão.'};
  }
  function privateHomeLayout(session){
    const access=authorization(session);if(!access.ok)return access;
    let assetAvailable=false;
    try{assetAvailable=Boolean(config.assetPath&&statSync(config.assetPath).isFile());}catch{/* A missing private model does not reveal its host path. */}
    return {ok:true,ownerName:config.ownerName??'Romário',layout:config.layout??{roomName:'Casa privada do criador',spawn:[0,0,3]},assetAvailable,assetUrl:assetAvailable?'/rpg/home/asset':null,expiresAt:access.expiresAt};
  }
  function privateHomeAsset(session){
    const access=authorization(session);if(!access.ok)return access;
    try{
      const bytes=readFileSync(config.assetPath);
      if(bytes.length<12||bytes.toString('ascii',0,4)!=='glTF'||bytes.readUInt32LE(8)!==bytes.length)return {ok:false,status:503,message:'O modelo privado precisa ser validado antes de abrir.'};
      return {ok:true,bytes};
    }catch{return {ok:false,status:503,message:'O modelo privado ainda não está disponível.'};}
  }
  return {ask,claimOwner,unlockHome,privateHomeLayout,privateHomeAsset};
}
