import {resolveAssetReferences} from '../config/deploymentConfig.js';
import worldRaw from '../config/realisticWorldManifest.json' with {type:'json'};
const world=resolveAssetReferences(worldRaw);
import catalogRaw from '../config/suppliedAssets.json' with {type:'json'};
const catalog=resolveAssetReferences(catalogRaw);

const SLS='SUP_2010_mercedes_sls_amg';
const APPROVED_SOURCES=new Set([SLS,'SUP_volkswagen_atlas_teramont_cross_sport_2025']);
const LIMIT=118;
const finitePoint=point=>point&&[point.x,point.y??0,point.z].every(Number.isFinite);
const copyCar=car=>car?{...car,asset:structuredClone(car.asset),position:{...car.position}}:null;

function makeCar(id,label,asset,position,heading=0){
  const source=catalog.find(item=>item.id===asset?.sourceId);
  if(!source||source.status!=='validated'||!APPROVED_SOURCES.has(source.id)||
    source.sha256!==asset.sha256||source.url!==asset.url||!finitePoint(position)||
    !Number.isFinite(asset.height)||asset.height<=0||!Number.isFinite(heading))return null;
  const dimensions=source.dimensions;
  if(!Array.isArray(dimensions)||dimensions.length!==3||dimensions.some(n=>!Number.isFinite(n)||n<=0))return null;
  const scale=asset.height/dimensions[2],width=dimensions[0]*scale,depth=dimensions[1]*scale;
  return {id,label,asset:structuredClone(asset),position:{x:position.x,y:position.y??0,z:position.z},heading,
    w:Math.abs(Math.cos(heading))*width+Math.abs(Math.sin(heading))*depth,
    d:Math.abs(Math.sin(heading))*width+Math.abs(Math.cos(heading))*depth};
}

const cars=[
  makeCar('car','Carro esportivo',world.dynamicReplacements.car,{x:20,y:0,z:44}),
  ...world.environmentReplacements.filter(record=>APPROVED_SOURCES.has(record.sourceId)).map(record=>
    makeCar(record.id,record.sourceId===SLS?'Carro esportivo':'Carro utilitário',record,
      {x:record.position[0],y:record.position[1],z:record.position[2]},record.rotation?.[1]??0)),
].filter(Boolean);

export function listInteractiveCars(){return cars.map(copyCar);}

export function resolveCarSource(id){
  return copyCar(cars.find(car=>car.id===id)||cars.find(car=>car.asset.sourceId===id));
}

function personalDefinition(personalCar){
  if(!personalCar)return null;
  const base=resolveCarSource(personalCar.sourceId??'car');
  const point=personalCar.position??personalCar;
  if(!base||!finitePoint(point))return null;
  return makeCar('personal-car',`Seu ${base.label.toLowerCase()}`,base.asset,point,personalCar.heading??base.heading);
}

export function nearestInteractiveCar(position,personalCar,maxRange=7){
  if(!finitePoint(position)||!Number.isFinite(maxRange)||maxRange<0)return null;
  // Prefer the player's copy if two sources are equally close.
  const candidates=[personalDefinition(personalCar),...cars.filter(car=>!personalCar||car.id!==personalCar.sourceId)].filter(Boolean)
    .map(car=>({...car,distance:Math.hypot(position.x-car.position.x,position.z-car.position.z)}))
    .filter(car=>car.distance<=maxRange&&Math.abs((position.y??0)-car.position.y)<=1.6)
    .sort((a,b)=>a.distance-b.distance);
  return copyCar(candidates[0]);
}

export function canEnterCar(state,car){
  if(!state||state.mode!=='foot'||state.sitting||state.elevator||!finitePoint(state.position)||!car||!finitePoint(car.position))return false;
  return Math.hypot(state.position.x-car.position.x,state.position.z-car.position.z)<=7&&
    Math.abs((state.position.y??0)-(car.position.y??0))<=1.6;
}

const validBox=box=>box&&[box.x,box.z,box.w,box.d].every(Number.isFinite)&&box.w>0&&box.d>0;
const overlaps=(candidate,obstacle,margin)=>Math.abs(candidate.x-obstacle.x)<(candidate.w+obstacle.w)/2+margin&&
  Math.abs(candidate.z-obstacle.z)<(candidate.d+obstacle.d)/2+margin;

export function safeVehicleCopy(definition,obstacles=[],radius=1.3){
  if(!definition||!finitePoint(definition.position)||![definition.w,definition.d].every(n=>Number.isFinite(n)&&n>0)||
    !Number.isFinite(radius)||radius<0||!Array.isArray(obstacles))return null;
  const source={x:definition.position.x,z:definition.position.z,w:definition.w,d:definition.d};
  // Malformed blockers cannot be treated as safe space.
  if(obstacles.some(box=>!validBox(box)))return null;
  const blocked=[source,...obstacles],heading=definition.heading??0;
  if(!Number.isFinite(heading))return null;
  for(const step of [4,6,8])for(const [x,z]of [[step,0],[-step,0],[0,step],[0,-step],[step,step],[-step,step],[step,-step],[-step,-step]]){
    const candidate={x:source.x+x,z:source.z+z,w:source.w,d:source.d};
    if(Math.abs(candidate.x)+candidate.w/2+radius>LIMIT||Math.abs(candidate.z)+candidate.d/2+radius>LIMIT)continue;
    if(blocked.some(box=>overlaps(candidate,box,radius)))continue;
    return {x:candidate.x,y:definition.position.y??0,z:candidate.z,heading};
  }
  return null;
}
