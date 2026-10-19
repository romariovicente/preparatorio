import http from 'node:http';
import { randomUUID } from 'node:crypto';
import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createInteractionState, reduceInteraction } from '../frontend/src/world/interactionState.js';
import { interactionRooms } from '../frontend/src/network/roomConfig.js';
import { createRpgServices } from './rpgServices.js';
import {doorPosition,doorwayOccupied} from '../frontend/src/cyber/doorGeometry.js';
import {normalizePlayerName,normalizePlayerOutfit} from '../frontend/src/network/playerIdentity.js';
const buildings=JSON.parse(readFileSync(new URL('../frontend/src/config/buildingDoors.json',import.meta.url),'utf8'));

const allowedOrigins = new Set(['http://127.0.0.1:5173','http://localhost:5173']);
const allowedActions = new Set(['PICKUP','DROP','MOVE','USE','INSPECT','RETURN']);
const allowedAnimations = new Set(['Idle','Walk','Dance','Interact','Gesture','Carry','Use','Armature|Idle','Armature|Walk']);
const characterIds = new Set(JSON.parse(readFileSync(new URL('../frontend/src/config/suppliedAssets.json', import.meta.url), 'utf8')).filter(a => a.category === 'Personagens').map(a => a.id));
const mixamoMetadataUrl = new URL('../frontend/src/config/mixamoAssets.json', import.meta.url);
if (existsSync(mixamoMetadataUrl)) {
  for (const asset of JSON.parse(readFileSync(mixamoMetadataUrl, 'utf8'))) {
    if (asset.reimportValidated && asset.rigged && asset.playable) characterIds.add(asset.id);
  }
}
const safeId = value => typeof value === 'string' && /^[A-Za-z0-9_:.-]{1,180}$/.test(value);
const finitePoint = p => p && [p.x,p.y ?? 0,p.z].every(Number.isFinite);

async function readBody(request) {
  let raw = '';
  for await (const chunk of request) {
    raw += chunk;
    if (raw.length > 16384) throw new Error('Solicitação grande demais.');
  }
  try { return JSON.parse(raw || '{}'); } catch { throw new Error('Solicitação JSON inválida.'); }
}

export function createDemoServer({rpgConfigPath,rpgNow}={}) {
  const sessions = new Map();
  const rpg=createRpgServices({configPath:rpgConfigPath,now:rpgNow});
  const rooms = new Map(Object.entries(interactionRooms).map(([name,config]) => [name,{ config,state:createInteractionState(config.templates),revision:0,subscribers:new Set() }]));
  rooms.get('cyber').state.doors=Object.fromEntries(buildings.map(b=>[b.id,{open:false,revision:0}]));
  const snapshot = room => ({ state:room.state,revision:room.revision });
  const broadcast = room => {
    const text = `event: snapshot\ndata: ${JSON.stringify(snapshot(room))}\n\n`;
    for (const response of room.subscribers) response.write(text);
  };
  const join = (room,session) => {
    if (!room.state.players[session.actorId]) {
      room.state = { ...room.state,players:{ ...room.state.players,[session.actorId]:{ carriedId:null,position:{ ...room.config.start },animation:'Idle',heading:0,characterId:null,online:false } } };
      room.revision++;
    }
  };
  const server = http.createServer(async (request,response) => {
    const origin = request.headers.origin;
    if (origin && !allowedOrigins.has(origin)) {
      response.writeHead(403,{'Content-Type':'application/json'}); response.end(JSON.stringify({ok:false,message:'Origem não autorizada para a demonstração local.'})); return;
    }
    if (origin) response.setHeader('Access-Control-Allow-Origin',origin);
    response.setHeader('Vary','Origin');
    response.setHeader('Cache-Control','no-store');
    response.setHeader('Access-Control-Allow-Headers','Authorization, Content-Type');
    response.setHeader('Access-Control-Allow-Methods','GET, POST, OPTIONS');
    const send = (code,data) => { response.writeHead(code,{'Content-Type':'application/json; charset=utf-8'}); response.end(JSON.stringify(data)); };
    if (request.method === 'OPTIONS') { response.writeHead(204);response.end();return; }
    const url = new URL(request.url,'http://127.0.0.1');
    if (request.method === 'GET' && url.pathname === '/health') { send(200,{ok:true,mode:'local-demo',rooms:[...rooms.keys()],sessions:sessions.size,serverTimeMs:Date.now(),timeZone:'America/Sao_Paulo'});return; }
    try {
      if (request.method === 'POST' && url.pathname === '/session') {
        const body = await readBody(request);
        let session = sessions.get(body.token);
        if (!session) {
          if (sessions.size >= 64) { send(429,{ok:false,message:'Limite de sessões desta demonstração atingido. Reinicie o servidor local.'});return; }
          session = {token:randomUUID(),actorId:`player-${randomUUID()}`,lastSeen:Date.now()};
          sessions.set(session.token,session);
        }
        session.lastSeen = Date.now();
        send(200,{ok:true,token:session.token,actorId:session.actorId});return;
      }
      const token = /^Bearer (.+)$/.exec(request.headers.authorization ?? '')?.[1];
      const session = sessions.get(token);
      if (!session) { send(401,{ok:false,message:'Abra uma sessão local antes de interagir.'});return; }
      session.lastSeen = Date.now();
      if(url.pathname.startsWith('/rpg/')){
        let result;
        if(request.method==='POST'&&url.pathname==='/rpg/ask'){
          const body=await readBody(request);result=rpg.ask(body.question,body.npcId);
        }else if(request.method==='POST'&&url.pathname==='/rpg/owner/claim'){
          const body=await readBody(request);result=rpg.claimOwner(session,body.ownerToken);
        }else if(request.method==='POST'&&url.pathname==='/rpg/home/unlock'){
          const body=await readBody(request);result=await rpg.unlockHome(session,body.password);
        }else if(request.method==='GET'&&url.pathname==='/rpg/home/layout'){
          result=rpg.privateHomeLayout(session);
        }else if(request.method==='GET'&&url.pathname==='/rpg/home/asset'){
          result=rpg.privateHomeAsset(session);
          if(result.ok){response.writeHead(200,{'Content-Type':'model/gltf-binary','Content-Length':result.bytes.length,'X-Content-Type-Options':'nosniff'});response.end(result.bytes);return;}
        }else {send(404,{ok:false,message:'Rota indisponível.'});return;}
        send(result.status??(result.ok?200:400),result);return;
      }
      if (request.method === 'GET' && ['/snapshot','/events'].includes(url.pathname)) {
        const room = rooms.get(url.searchParams.get('room'));
        if (!room) { send(400,{ok:false,message:'Sala desconhecida.'});return; }
        join(room,session);
        if (url.pathname === '/snapshot') { send(200,{ok:true,...snapshot(room),actorId:session.actorId});return; }
        response.writeHead(200,{'Content-Type':'text/event-stream; charset=utf-8','Connection':'keep-alive','X-Accel-Buffering':'no'});
        room.subscribers.add(response);
        room.state = {...room.state,players:{...room.state.players,[session.actorId]:{...room.state.players[session.actorId],online:true}}};room.revision++;
        broadcast(room);
        const heartbeat = setInterval(() => response.write(': local heartbeat\n\n'),15000);
        request.on('close',() => {
          clearInterval(heartbeat);room.subscribers.delete(response);
          if (![...room.subscribers].some(r => r.actorId === session.actorId)) {
            room.state = {...room.state,players:{...room.state.players,[session.actorId]:{...room.state.players[session.actorId],online:false}}};room.revision++;broadcast(room);
          }
        });
        response.actorId = session.actorId;
        return;
      }
      if(request.method==='POST'&&url.pathname==='/door'){
        const body=await readBody(request),room=rooms.get(body.room),building=buildings.find(b=>b.id===body.doorId);
        if(body.room!=='cyber'||!room||!building||typeof body.open!=='boolean'){send(400,{ok:false,message:'Porta inválida.'});return;}
        join(room,session);
        const player=room.state.players[session.actorId],p=player.position,target=doorPosition(building);
        if(Math.hypot(p.x-target[0],p.z-target[2])>5||Math.abs((p.y??0)-target[1])>1.5){send(409,{ok:false,message:'Aproxime-se da porta para abrir ou fechar.',...snapshot(room)});return;}
        if(!body.open&&doorwayOccupied(room.state.players,building)){send(409,{ok:false,message:'A passagem está ocupada. Afaste-se para fechar a porta.',...snapshot(room)});return;}
        const current=room.state.doors[building.id];
        room.state={...room.state,doors:{...room.state.doors,[building.id]:{open:body.open,revision:current.revision+1,changedAtMs:Date.now()}}};room.revision++;broadcast(room);
        send(200,{ok:true,message:body.open?'Porta aberta. Você pode entrar.':'Porta fechada.',...snapshot(room)});return;
      }
      if (request.method === 'POST' && ['/action','/position'].includes(url.pathname)) {
        const body = await readBody(request);
        const room = rooms.get(body.room);
        if (!room) { send(400,{ok:false,message:'Sala desconhecida.'});return; }
        join(room,session);
        const player = room.state.players[session.actorId];
        if (url.pathname === '/position') {
          const p = body.position,bounds = room.config.positionBounds ?? room.config.options.bounds;
          const minY=room.config.minY ?? -1,maxY=room.config.maxY ?? 1;
          if (!finitePoint(p) || (p.y ?? 0) < minY || (p.y ?? 0) > maxY || p.x < bounds.minX || p.x > bounds.maxX || p.z < bounds.minZ || p.z > bounds.maxZ) { send(400,{ok:false,message:'Posição fora da área da demonstração.'});return; }
          const animation = allowedAnimations.has(body.animation) ? body.animation : player.animation;
          const heading = Number.isFinite(body.heading) ? Math.atan2(Math.sin(body.heading),Math.cos(body.heading)) : player.heading;
          const characterId = characterIds.has(body.characterId) ? body.characterId : player.characterId;
          const displayName=body.displayName===undefined?player.displayName:normalizePlayerName(body.displayName);
          const outfit=body.outfit===undefined?player.outfit:normalizePlayerOutfit(body.outfit);
          const sitting=body.sitting===undefined?Boolean(player.sitting):body.sitting===true;
          const mode=['foot','car','mototaxi','truck','tractor','harvester','bus','bus-brt','train'].includes(body.mode)?body.mode:player.mode??'foot';
          const jumpHeight=Number.isFinite(body.jumpHeight)?Math.max(0,Math.min(2,body.jumpHeight)):player.jumpHeight??0;
          room.state = {...room.state,players:{...room.state.players,[session.actorId]:{...player,position:{x:p.x,y:p.y ?? 0,z:p.z},animation,heading,characterId,displayName,outfit,sitting,mode,jumpHeight}}};room.revision++;broadcast(room);
          send(200,{ok:true,revision:room.revision});return;
        }
        if (!allowedActions.has(body.type) || !safeId(body.eventId) || !safeId(body.objectId) || (body.expectedRevision !== undefined && (!Number.isInteger(body.expectedRevision) || body.expectedRevision < 0))) { send(400,{ok:false,message:'Ação inválida.'});return; }
        if (body.position !== undefined && (!finitePoint(body.position) || Math.abs(body.position.y ?? 0) > .001)) { send(400,{ok:false,message:'Escolha um destino no piso da sala.'});return; }
        const object = room.state.objects.find(o => o.id === body.objectId);
        const template = room.config.templates.find(t => t.id === object?.templateId);
        if (['MOVE','DROP'].includes(body.type) && body.position && object && template && room.config.validatePlacement && !room.config.validatePlacement(body.position,template,room.state,object,session.actorId)) {
          send(409,{ok:false,message:'O destino bloquearia camas, balcão ou outro objeto.',...snapshot(room)});return;
        }
        if (['PICKUP','MOVE'].includes(body.type) && object?.kind === 'base' && room.state.objects.filter(o => o.kind === 'copy').length >= 256) { send(429,{ok:false,message:'Limite de cópias da sala atingido.',...snapshot(room)});return; }
        // The authenticated session is the only source of ownership identity.
        const command = {type:body.type,objectId:body.objectId,eventId:`${session.actorId}:${body.eventId}`,actorId:session.actorId,expectedRevision:body.expectedRevision,position:body.position};
        const result = reduceInteraction(room.state,command,{...room.config.options,templates:room.config.templates,playerPosition:player.position});
        if (result.ok) { room.state=result.state;room.revision++;broadcast(room); }
        send(result.ok ? 200 : 409,{...result,...snapshot(room)});return;
      }
      send(404,{ok:false,message:'Rota indisponível.'});
    } catch (error) { send(400,{ok:false,message:error.message}); }
  });
  server.on('close',() => { for (const room of rooms.values()) for (const response of room.subscribers) response.end(); });
  server.closeDemo = async () => {
    for (const room of rooms.values()) for (const response of room.subscribers) response.end();
    const closing=new Promise((done,reject) => server.close(error => error ? reject(error) : done()));
    server.closeAllConnections();
    await closing;
  };
  return server;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const server = createDemoServer();
  server.listen(5180,'127.0.0.1',() => console.log('PREPARATÓRIO: demonstração compartilhada local em http://127.0.0.1:5180'));
  process.on('SIGINT',() => { server.closeDemo().then(() => process.exit(0)); });
}
