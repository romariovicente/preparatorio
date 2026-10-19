// Serializable commands: a future authoritative server can apply the same ownership,
// revision and placement rules. This prototype applies them in the current browser.
export const INTERACTION_VERSION = 1;
const near = (a, b, distance) => Math.hypot(a.x - b.x, a.z - b.z) <= distance;
const finitePosition = p => p && [p.x, p.y ?? 0, p.z].every(Number.isFinite);
const point = p => ({x:p.x, y:p.y ?? 0, z:p.z});

export function getLocalPlayerId(storage) {
  try {
    const saved = storage?.getItem('prep.player.v1');
    if (saved && /^player-[a-zA-Z0-9-]{8,80}$/.test(saved)) return saved;
    const id = `player-${globalThis.crypto?.randomUUID?.() ?? Math.random().toString(36).slice(2)+Date.now().toString(36)}`;
    storage?.setItem('prep.player.v1',id);
    return id;
  } catch { return `player-session-${Math.random().toString(36).slice(2)}`; }
}

export function createInteractionState(templates) {
  return {version:INTERACTION_VERSION, objects:templates.map(t => ({
    id:`base:${t.id}`, templateId:t.id, kind:'base', ownerId:null,
    position:point(t.position), carriedBy:null, revision:0, uses:0,
  })), players:{}, processedIds:[]};
}

export function carriedObject(state, actorId) {
  return state.objects.find(o => o.id === state.players[actorId]?.carriedId && o.carriedBy === actorId) ?? null;
}

export function placementAllowed(position, options = {}, ignoreId = null, objects = []) {
  if (!finitePosition(position)) return false;
  if(Math.abs((position.y ?? 0)-(options.floorY ?? 0))>.05)return false;
  const bounds = options.bounds ?? {minX:-9,maxX:9,minZ:-8,maxZ:9};
  if (position.x < bounds.minX || position.x > bounds.maxX || position.z < bounds.minZ || position.z > bounds.maxZ) return false;
  const radius = options.placementRadius ?? .45;
  if ((options.obstacles ?? []).some(o => Math.abs(position.x-o.x) < o.w/2+radius && Math.abs(position.z-o.z) < o.d/2+radius)) return false;
  return !objects.some(o => o.id !== ignoreId && o.position && Math.hypot(position.x-o.position.x,position.z-o.position.z) < radius*2);
}

export function reduceInteraction(state, command, options) {
  const {templates, playerPosition} = options;
  const verticallyNear = p => Math.abs((playerPosition.y ?? 0)-(p?.y ?? 0)) <= (options.maxVerticalReach ?? Infinity);
  const fail = message => ({state,ok:false,message});
  if (!command || !command.actorId || !command.eventId || typeof command.eventId !== 'string') return fail('A ação precisa identificar o jogador e a solicitação.');
  if (state.processedIds.includes(command.eventId)) return fail('Esta ação já foi processada.');
  if (!finitePosition(playerPosition)) return fail('A posição do jogador está indisponível.');
  const actorId = command.actorId;
  const object = state.objects.find(o => o.id === command.objectId);
  const template = templates.find(t => t.id === object?.templateId);
  if (!object || !template) return fail('Objeto indisponível.');
  if (command.expectedRevision !== undefined && command.expectedRevision !== object.revision) return fail('O objeto mudou. Selecione-o novamente.');
  if (object.kind === 'copy' && object.ownerId !== actorId) return fail('Esta cópia pertence a outro jogador.');
  if (object.carriedBy && object.carriedBy !== actorId) return fail('Outro jogador está carregando este objeto.');
  const usingCarried = ['USE','INSPECT','RETURN'].includes(command.type) && object.carriedBy === actorId;
  if (command.type !== 'DROP' && !usingCarried && (!object.position || !verticallyNear(object.position) || !near(playerPosition,object.position,options.reach ?? 2.25))) return fail('Aproxime o personagem do objeto para interagir.');
  let objects = state.objects;
  let players = state.players;
  let message;
  let createdId = null;
  const update = fields => {objects = objects.map(o => o.id === object.id ? {...o,...fields,revision:o.revision+1} : o);};
  if (command.type === 'PICKUP') {
    if (!template.portable) return fail('Este objeto pode ser reposicionado, mas não carregado.');
    if (carriedObject(state,actorId)) return fail('Solte o objeto que você está carregando primeiro.');
    let item = object;
    if (object.kind === 'base') {
      if (objects.filter(o => o.kind === 'copy' && o.ownerId === actorId).length >= (options.maxCopies ?? 20)) return fail('Recolha uma das suas cópias já colocadas no chão.');
      item = {...object,id:`item:${actorId}:${command.eventId}`,kind:'copy',ownerId:actorId,position:null,carriedBy:actorId,revision:0,uses:0};
      objects = [...objects,item];
      createdId = item.id;
      message = `Você está carregando uma cópia de ${template.name}. O objeto base continua disponível.`;
    } else {
      update({position:null,carriedBy:actorId});
      message = `Você recolheu sua cópia de ${template.name}.`;
    }
    players = {...players,[actorId]:{...players[actorId],carriedId:item.id}};
  } else if (command.type === 'DROP') {
    if (carriedObject(state,actorId)?.id !== object.id) return fail('Você não está carregando este objeto.');
    if (!verticallyNear(command.position) || !near(playerPosition,command.position ?? {},options.dropReach ?? 2)) return fail('Escolha uma posição próxima do personagem.');
    if (!placementAllowed(command.position,options,object.id,objects)) return fail('Esse espaço está ocupado ou fora da área permitida.');
    update({position:point(command.position),carriedBy:null});
    players = {...players,[actorId]:{...players[actorId],carriedId:null}};
    message = `${template.name} colocado no chão. Sua cópia pode ser recolhida novamente.`;
  } else if (command.type === 'MOVE') {
    if (!template.movable || object.carriedBy) return fail('Este objeto não pode ser reposicionado agora.');
    if (!verticallyNear(command.position) || !near(playerPosition,command.position ?? {},options.moveReach ?? 3)) return fail('Mova o personagem para mais perto do destino.');
    if (!placementAllowed(command.position,options,object.id,objects)) return fail('Esse espaço está ocupado ou fora da área permitida.');
    if(object.kind === 'base'){
      if(objects.filter(o=>o.kind==='copy'&&o.ownerId===actorId).length >= (options.maxCopies ?? 20))return fail('Devolva uma das suas cópias para liberar espaço.');
      const copy={...object,id:`item:${actorId}:${command.eventId}`,kind:'copy',ownerId:actorId,position:point(command.position),revision:0,uses:0};
      objects=[...objects,copy];createdId=copy.id;
      message=`Uma cópia de ${template.name} foi posicionada. O objeto base continua disponível.`;
    }else{
      update({position:point(command.position)});
      message=`Sua cópia de ${template.name} foi reposicionada.`;
    }
  } else if (command.type === 'USE') {
    if(object.kind==='copy')update({uses:object.uses+1});
    message = template.actionText ?? `${template.name} examinado.`;
  } else if(command.type === 'RETURN'){
    if(object.kind !== 'copy' || object.ownerId !== actorId)return fail('Apenas suas cópias podem ser devolvidas.');
    objects=objects.filter(o=>o.id!==object.id);
    if(players[actorId]?.carriedId===object.id)players={...players,[actorId]:{...players[actorId],carriedId:null}};
    message=`Sua cópia de ${template.name} foi devolvida. O objeto base continua disponível.`;
  } else if (command.type === 'INSPECT') {
    message = template.description ?? template.name;
  } else return fail('Ação desconhecida.');
  return {ok:true,message,createdId,state:{...state,objects,players,processedIds:[...state.processedIds,command.eventId].slice(-100)}};
}

export function restoreInteractionState(value, templates, actorId, options = {}) {
  const fresh = createInteractionState(templates);
  if (!value || value.version !== INTERACTION_VERSION || !Array.isArray(value.objects)) return fresh;
  const known = new Set(templates.map(t => t.id));
  const safe = o => o && known.has(o.templateId) && typeof o.id === 'string' && Number.isInteger(o.revision) && o.revision >= 0 && (o.position === null || finitePosition(o.position));
  const bases = fresh.objects.map(base => {
    if (!templates.find(t => t.id === base.templateId)?.movable) return base;
    const saved = value.objects.find(o => o.id === base.id && o.kind === 'base' && safe(o) && o.position);
    return saved ? {...base,position:placementAllowed(saved.position,options)?point(saved.position):base.position,revision:saved.revision,uses:Number.isInteger(saved.uses)?Math.max(0,saved.uses):0} : base;
  });
  const copies = value.objects.filter(o => safe(o) && o.kind === 'copy' && o.ownerId === actorId && o.id.startsWith(`item:${actorId}:`)).slice(0,options.maxCopies ?? 20).map(o => ({
    id:o.id,templateId:o.templateId,kind:'copy',ownerId:actorId,
    position:o.position && placementAllowed(o.position,options)?point(o.position):null,
    carriedBy:o.carriedBy === actorId ? actorId : null,revision:o.revision,uses:Number.isInteger(o.uses)?Math.max(0,o.uses):0,
  })).filter(o => o.position || o.carriedBy);
  const held = copies.find(o => o.carriedBy === actorId);
  for (const copy of copies) if (copy !== held && copy.carriedBy) {copy.carriedBy=null;copy.position={x:0,y:0,z:0};}
  return {...fresh,objects:[...bases,...copies],players:{[actorId]:{carriedId:held?.id ?? null}}};
}
