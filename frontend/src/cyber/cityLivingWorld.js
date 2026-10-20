import rawPlan from '../config/cityLivingWorld.json' with {type:'json'};
import additions from '../config/suppliedAdditions20261016.json' with {type:'json'};
import {resolveAssetReferences} from '../config/deploymentConfig.js';

const catalog=new Map(resolveAssetReferences(additions).map(asset=>[asset.id,asset]));
export const cityLivingWorldPlan=resolveAssetReferences(rawPlan);
export function habitatAsset(habitat){return catalog.get(habitat.assetId)??null;}
export const livingWorldZones=[
  {id:rawPlan.campus.id,label:rawPlan.campus.label,position:rawPlan.campus.position,approach:rawPlan.campus.approach},
  ...rawPlan.habitats.map(h=>({id:h.id,label:h.label,position:h.position,
    approach:[h.position[0],h.position[1],h.position[2]+h.size[1]/2+1.8]})),
];
export const campusBenchLocations=rawPlan.campus.benches;
export function prepareCityCampusScene(scene){
  const hidden=new Set(rawPlan.campus.hideNodes),walkable=new Set(rawPlan.campus.walkableNodes);
  scene.traverse(object=>{
    // GLTFLoader sanitizes periods in .001 names for animation bindings, while
    // retaining the exact Blender node name in userData.name.
    const name=object.userData?.name??object.userData?.asset_node_name??object.name;
    if(hidden.has(name))object.visible=false;
    if(walkable.has(name))object.userData.walkable=true;
  });
  return scene;
}
export function prepareCityCampusShadows(scene){
  scene.traverse(object=>{
    const name=object.userData?.name??object.userData?.asset_node_name??object.name;
    if(object.isMesh&&name==='Patio'){
      // The broad floor receives prop/character shadows but has no useful
      // lower surface to shade. Avoid sampling its own PCF depth footprint.
      object.castShadow=false;
      object.receiveShadow=true;
    }
  });
  return scene;
}
const campusAt=(id,x,z,w,d)=>({id,x:rawPlan.campus.position[0]+x,z:rawPlan.campus.position[2]+z,w,d});
export const livingWorldColliders=[
  campusAt('campus-study-desk',0,-4.5,3.4,1.6),
  ...[-7,7].map(x=>campusAt(`campus-anatomy-${x}`,x,-4,1.4,1.4)),
  ...[-6,6].map(x=>campusAt(`campus-bench-${x}`,x,5,2.6,.64)),
  ...[-10,10].flatMap(x=>[-9,0,9].map(z=>campusAt(`campus-lamp-${x}-${z}`,x,z,.18,.18))),
  ...rawPlan.habitats.flatMap(h=>{
    const [x,,z]=h.position,[w,d]=h.size,t=.18;
    if(h.kind==='aquarium')return [{id:`${h.id}-tank`,x,z,w,d}];
    return [{id:`${h.id}-west`,x:x-w/2,z,w:t,d},
      {id:`${h.id}-east`,x:x+w/2,z,w:t,d},
      {id:`${h.id}-north`,x,z:z-d/2,w,d:t},
      {id:`${h.id}-south`,x,z:z+d/2,w,d:t}];
  }),
];
const distance=(position,center)=>Math.hypot(position.x-center[0],position.z-center[2]);
// Every habitat has one resident. A small nearest-first budget limits parsing,
// skeletons and GPU textures; exit radii avoid churn at a loading boundary.
export function selectLivingWorldResidents(position,previous=[]){
  if(!position||!Number.isFinite(position.x)||!Number.isFinite(position.z))return [];
  return rawPlan.habitats.map(h=>({h,d:distance(position,h.position)}))
    .filter(({h,d})=>d<=(previous.includes(h.id)?h.unloadRadius:h.loadRadius))
    .sort((a,b)=>a.d-b.d||a.h.id.localeCompare(b.h.id))
    .slice(0,rawPlan.district.maxConcurrentAnimals).map(({h})=>h.id);
}
export function campusIsNear(position,wasLoaded=false){
  return Boolean(position&&distance(position,rawPlan.campus.position)<=(wasLoaded?rawPlan.campus.unloadRadius:rawPlan.campus.loadRadius));
}
export function habitatPath(habitat,elapsed){
  const angle=(Number.isFinite(elapsed)?elapsed:0)*Math.PI*2/habitat.periodSeconds+habitat.phase;
  const [rx,rz]=habitat.pathRadii;
  return {x:Math.cos(angle)*rx,z:Math.sin(angle)*rz,
    y:habitat.kind==='aquarium'?(habitat.swimBaseY??0)+Math.sin(angle*2)*.035:0,
    heading:rx||rz?Math.atan2(-Math.sin(angle)*rx,Math.cos(angle)*rz):habitat.phase};
}
export function livingWorldBlenderPoint(point){return [point[0],-point[2],point[1]];}
