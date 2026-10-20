import {resolveAssetReferences} from '../config/deploymentConfig.js';
import {resolveCarSource,safeVehicleCopy,canEnterCar} from './carInteraction.js';
import {resolveMotorcycle,nearestMotorcycle} from './motorcycleInteraction.js';
import {playableCityBounds} from '../config/cityBounds.js';
import deliveryConfigRaw from '../config/newDeliveryWorld.json' with {type:'json'};
const deliveryConfig=resolveAssetReferences(deliveryConfigRaw);
import {BUS_IDS,BUS_BRT_ROUTE,BUS_DEFINITIONS,createLiveBuses,sampleLiveBus,canBoardBus,busSeatPosition,busExitPosition,busMotion,busPositionBlocked,moveLiveBus,returnBusToRoute,tickLiveBuses} from './busInteraction.js';
export {BUS_IDS,BUS_BRT_ROUTE,BUS_DEFINITIONS,sampleLiveBus,nearestBus,busSeatPosition,busDoorPosition,busFootprint} from './busInteraction.js';
export const CYBER_STORAGE_KEY = 'prep.cyber.local.v1';
export const CYBER_BOUNDS = playableCityBounds;
// Clear approach south of the plaza's outer 20 m ring and its monuments.
export const CITY_START = { x: 0, y: 0, z: 25 };
export const JUMP_PHYSICS={velocity:6.2,gravity:18};
export const ELEVATOR_POSITION = { x:-17, y:0, z:56 };
export const DRIVE_VEHICLES = {
  car:{id:'car',label:'Carro esportivo',position:{x:20,y:0,z:44},seat:.45,speed:14,farmOnly:false},
  tractor:{id:'tractor',label:'Trator',position:{x:12,y:0,z:96},seat:1.2,speed:9,farmOnly:true},
  harvester:{id:'harvester',label:'Colheitadeira',position:{x:-12,y:0,z:96},seat:1.5,speed:7,farmOnly:true},
  mototaxi:{id:'mototaxi',label:'Mototáxi',position:{x:-40,y:0,z:40},seat:.7,speed:10,farmOnly:false},
  truck:{id:'truck',label:'Caminhão',position:{x:90,y:0,z:50},seat:1.5,speed:8,farmOnly:false},
};
export const DEFAULT_PARKING = [
  {id:'park-store',label:'Estacionamento da loja',position:[-40,0,44]},
  {id:'park-hangar',label:'Estacionamento do hangar',position:[72,0,75]},
  {id:'park-farm',label:'Estacionamento da fazenda',position:[12,0,98]},
];
export const WORLD_CLOCK_DEFAULTS = { epochMs:1791201600000, orbitPeriodSeconds:120, dayPeriodSeconds:240, orbitRadius:14, sunCenter:[0,55,0] };
export const FARM_PLOTS = [-8, -3, 3, 8].map((x, index) => ({ id: `plot-${index + 1}`, position: { x, y: 0, z: 104 } }));
export const FLOWER_BASES = [[-8,14],[-5,15],[7,14],[11,12]].map(([x,z], index) => ({ id: `flower-${index + 1}`, position: { x, y: 0, z } }));
export const TRANSIT_ROUTES = {
  bus: { id: 'bus', label: 'Ônibus circular', speed: 10, dwell: 9, points: [
    {x:0,z:35},{x:105,z:35},{x:105,z:-45},{x:105,z:-75},{x:-80,z:-75},{x:-80,z:35},{x:-45,z:35},
  ], stops: [
    { id: 'plaza', label: 'Praça PREP', position: {x:0,y:0,z:35} },
    { id: 'hospital', label: 'Hospital', position: {x:105,y:0,z:-45} },
    { id: 'station', label: 'Estação', position: {x:-80,y:0,z:-75} },
    { id: 'store', label: 'Loja', position: {x:-45,y:0,z:35} },
  ] },
  train: { id: 'train', label: 'Trem regional de demonstração', speed: 16, dwell: 10, points:[
    {x:-70,z:-103},{x:102,z:-103},{x:117,z:-88},{x:117,z:65},{x:117,z:92},{x:100,z:114},{x:0,z:114},{x:-97,z:114},{x:-115,z:96},{x:-115,z:-85},{x:-95,z:-103},
  ], stops: [
    { id: 'station', label: 'Estação Arapiraca', position: {x:-70,y:0,z:-103} },
    { id: 'farm', label: 'Terminal agrícola', position: {x:0,y:0,z:114} },
    { id: 'hangar', label: 'Terminal do hangar', position: {x:117,y:0,z:65} },
  ] },
  ...deliveryConfig.routeOverrides,
  'bus-brt':BUS_BRT_ROUTE,
};
const clamp = (value, min, max) => Math.min(max, Math.max(min, value));
const distance = (a, b) => Math.hypot(a.x - b.x, a.z - b.z);
const finitePoint = point => point && [point.x, point.y ?? 0, point.z].every(Number.isFinite);

// One accelerated, educational clock drives the planetarium, sky phase,
// phone and billboard. It is not an astronomical position calculation.
export function sampleWorldClock(elapsedSeconds = 0, config = WORLD_CLOCK_DEFAULTS) {
  const safeSeconds = Math.max(0, Number.isFinite(elapsedSeconds) ? elapsedSeconds : 0);
  const daySeconds = config.dayPeriodSeconds > 0 ? config.dayPeriodSeconds : WORLD_CLOCK_DEFAULTS.dayPeriodSeconds;
  const orbitSeconds = config.orbitPeriodSeconds > 0 ? config.orbitPeriodSeconds : WORLD_CLOCK_DEFAULTS.orbitPeriodSeconds;
  const epochMs = Number.isFinite(config.epochMs) ? config.epochMs : WORLD_CLOCK_DEFAULTS.epochMs;
  const sun = Array.isArray(config.sunCenter) && config.sunCenter.length === 3 ? config.sunCenter : WORLD_CLOCK_DEFAULTS.sunCenter;
  const radius = config.orbitRadius > 0 ? config.orbitRadius : WORLD_CLOCK_DEFAULTS.orbitRadius;
  if(config.clockMode==='server-wall') {
    const nowMs=Number.isFinite(config.nowMs)&&Math.abs(config.nowMs)<=8.64e15?config.nowMs:epochMs;
    const timeZone=config.timeZone??'America/Sao_Paulo';
    let formatter;
    try { formatter=new Intl.DateTimeFormat('pt-BR',{timeZone,year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}); }
    catch { formatter=new Intl.DateTimeFormat('pt-BR',{timeZone:'America/Sao_Paulo',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}); }
    const parts=Object.fromEntries(formatter.formatToParts(nowMs).map(part=>[part.type,part.value]));
    const hour=Number(parts.hour),minute=Number(parts.minute),night=hour<6||hour>=18;
    const worldSeconds=(nowMs-epochMs)/1000;
    const earthAngle=((worldSeconds/orbitSeconds*Math.PI*2)%(Math.PI*2)+Math.PI*2)%(Math.PI*2);
    return {clockMode:'server-wall',nowMs,elapsedSeconds:worldSeconds,day:Math.floor(worldSeconds/86400),hour,minute,text:`${parts.hour}:${parts.minute}`,
      phase:night?'Noite':hour<12?'Manhã':'Tarde',night,earthAngle,
      earthPosition:[sun[0]+Math.cos(earthAngle)*radius,sun[1],sun[2]+Math.sin(earthAngle)*radius],
      sunCenter:sun,orbitRadius:radius,dateText:`${parts.day}/${parts.month}/${parts.year}`,
      subtitle:'Horário de Brasília · órbitas em escala didática'};
  }
  const initialDate = new Date(epochMs - 3 * 3600000), initialHour = initialDate.getUTCHours() + initialDate.getUTCMinutes() / 60;
  const totalHours = initialHour + safeSeconds / daySeconds * 24;
  const hour = Math.floor(totalHours % 24), minute = Math.floor((totalHours * 60) % 60);
  const day = Math.floor(totalHours / 24);
  const earthAngle = (safeSeconds / orbitSeconds * Math.PI * 2) % (Math.PI * 2);
  const date = new Date(epochMs - 3 * 3600000 + safeSeconds / daySeconds * 86400000);
  const night = hour < 6 || hour >= 18;
  return { elapsedSeconds: safeSeconds, day, hour, minute, text: `${String(hour).padStart(2,'0')}:${String(minute).padStart(2,'0')}`,
    phase: night ? 'Noite' : hour < 12 ? 'Manhã' : 'Tarde', night, earthAngle,
    earthPosition: [sun[0] + Math.cos(earthAngle) * radius, sun[1], sun[2] + Math.sin(earthAngle) * radius],
    sunCenter:sun, orbitRadius:radius, dateText:`${String(date.getUTCDate()).padStart(2,'0')}/${String(date.getUTCMonth()+1).padStart(2,'0')}/${date.getUTCFullYear()}`,
    subtitle: 'Relógio e órbita acelerados · esquema didático',
  };
}

export function sampleTransit(route, elapsedSeconds) {
  const points=route.points ?? route.stops.map(stop=>stop.position);
  const legs = points.map((position, index) => {
    const stop=route.stops.find(item=>distance(item.position,position)<.01), next=points[(index+1)%points.length];
    const nextStop=Array.from({length:points.length},(_,offset)=>points[(index+offset+1)%points.length]).map(point=>route.stops.find(item=>distance(item.position,point)<.01)).find(Boolean);
    let afterTravel=0,cursor=(index+1)%points.length;
    for(let count=0;count<points.length&&!route.stops.some(item=>distance(item.position,points[cursor])<.01);count++){
      const following=(cursor+1)%points.length;afterTravel+=distance(points[cursor],points[following])/route.speed;cursor=following;
    }
    return {position,next,stop,nextStop,afterTravel,travel:distance(position,next)/route.speed,dwell:stop?route.dwell:0};
  });
  const cycle = legs.reduce((sum, leg) => sum + leg.dwell + leg.travel, 0);
  let time = ((elapsedSeconds % cycle) + cycle) % cycle;
  for (const leg of legs) {
    if (time < leg.dwell) return { ...leg.stop.position, heading: Math.atan2(leg.next.x-leg.position.x, leg.next.z-leg.position.z),
      stopped: true, stopId: leg.stop.id, stopLabel: leg.stop.label, nextStop: leg.nextStop.label, remaining: Math.ceil(leg.dwell-time) };
    time -= leg.dwell;
    if (time < leg.travel) {
      const fraction = time / leg.travel;
      return { x:leg.position.x+(leg.next.x-leg.position.x)*fraction, y:0, z:leg.position.z+(leg.next.z-leg.position.z)*fraction,
        heading:Math.atan2(leg.next.x-leg.position.x,leg.next.z-leg.position.z), stopped:false,
        stopId:null, stopLabel:'Em movimento', nextStop:leg.nextStop.label, remaining:Math.ceil(leg.travel-time+leg.afterTravel) };
    }
    time -= leg.travel;
  }
  return sampleTransit(route, 0);
}

export function advanceCityPosition(position, direction, delta, speed = 5, obstacles = [],radius=.4) {
  if (!finitePoint(position) || !finitePoint(direction)) return {...CITY_START};
  const length = Math.hypot(direction.x, direction.z), step = clamp(delta, 0, .05) * speed;
  if (!length) return {...position};
  const allowed = (x,z) => !obstacles.some(o => Math.abs(x-o.x)<o.w/2+radius && Math.abs(z-o.z)<o.d/2+radius);
  const x = clamp(position.x+direction.x/length*step,CYBER_BOUNDS.minX,CYBER_BOUNDS.maxX);
  const z = clamp(position.z+direction.z/length*step,CYBER_BOUNDS.minZ,CYBER_BOUNDS.maxZ);
  return {x:allowed(x,position.z)?x:position.x,y:position.y ?? 0,z:allowed(allowed(x,position.z)?x:position.x,z)?z:position.z};
}

export function createCyberState() {
  return { version:1, elapsed:0, position:{...CITY_START}, heading:0, mode:'foot', sitting:false, action:'Idle',
    outfit:{ scrubs:true, coat:false, color:'#247fba' }, inventory:{ flowers:0, fish:0, seeds:6, harvest:0 },
    plots:Object.fromEntries(FARM_PLOTS.map(plot => [plot.id,null])), flowerCooldowns:{}, fishing:null, fishingAttempts:0, elevator:null, jump:null,jumpHeight:0,jumpCount:0, personalVehicles:{}, garage:{}, liveBuses:createLiveBuses(),busControls:{vehicleId:null,role:null},motorcycleControls:{engineOn:false}, carControls:{doorOpen:false,engineOn:false,windowsOpen:false}, trailer:'flatbed', lastMessage:'Bem-vindo a Arapiraca PREP.' };
}

export function tickCyberState(state, delta, context={}) {
  const elapsed = state.elapsed + clamp(delta,0,.5);
  const liveBuses=tickLiveBuses(state,clamp(delta,0,.5),elapsed,context.obstacles);
  let position = state.position;
  let heading=state.heading;
  if(BUS_IDS.includes(state.mode)){
    const bus=liveBuses[state.mode];position=busSeatPosition(bus,state.busControls?.role);heading=bus.heading;
  }else if (TRANSIT_ROUTES[state.mode]) {
    const vehicle = sampleTransit(TRANSIT_ROUTES[state.mode], elapsed);
    position = {x:vehicle.x,y:1.1,z:vehicle.z};
  }
  let elevator = state.elevator;
  let jump=state.jump,jumpHeight=0;
  if(jump){const flight=elapsed-jump.startedAt;jumpHeight=Math.max(0,JUMP_PHYSICS.velocity*flight-JUMP_PHYSICS.gravity*flight*flight/2);if(flight>0&&jumpHeight===0)jump=null;}
  if (elevator) {
    const progress = clamp((elapsed-elevator.startedAt)/4,0,1), y = elevator.from+(elevator.to-elevator.from)*progress;
    position = {...position,y};
    if (progress === 1) elevator = null;
  }
  let entryFields={};
  if(state.carEntry&&elapsed>=state.carEntry.enterAt){
    const car=state.personalVehicles.car;
    if(state.mode==='foot'&&car&&distance(position,car)<=7){
      position={x:car.x,y:.45,z:car.z};
      entryFields={mode:'car',heading:car.heading??0,sitting:true,action:'Idle',carEntry:null,carControls:{...state.carControls,doorOpen:false,engineOn:false},lastMessage:'Você entrou no carro. Ligue o motor para dirigir.'};
    }else entryFields={carEntry:null,carControls:{...state.carControls,doorOpen:false,engineOn:false},lastMessage:'Entrada cancelada: você se afastou do carro.'};
  }
  if(state.carExit&&elapsed>=state.carExit.exitAt){
    const car=state.personalVehicles.car;
    if(state.mode==='car'&&car){
      position={x:clamp(car.x+Math.cos(state.heading)*3,CYBER_BOUNDS.minX,CYBER_BOUNDS.maxX),y:0,z:clamp(car.z-Math.sin(state.heading)*3,CYBER_BOUNDS.minZ,CYBER_BOUNDS.maxZ)};
      entryFields={mode:'foot',sitting:false,action:'Idle',carExit:null,lastMessage:'Você saiu do carro. F para entrar novamente.'};
    }else entryFields={carExit:null};
  }
  return {...state,elapsed,liveBuses,position,heading,elevator,jump,jumpHeight,...entryFields,...(state.action==='Interact'&&elapsed>=(state.actionUntil??Infinity)?{action:'Idle',actionUntil:null}:{})};
}

export function applyCyberAction(state, action, context = {}) {
  const fail = message => ({state,ok:false,message});
  const update = (fields,message) => ({ok:true,message,state:{...state,...fields,...(fields.action==='Interact'?{actionUntil:state.elapsed+2}:{}),lastMessage:message}});
  if (!action || typeof action.type !== 'string') return fail('Escolha uma ação.');
  if(state.carExit)return fail('Aguarde a abertura da porta para sair.');
  if(action.type==='BOARD'&&BUS_IDS.includes(action.vehicle)){
    const bus=sampleLiveBus(state,action.vehicle);
    if(context.carrying)return fail('Solte o objeto que está carregando antes de embarcar.');
    if(!canBoardBus(state,bus))return fail(bus?.stopped?'Aproxime-se da porta do ônibus a pé para embarcar.':'Aguarde o ônibus parar para embarcar.');
    return update({mode:action.vehicle,sitting:true,action:'Idle',heading:bus.heading,position:busSeatPosition(bus),busControls:{vehicleId:action.vehicle,role:'passenger'},liveBuses:{...state.liveBuses,[action.vehicle]:bus}},`Você embarcou: ${BUS_DEFINITIONS[action.vehicle].label}. F para sair quando estiver parado.`);
  }
  if(action.type==='BUS_TAKE_WHEEL'){
    if(!BUS_IDS.includes(state.mode)||state.busControls?.role!=='passenger')return fail('Embarque como passageiro para assumir o volante.');
    const bus=sampleLiveBus(state,state.mode);if(!bus.stopped)return fail('Aguarde o ônibus parar para assumir o volante.');
    const driven={...bus,control:'player',engineOn:false,doorOpen:true,stopped:true,speed:0,returnBlocked:false};
    return update({liveBuses:{...state.liveBuses,[state.mode]:driven},busControls:{vehicleId:state.mode,role:'driver'},position:busSeatPosition(driven,'driver'),heading:bus.heading},'Você assumiu o volante. Ligue o motor para dirigir; F para sair quando parar.');
  }
  if(action.type==='BUS_RELEASE_WHEEL'){
    if(!BUS_IDS.includes(state.mode)||state.busControls?.role!=='driver')return fail('Você precisa estar ao volante do ônibus.');
    const bus=sampleLiveBus(state,state.mode);if(!bus.stopped)return fail('Pare o ônibus antes de devolver o volante.');
    const returned=returnBusToRoute(state,state.mode),next=returned.liveBuses[state.mode];
    return update({liveBuses:returned.liveBuses,busControls:{vehicleId:state.mode,role:'passenger'},position:busSeatPosition(next)},'Motorista retomando a linha a partir deste ponto. Você continua como passageiro.');
  }
  if(action.type==='BUS_ENGINE'||action.type==='BUS_STOP'){
    if(!BUS_IDS.includes(state.mode)||state.busControls?.role!=='driver')return fail('Assuma o volante para operar o ônibus.');
    const bus=sampleLiveBus(state,state.mode),engineOn=action.type==='BUS_STOP'?false:!bus.engineOn;
    return update({liveBuses:{...state.liveBuses,[state.mode]:{...bus,engineOn,doorOpen:!engineOn,stopped:true,speed:0}}},engineOn?'Motor do ônibus ligado. WASD ou setas para dirigir.':'Ônibus parado, motor desligado e portas abertas.');
  }
  if(action.type==='BUS_DRIVE'){
    if(!BUS_IDS.includes(state.mode)||state.busControls?.role!=='driver')return fail('Assuma o volante para dirigir o ônibus.');
    const bus=sampleLiveBus(state,state.mode);if(!bus.engineOn)return fail('Ligue o motor do ônibus para dirigir.');
    const motion=busMotion(bus.heading,action.keys??{},action.delta,state.mode),position={x:clamp(bus.x+motion.dx,CYBER_BOUNDS.minX+BUS_DEFINITIONS[state.mode].length/2,CYBER_BOUNDS.maxX-BUS_DEFINITIONS[state.mode].length/2),y:0,
      z:clamp(bus.z+motion.dz,CYBER_BOUNDS.minZ+BUS_DEFINITIONS[state.mode].length/2,CYBER_BOUNDS.maxZ-BUS_DEFINITIONS[state.mode].length/2)};
    const proposed=moveLiveBus(state,state.mode,position,motion.heading,motion.steeringAngle,action.delta);
    const blocked=busPositionBlocked(sampleLiveBus(proposed,state.mode),context.obstacles,CYBER_BOUNDS);
    const moved=blocked?moveLiveBus(state,state.mode,bus,bus.heading,motion.steeringAngle,action.delta):proposed;
    return {ok:true,message:'',state:{...moved,action:'Idle'}};
  }
  if(action.type==='EXIT'&&BUS_IDS.includes(state.mode)){
    const bus=sampleLiveBus(state,state.mode);if(!bus.stopped)return fail('Pare o ônibus ou aguarde a próxima parada para desembarcar.');
    if(!bus.doorOpen)return fail('Desligue o motor e abra as portas antes de desembarcar.');
    const exit=busExitPosition(bus,context.obstacles,.4,CYBER_BOUNDS);
    if(!exit)return fail('A saída do ônibus está bloqueada. Reposicione o ônibus ou aguarde a passagem ficar livre.');
    const exited=state.busControls?.role==='driver'?returnBusToRoute(state,state.mode):state;
    return update({liveBuses:exited.liveBuses,mode:'foot',position:exit,sitting:false,action:'Idle',busControls:{vehicleId:null,role:null}},`Você desembarcou: ${BUS_DEFINITIONS[bus.id].label}.`);
  }
  if(action.type==='JUMP'){
    if(state.mode!=='foot'||state.sitting||state.elevator||state.carEntry||state.jump)return fail('O salto fica disponível quando você está em pé e no chão.');
    return update({jump:{startedAt:state.elapsed},jumpHeight:0,jumpCount:(state.jumpCount??0)+1,action:'Idle',fishing:null},'Salto · Espaço');
  }
  if (action.type === 'MOVE') {
    if (state.mode !== 'foot' && !DRIVE_VEHICLES[state.mode]) return fail('Saia do transporte antes de caminhar.');
    if ((state.sitting && !DRIVE_VEHICLES[state.mode]) || state.elevator) return fail('Levante-se ou aguarde o elevador.');
    if(state.mode==='car'&&(!state.carControls?.engineOn||state.carControls?.doorOpen))return fail('Feche a porta e ligue o motor para dirigir.');
    if(state.mode==='mototaxi'&&!state.motorcycleControls?.engineOn)return fail('Ligue o motor da moto para pilotar.');
    if (!finitePoint(action.position)) return fail('Posição inválida.');
    if(action.position.x<CYBER_BOUNDS.minX||action.position.x>CYBER_BOUNDS.maxX||action.position.z<CYBER_BOUNDS.minZ||action.position.z>CYBER_BOUNDS.maxZ)return fail('Posição fora da cidade.');
    const heading=action.heading??state.heading;
    return update({position:{...action.position},heading,action:DRIVE_VEHICLES[state.mode]?'Idle':'Walk',...(DRIVE_VEHICLES[state.mode]?{personalVehicles:{[state.mode]:{...state.personalVehicles[state.mode],x:action.position.x,y:0,z:action.position.z,heading}}}:{})},'');
  }
  if (action.type === 'BOARD') {
    const route = TRANSIT_ROUTES[action.vehicle], vehicle = route && sampleTransit(route,state.elapsed);
    if (!vehicle || state.mode !== 'foot') return fail('Escolha um transporte disponível.');
    if (!vehicle.stopped) return fail('Aguarde o veículo parar para embarcar.');
    if (distance(state.position,vehicle)>9) return fail('Aproxime-se da parada para embarcar.');
    return update({mode:action.vehicle,sitting:true,action:'Idle'},`Você embarcou: ${route.label}.`);
  }
  if (action.type === 'EXIT') {
    if(state.mode==='mototaxi')return applyCyberAction(state,{type:'MOTO_EXIT'},context);
    if(state.mode==='car'&&(state.carControls?.engineOn||!state.carControls?.doorOpen))return fail('Desligue o motor e abra a porta antes de sair do carro.');
    const route = TRANSIT_ROUTES[state.mode];
    if (!route) {
      if (DRIVE_VEHICLES[state.mode]) return update({mode:'foot',position:{...state.position,x:clamp(state.position.x+3,CYBER_BOUNDS.minX,CYBER_BOUNDS.maxX),y:0},sitting:false},`Você saiu: ${DRIVE_VEHICLES[state.mode].label}.`);
      return fail('Você já está a pé.');
    }
    const vehicle = sampleTransit(route,state.elapsed);
    if (!vehicle.stopped) return fail('O desembarque fica disponível na próxima parada.');
    return update({mode:'foot',position:{x:clamp(vehicle.x+6,CYBER_BOUNDS.minX,CYBER_BOUNDS.maxX),y:0,z:clamp(vehicle.z+3,CYBER_BOUNDS.minZ,CYBER_BOUNDS.maxZ)},sitting:false,action:'Idle'},`Desembarque em ${vehicle.stopLabel}.`);
  }
  if (action.type === 'TELEPORT') {
    if (state.mode !== 'foot' || state.elevator) return fail('Saia do veículo ou aguarde o elevador para usar o terminal.');
    const zone = context.zones?.find(z => z.id === action.zoneId), destination = zone?.approach ?? zone?.position;
    if (!destination || !Array.isArray(destination) || destination.some(n => !Number.isFinite(n))) return fail('Destino indisponível.');
    return update({position:{x:destination[0],y:destination[1],z:destination[2]},sitting:false,action:'Idle'},`Teletransporte de demonstração: ${zone.label}.`);
  }
  if (action.type === 'SIT') {
    if (state.mode !== 'foot' || state.elevator) return fail('Saia do transporte para usar um banco.');
    const bench = context.benches?.find(b => b.id === action.benchId);
    if (!bench || distance(state.position,bench.position)>5) return fail('Aproxime-se de um banco.');
    return update({position:{...bench.position,y:.52},sitting:true,action:'Idle'},'Você se sentou no banco.');
  }
  if (action.type === 'STAND') return update({sitting:false,position:{...state.position,y:0,z:state.position.z+1},action:'Idle'},'Você se levantou.');
  if (action.type === 'DANCE') {
    if (state.mode !== 'foot' || state.sitting || state.elevator) return fail('Fique em pé para dançar.');
    return update({action:state.action==='Dance'?'Idle':'Dance'},state.action==='Dance'?'Dança encerrada.':'Dançando com o rig do personagem.');
  }
  if (action.type === 'INTERACT') {
    if (state.mode !== 'foot' || state.sitting || state.elevator) return fail('Fique em pé para interagir.');
    return update({action:'Interact'},'Interagindo com o objeto.');
  }
  if (action.type === 'OUTFIT') {
    const color = ['#247fba','#37664b','#783874','#c85e26'].includes(action.color)?action.color:state.outfit.color;
    return update({outfit:{scrubs:true,coat:Boolean(action.coat),color}},'Roupa aplicada no provador 3D de demonstração.');
  }
  if (action.type === 'FLOWER') {
    const flower = FLOWER_BASES.find(f => f.id === action.flowerId);
    if (!flower || distance(state.position,flower.position)>5) return fail('Aproxime-se de uma flor da praça.');
    if ((state.flowerCooldowns[flower.id] ?? 0)>state.elapsed) return fail('Aguarde alguns segundos para receber outra cópia dessa flor.');
    if (state.inventory.flowers>=50) return fail('Seu inventário de demonstração está cheio.');
    return update({inventory:{...state.inventory,flowers:state.inventory.flowers+1},flowerCooldowns:{...state.flowerCooldowns,[flower.id]:state.elapsed+10},action:'Interact'},'Uma cópia pessoal foi adicionada. A flor base permanece no jardim.');
  }
  if (action.type === 'PLANT' || action.type === 'HARVEST') {
    const plot = FARM_PLOTS.find(p => p.id === action.plotId);
    if (!plot || distance(state.position,plot.position)>(state.mode==='harvester'?9:7)) return fail('Aproxime-se do canteiro da fazenda.');
    const planted = state.plots[plot.id];
    if (action.type === 'PLANT') {
      if (state.mode!=='foot')return fail('Saia do veículo para plantar.');
      if (planted) return fail('Este canteiro já está plantado.');
      if (state.inventory.seeds<1) return fail('Pegue sementes no terminal da fazenda.');
      return update({plots:{...state.plots,[plot.id]:{plantedAt:state.elapsed}},inventory:{...state.inventory,seeds:state.inventory.seeds-1},action:'Interact'},'Semente plantada. Crescimento acelerado de 20 segundos neste protótipo.');
    }
    if (!planted || state.elapsed-planted.plantedAt<20) return fail('A plantação ainda não está pronta.');
    return update({plots:{...state.plots,[plot.id]:null},inventory:{...state.inventory,harvest:state.inventory.harvest+1,seeds:state.inventory.seeds+1},action:'Interact'},'Colheita virtual concluída. Uma semente voltou ao inventário.');
  }
  if (action.type === 'SEEDS') {
    if (distance(state.position,{x:0,z:100})>20) return fail('Visite o terminal da fazenda.');
    return update({inventory:{...state.inventory,seeds:Math.min(20,state.inventory.seeds+3)}},'Três sementes de demonstração recebidas.');
  }
  if (action.type === 'TRACTOR') {
    if (state.mode !== 'foot' || distance(state.position,context.tractor ?? {x:12,z:96})>7) return fail('Aproxime-se do trator parado.');
    const tractor=context.tractor ?? {x:12,y:0,z:96};
    return update({mode:'tractor',position:{x:tractor.x,y:1.2,z:tractor.z},personalVehicles:{tractor:{...tractor,heading:state.heading}},sitting:true,action:'Idle'},'No trator: use os controles de direção; desembarque para plantar.');
  }
  if(action.type==='DRIVE'){
    const definition=DRIVE_VEHICLES[action.vehicle],vehicle=state.personalVehicles[action.vehicle]??definition?.position;
    if(!definition||state.mode!=='foot'||state.elevator)return fail('Escolha um veículo parado e fique em pé.');
    if(distance(state.position,vehicle)>7)return fail('Aproxime-se do veículo para entrar na sua cópia.');
    if(action.vehicle==='car'&&!state.carControls?.doorOpen)return fail('Abra a porta do carro antes de entrar.');
    const personal=state.personalVehicles[definition.id]??{...vehicle,x:vehicle.x+5};
    return update({mode:definition.id,position:{x:personal.x,y:definition.seat,z:personal.z},personalVehicles:{[definition.id]:{...personal,heading:personal.heading??0}},heading:personal.heading??0,sitting:true,action:'Idle'},`Você entrou: ${definition.label}.`);
  }
  if(action.type==='CAR_ENTER'){
    if(state.carEntry)return fail('Aguarde a abertura da porta.');
    const source=resolveCarSource(action.carId),personal=state.personalVehicles.car;
    const own=action.carId==='personal-car'&&personal?resolveCarSource(personal.sourceId??'car'):null;
    const car=own?{...own,position:{x:personal.x,y:0,z:personal.z},heading:personal.heading??0}:source;
    if(!car||!canEnterCar(state,car)||state.jump)return fail('Aproxime-se do carro a pé e aguarde aterrissar para entrar.');
    if(context.carrying)return fail('Solte o objeto que está carregando antes de entrar no carro.');
    const parked=own?{...personal}:safeVehicleCopy(car,context.obstacles??[],1.3);
    if(!parked)return fail('Não há espaço livre ao lado deste carro.');
    const personalCar={...parked,sourceId:own?personal.sourceId:car.id};
    return update({personalVehicles:{car:personalCar},carControls:{doorOpen:true,engineOn:false,windowsOpen:own?Boolean(state.carControls?.windowsOpen):false},carEntry:{enterAt:state.elapsed+1.4},sitting:false,action:'Idle'},'Abrindo a porta para você entrar no carro…');
  }
  if(action.type==='MOTO_ENTER'){
    if(state.mode!=='foot'||state.sitting||state.elevator||state.jump||state.carEntry||context.carrying)return fail('Fique a pé, no chão e sem objetos nas mãos para subir na moto.');
    const own=action.motoId==='personal-moto'&&state.personalVehicles.mototaxi;
    const bike=own?{...resolveMotorcycle(own.sourceId??'mototaxi'),position:{x:own.x,y:0,z:own.z},heading:own.heading??0}:resolveMotorcycle(action.motoId??'mototaxi');
    if(!bike||!nearestMotorcycle(state.position,own)||distance(state.position,bike.position)>7)return fail('Aproxime-se da moto para pilotar.');
    const parked=own?{...own}:safeVehicleCopy(bike,context.obstacles??[],.6);
    if(!parked)return fail('Não há espaço livre para a moto.');
    const personal={...parked,sourceId:own?own.sourceId:bike.id};
    return update({mode:'mototaxi',personalVehicles:{mototaxi:personal},position:{x:personal.x,y:.7,z:personal.z},heading:personal.heading,sitting:true,action:'Idle',motorcycleControls:{engineOn:false}},'Você subiu na moto. Ligue o motor para pilotar. F para descer.');
  }
  if(action.type==='MOTO_ENGINE'){
    if(state.mode!=='mototaxi')return fail('Suba na moto para operar o motor.');
    const engineOn=!state.motorcycleControls?.engineOn;
    return update({motorcycleControls:{engineOn}},engineOn?'Motor da moto ligado. WASD ou setas para pilotar.':'Motor da moto desligado.');
  }
  if(action.type==='MOTO_EXIT'){
    if(state.mode!=='mototaxi')return fail('Você já está fora da moto.');
    return update({mode:'foot',motorcycleControls:{engineOn:false},sitting:false,action:'Idle',position:{x:clamp(state.position.x+Math.cos(state.heading)*1.5,CYBER_BOUNDS.minX,CYBER_BOUNDS.maxX),y:0,z:clamp(state.position.z-Math.sin(state.heading)*1.5,CYBER_BOUNDS.minZ,CYBER_BOUNDS.maxZ)}},'Você desceu da moto. F para subir novamente.');
  }
  if(action.type==='SUMMON_VEHICLE'){
    if(state.mode!=='foot'||state.sitting||state.elevator||state.jump||state.carEntry)return fail('Saia do veículo e fique em pé para chamar outro.');
    const definition=DRIVE_VEHICLES[action.vehicle];if(!definition)return fail('Escolha um veículo da garagem.');
    if(definition.farmOnly&&(state.position.z<86||state.position.z>114||Math.abs(state.position.x)>22))return fail('Chame o equipamento agrícola na fazenda.');
    const chosen=action.vehicle==='car'?resolveCarSource(action.sourceId??'car'):action.vehicle==='mototaxi'?resolveMotorcycle(action.sourceId??'mototaxi'):null;
    const template=chosen??{position:definition.position,heading:0,w:action.vehicle==='truck'?3:2.8,d:action.vehicle==='truck'?8:5};
    const point=safeVehicleCopy({...template,position:{...state.position,y:0},heading:state.heading},context.obstacles??[],action.vehicle==='mototaxi'?.6:1.3);
    if(!point)return fail('Procure um espaço aberto para chamar o veículo.');
    const personal={...point,sourceId:chosen?.id??action.vehicle,wheelAngle:0,steeringAngle:0};
    const previous=Object.entries(state.personalVehicles)[0];
    const garage=previous?{...state.garage,[previous[0]]:{sourceId:previous[1].sourceId,parkingId:'garage'}}:state.garage;
    return update({garage,personalVehicles:{[action.vehicle]:personal},carControls:{doorOpen:false,engineOn:false,windowsOpen:false},motorcycleControls:{engineOn:false}},`${definition.label} chamado. Apenas um veículo pessoal fica no mapa.`);
  }
  if(action.type==='STORE_VEHICLE'){
    const active=Object.entries(state.personalVehicles)[0];if(!active)return fail('Não há veículo pessoal no mapa.');
    const [id,vehicle]=active;
    const parking=context.parking??DEFAULT_PARKING,slot=parking.find(item=>distance(state.position,{x:item.position[0],z:item.position[2]})<=10||distance(vehicle,{x:item.position[0],z:item.position[2]})<=10);
    if(!slot)return fail('Leve seu veículo a um estacionamento para guardá-lo.');
    const position=state.mode===id?{x:clamp(vehicle.x+3,CYBER_BOUNDS.minX,CYBER_BOUNDS.maxX),y:0,z:vehicle.z}:state.position;
    return update({garage:{...state.garage,[id]:{sourceId:vehicle.sourceId,parkingId:slot.id}},personalVehicles:{},mode:'foot',position,sitting:false,carEntry:null,carExit:null,carControls:{...state.carControls,engineOn:false,doorOpen:false},motorcycleControls:{engineOn:false},action:'Idle'},`${DRIVE_VEHICLES[id].label} guardado no estacionamento. Chame novamente pelo telefone.`);
  }
  if(action.type==='CAR_EXIT'){
    if(state.mode!=='car'||!state.personalVehicles.car)return fail('Você precisa estar no carro para sair.');
    return update({carControls:{...state.carControls,engineOn:false,doorOpen:true},carExit:{exitAt:state.elapsed+1.2},action:'Idle'},'Parando o carro e abrindo a porta para sair…');
  }
  if(action.type==='CAR_DOOR'){
    const vehicle=state.personalVehicles.car??DRIVE_VEHICLES.car.position;
    if(!['foot','car'].includes(state.mode)||distance(state.position,vehicle)>7)return fail('Aproxime-se do carro para usar a porta.');
    if(state.carControls?.engineOn)return fail('Desligue o motor antes de abrir a porta.');
    const doorOpen=!state.carControls?.doorOpen;
    const personalVehicles=state.personalVehicles.car?state.personalVehicles:{car:{...vehicle,x:vehicle.x+5,heading:0,sourceId:'car'}};
    return update({personalVehicles,carControls:{...state.carControls,doorOpen,engineOn:false}},doorOpen?'Porta do carro aberta. Entre pela opção Entrar na cópia.':'Porta do carro fechada.');
  }
  if(action.type==='CAR_ENGINE'){
    if(state.mode!=='car')return fail('Entre no carro para operar o motor.');
    if(state.carControls?.doorOpen)return fail('Feche a porta antes de ligar o motor.');
    const engineOn=!state.carControls?.engineOn;
    return update({carControls:{...state.carControls,doorOpen:false,engineOn}},engineOn?'Motor ligado. Use os controles de direção.':'Motor desligado. O carro permanece parado.');
  }
  if(action.type==='CAR_WINDOWS'){
    if(state.mode!=='car')return fail('Entre no carro para operar os vidros laterais.');
    const windowsOpen=!state.carControls?.windowsOpen;
    return update({carControls:{...state.carControls,windowsOpen}},windowsOpen?'Vidros laterais baixados. O vidro traseiro permanece fechado.':'Vidros laterais fechados.');
  }
  if(action.type==='PARK'){
    return applyCyberAction(state,{type:'STORE_VEHICLE'},context);
  }
  if(action.type==='TRAILER'){
    if(!['flatbed','tanker','box'].includes(action.trailer))return fail('Escolha uma carroceria disponível.');
    return update({trailer:action.trailer},'Carroceria de demonstração acoplada à sua cópia do caminhão.');
  }
  if (action.type === 'CAST') {
    if (distance(state.position,{x:100,z:0})>20 || state.mode!=='foot') return fail('Visite a margem da praia para pescar.');
    if (state.fishing) return fail('Recolha a linha atual primeiro.');
    return update({fishing:{startedAt:state.elapsed,readyAt:state.elapsed+8},action:'Interact'},'Linha lançada. Aguarde 8 segundos: pesca educativa virtual.');
  }
  if (action.type === 'REEL') {
    if (!state.fishing) return fail('Lance a linha primeiro.');
    if (state.elapsed<state.fishing.readyAt) return fail('Aguarde a indicação para recolher.');
    if (distance(state.position,{x:100,z:0})>20) return fail('Volte à margem para recolher a linha.');
    const caught = state.fishingAttempts % 3 !== 2;
    return update({fishing:null,fishingAttempts:state.fishingAttempts+1,inventory:{...state.inventory,fish:state.inventory.fish+(caught?1:0)},action:'Interact'},caught?'Um peixe virtual foi adicionado ao inventário.':'Nenhum peixe virtual nesta tentativa. Lance novamente.');
  }
  if (action.type === 'ELEVATOR') {
    if (state.mode!=='foot' || state.elevator || distance(state.position,ELEVATOR_POSITION)>9) return fail('Aproxime-se do elevador da galeria.');
    const target = action.floor===-1?-6:0;
    return update({position:{...ELEVATOR_POSITION,y:state.position.y},sitting:false,elevator:{from:state.position.y,to:target,startedAt:state.elapsed},action:'Idle'},`Elevador para ${target?'o subsolo':'o térreo'}.`);
  }
  return fail('Esta ação ainda não está disponível.');
}

export function restoreCyberState(storage) {
  const fresh = createCyberState();
  try {
    const saved = JSON.parse(storage.getItem(CYBER_STORAGE_KEY));
    if (saved?.version!==1) return fresh;
    if (saved.inventory && typeof saved.inventory==='object') for (const key of Object.keys(fresh.inventory)) {
      const value=saved.inventory[key]; if (Number.isInteger(value)&&value>=0&&value<=10000) fresh.inventory[key]=value;
    }
    if (saved.outfit) fresh.outfit=applyCyberAction(fresh,{type:'OUTFIT',...saved.outfit}).state.outfit;
    for(const [id,stored]of Object.entries(saved.garage??{})){
      if(DRIVE_VEHICLES[id]&&stored&&typeof stored.sourceId==='string'&&stored.sourceId.length<120)fresh.garage[id]={sourceId:stored.sourceId,parkingId:typeof stored.parkingId==='string'?stored.parkingId:'garage'};
    }
    return fresh;
  } catch { return fresh; }
}
export function saveCyberState(storage,state) {
  try { storage.setItem(CYBER_STORAGE_KEY,JSON.stringify({version:1,inventory:state.inventory,outfit:state.outfit,garage:state.garage}));return true; }
  catch { return false; }
}
