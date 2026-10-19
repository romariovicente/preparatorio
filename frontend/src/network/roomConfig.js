import {assetUrl} from '../config/deploymentConfig.js';
import { campusTemplates, campusInteractionOptions, CAMPUS_START } from '../world/campusObjects.js';
import { hospitalTemplates, HOSPITAL_BOUNDS, HOSPITAL_START, hospitalPlacementAllowed } from '../etapa41/hospitalObjects.js';
import { CITY_START, CYBER_BOUNDS } from '../cyber/simulation.js';

const asPoint = p => Array.isArray(p) ? { x:p[0], y:p[1], z:p[2] } : { ...p };
const hospitalObjects = hospitalTemplates.map(t => ({ ...t, position:asPoint(t.position) }));

export const cyberTemplates = [
  { id:'cyber_flower', name:'Flor coletável', kind:'flower', position:{x:-10,y:0,z:14}, portable:true, movable:false, url:assetUrl('/assets/cyber/PROP_flower_20261005.glb'), description:'Pegue uma cópia da flor para carregar; a planta base permanece no jardim.', actionLabel:'Observar flor', actionText:'Sua flor foi observada. A planta base continua disponível para outros jogadores.' },
  { id:'cyber_bench', name:'Banco da praça', kind:'bench', position:{x:-12,y:0,z:8}, portable:false, movable:true, size:[2.4,.8], url:assetUrl('/assets/cyber/PROP_bench_20261005.glb'), description:'Crie e reposicione sua cópia do banco em um espaço livre.', actionLabel:'Examinar banco', actionText:'Banco examinado. A ação de sentar usa o controle de personagem da cidade.' },
  { id:'cyber_fishing_rod', name:'Vara de pesca', kind:'fishing-rod', position:{x:11,y:0,z:10}, portable:true, movable:false, url:assetUrl('/assets/cyber/PROP_fishing-rod_20261005.glb'), description:'Carregue uma cópia da vara até a área de pesca do bioma fictício.', actionLabel:'Conferir vara', actionText:'Vara conferida. A pesca do protótipo continua no controle local do jogador.' },
];
const cyberBounds = CYBER_BOUNDS;

export const interactionRooms = {
  campus: {
    templates:campusTemplates,options:campusInteractionOptions,start:asPoint(CAMPUS_START),positionBounds:{minX:-10,maxX:10,minZ:-9,maxZ:10},
    validatePlacement(position,template,state,object,actorId) {
      if (object.kind === 'base' && Math.hypot(position.x-object.position.x,position.z-object.position.z)<campusInteractionOptions.placementRadius*2) return false;
      return !Object.entries(state.players).some(([id,player])=>(id===actorId || player.online) && player.position && Math.hypot(position.x-player.position.x,position.z-player.position.z)<.55);
    },
  },
  hospital: {
    templates:hospitalObjects,
    options:{ bounds:HOSPITAL_BOUNDS, reach:2.25, dropReach:2, moveReach:3, placementRadius:.3, maxCopies:12 },
    start:asPoint(HOSPITAL_START),
    validatePlacement(position, template, state, object, actorId) {
      const furniture = state.objects.filter(o => o.position && (o.kind !== 'base' || hospitalObjects.find(t => t.id === o.templateId)?.movable))
        .map(o => ({ id:o.id, position:[o.position.x,o.position.y ?? 0,o.position.z], size:hospitalObjects.find(t => t.id === o.templateId)?.size ?? [.5,.5] }));
      // Moving a base creates a copy; its authored footprint stays occupied.
      const players = Object.entries(state.players).filter(([id,p])=>(id===actorId || p.online) && p.position).map(([id,p])=>({id,position:[p.position.x,0,p.position.z],size:[.5,.5]}));
      const ignoredId = object.kind === 'copy' ? object.id : null;
      return hospitalPlacementAllowed([position.x,position.y ?? 0,position.z],template.size,[...furniture,...players],ignoredId);
    },
  },
  cyber: {
    templates:cyberTemplates,
    options:{ bounds:cyberBounds, reach:2.25, dropReach:2, moveReach:3, placementRadius:.5, maxCopies:20, floorY:0, maxVerticalReach:1.6 },
    start:asPoint(CITY_START),
    positionBounds:cyberBounds,
    minY:-6.5,
    maxY:2,
    validatePlacement(position,template,state,object,actorId) {
      const width=template.size?.[0] ?? .6,depth=template.size?.[1] ?? .6;
      if(position.x-width/2<cyberBounds.minX || position.x+width/2>cyberBounds.maxX || position.z-depth/2<cyberBounds.minZ || position.z+depth/2>cyberBounds.maxZ)return false;
      const ignoredId=object.kind==='copy' ? object.id : null;
      const overlaps=(target,otherWidth,otherDepth)=>Math.abs(position.x-target.x)<(width+otherWidth)/2+.1 && Math.abs(position.z-target.z)<(depth+otherDepth)/2+.1;
      // Base footprints remain occupied when MOVE produces a new owned copy.
      if(state.objects.some(other=>other.id!==ignoredId && other.position && overlaps(other.position,...(cyberTemplates.find(t=>t.id===other.templateId)?.size ?? [.6,.6]))))return false;
      return !Object.entries(state.players).some(([id,player])=>(id===actorId || player.online) && player.position && Math.abs((position.y ?? 0)-(player.position.y ?? 0))<1 && overlaps(player.position,.5,.5));
    },
  },
};
