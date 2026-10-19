import {resolveAssetReferences} from '../config/deploymentConfig.js';
import worldRaw from '../config/realisticWorldManifest.json' with {type:'json'};
const world=resolveAssetReferences(worldRaw);
import catalogRaw from '../config/suppliedAssets.json' with {type:'json'};
const catalog=resolveAssetReferences(catalogRaw);
const sourceId=world.dynamicReplacements.mototaxi.sourceId;
const source=catalog.find(a=>a.id===sourceId);
function record(id,asset,position,heading=0){
  const scale=asset.height/source.dimensions[2];
  return {id,label:'Motocicleta',asset,position,heading,w:source.dimensions[0]*scale,d:source.dimensions[1]*scale};
}
const bikes=[record('mototaxi',world.dynamicReplacements.mototaxi,{x:-40,y:0,z:40}),...world.environmentReplacements.filter(a=>a.sourceId===sourceId).map(a=>record(a.id,a,{x:a.position[0],y:a.position[1],z:a.position[2]},a.rotation?.[1]??0))];
export function resolveMotorcycle(id){const bike=bikes.find(b=>b.id===id);return bike?structuredClone(bike):null;}
export function listMotorcycles(){return structuredClone(bikes);}
export function nearestMotorcycle(position,personal,maxRange=7){
  const own=personal?{...resolveMotorcycle(personal.sourceId??'mototaxi'),id:'personal-moto',position:{x:personal.x,y:0,z:personal.z},heading:personal.heading??0}:null;
  const found=[own,...bikes.filter(b=>!personal||b.id!==personal.sourceId)].filter(b=>b&&Math.abs((position.y??0)-b.position.y)<=1.6).map(b=>({...b,distance:Math.hypot(position.x-b.position.x,position.z-b.position.z)})).filter(b=>b.distance<=maxRange).sort((a,b)=>a.distance-b.distance)[0];
  return found?structuredClone(found):null;
}
