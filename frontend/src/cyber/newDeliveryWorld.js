import {resolveAssetReferences} from '../config/deploymentConfig.js';
import configRaw from '../config/newDeliveryWorld.json' with {type:'json'};
const config=resolveAssetReferences(configRaw);
import {newDeliveryRuntimeAssets} from '../config/newDeliveryRuntimeAssets.js';
const catalog=new Map(newDeliveryRuntimeAssets.map(asset=>[asset.id,asset]));
export const newDeliveryWorld=config;
export const newDeliveryColliders=config.colliders;
export const newDeliveryZones=config.zones;
export const newDeliveryHidePrefixes=config.hidePrefixes;
export const newDeliveryParking=config.parkingOverrides;
export const newDeliveryRoutes=config.routeOverrides;
export const newDeliveryRoadConnections=config.roadConnections;
export function getDeliveryAsset(id){const source=catalog.get(id);return source?structuredClone(source):null;}
export function getDeliveryReplacement(id){
  const source=getDeliveryAsset(config.dynamicReplacements[id]);
  return source?{...source,sourceId:source.id,id,label:source.name}:null;
}
export function deliveryFootprint(composition){
  const asset=catalog.get(composition.assetId);if(!asset)return null;
  const scale=(composition.height??asset.height)/asset.dimensions[2],yaw=composition.rotation?.[1]??0;
  const w=asset.dimensions[0]*scale,d=asset.dimensions[1]*scale;
  return {id:composition.id,x:composition.position[0],z:composition.position[2],
    w:Math.abs(Math.cos(yaw))*w+Math.abs(Math.sin(yaw))*d,d:Math.abs(Math.sin(yaw))*w+Math.abs(Math.cos(yaw))*d};
}
export function resolveDeliveryParking(original){
  const overrides=new Map(config.parkingOverrides.map(bay=>[bay.id,bay]));
  return original.map(bay=>structuredClone(overrides.get(bay.id)??bay));
}

// The same planar polygons can be consumed by Three and Blender. All coordinates
// are [X,Z] metres; Blender maps a vertex to (X,-Z,surfaceY).
export function deliveryRoadRectangle(from,to,width,offset=0){
  const dx=to[0]-from[0],dz=to[1]-from[1],length=Math.hypot(dx,dz);
  if(!length||width<=0)return [];
  const nx=-dz/length,nz=dx/length;
  return [[from[0]+nx*(offset-width/2),from[1]+nz*(offset-width/2)],
    [to[0]+nx*(offset-width/2),to[1]+nz*(offset-width/2)],
    [to[0]+nx*(offset+width/2),to[1]+nz*(offset+width/2)],
    [from[0]+nx*(offset+width/2),from[1]+nz*(offset+width/2)]];
}
const sideOf=(a,b,p)=>(b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0]);
const clipSide=(polygon,a,b,inside)=>{
  const result=[];
  for(let i=0;i<polygon.length;i++){
    const p=polygon[i],q=polygon[(i+1)%polygon.length],sp=sideOf(a,b,p),sq=sideOf(a,b,q);
    const keepP=inside?sp>=-1e-8:sp<=1e-8,keepQ=inside?sq>=-1e-8:sq<=1e-8;
    if(keepP)result.push(p);
    if(keepP!==keepQ){const t=sp/(sp-sq);result.push([p[0]+(q[0]-p[0])*t,p[1]+(q[1]-p[1])*t]);}
  }
  return result;
};
export function deliveryPolygonArea(polygon){
  return Math.abs(polygon.reduce((area,p,i)=>{const q=polygon[(i+1)%polygon.length];return area+p[0]*q[1]-q[0]*p[1];},0))/2;
}
export function subtractDeliveryPolygon(polygon,obstacle){
  let remainder=polygon;const fragments=[];
  for(let i=0;i<obstacle.length&&remainder.length>=3;i++){
    const a=obstacle[i],b=obstacle[(i+1)%obstacle.length],outside=clipSide(remainder,a,b,false);
    if(outside.length>=3&&deliveryPolygonArea(outside)>1e-6)fragments.push(outside);
    remainder=clipSide(remainder,a,b,true);
  }
  return fragments;
}
export function deliveryPointInPolygon(point,polygon){
  return polygon.every((a,i)=>sideOf(a,polygon[(i+1)%polygon.length],point)>=-1e-6);
}
function cutRoadPolygons(polygon,obstacles){
  return obstacles.reduce((fragments,obstacle)=>fragments.flatMap(piece=>subtractDeliveryPolygon(piece,obstacle)),[polygon]);
}
const lineAlong=(from,to,offset,width)=>deliveryRoadRectangle(from,to,width,offset);

export function buildDeliveryRoadSurfaces(roads=newDeliveryRoadConnections){
  if(!roads)return [];
  const surfaces=[],asphalt=roads.existingRoads.map(r=>deliveryRoadRectangle(r.from,r.to,r.width));
  const sourceCycles=roads.existingRoads.flatMap(r=>[-1,1].map(side=>lineAlong(r.from,r.to,side*7.3,2)));
  const sourceSidewalks=roads.existingRoads.flatMap(r=>[-1,1].map(side=>lineAlong(r.from,r.to,side*9.75,2.3)));
  const add=(id,label,material,surfaceY,polygon,obstacles=[],kind=material)=>{
    cutRoadPolygons(polygon,obstacles).forEach((points,i)=>surfaces.push({id:`${id}-${i}`,label,material,kind,surfaceY,points,walkable:true}));
  };
  for(const street of roads.streets){
    const length=Math.hypot(street.to[0]-street.from[0],street.to[1]-street.from[1]),padding=street.endPadding??0;
    const direction=street.to.map((value,i)=>(value-street.from[i])/(length||1));
    const from=street.from.map((value,i)=>value-direction[i]*padding),to=street.to.map((value,i)=>value+direction[i]*padding);
    const polygon=deliveryRoadRectangle(from,to,street.width);
    add(street.id,street.label,'asfalto',street.surfaceY,polygon,asphalt);asphalt.push(polygon);
    // One-way markings keep the narrow northern bus corridor clear of the rail.
    for(const side of [-1,1]){
      const axis=Math.abs(street.to[0]-street.from[0])>Math.abs(street.to[1]-street.from[1])?0:1;
      const gaps=(street.edgeGaps??[]).filter(gap=>gap.side===side).sort((a,b)=>a.from-b.from);
      let start=street.from[axis];
      for(const gap of [...gaps,{from:street.to[axis],to:street.to[axis]}]){
        if(gap.from>start){
          const from=[...street.from],to=[...street.to];from[axis]=start;to[axis]=gap.from;
          add(`${street.id}-borda-${side}-${start}`,street.label,'branco',.241,lineAlong(from,to,side*(street.width/2-.12),.12),roads.existingRoads.map(r=>deliveryRoadRectangle(r.from,r.to,r.width)),'borda');
        }
        start=gap.to;
      }
    }
    for(const [i,position] of street.arrowPositions.entries())addArrow(`${street.id}-seta-${i}`,street.label,position,street.direction,.241,add);
  }
  const cycles=[...sourceCycles];
  for(const lane of roads.cycleLanes){
    const polygon=deliveryRoadRectangle(lane.from,lane.to,lane.width);
    add(lane.id,lane.label,'ciclofaixa',lane.surfaceY,polygon,cycles);cycles.push(polygon);
    for(const side of [-1,1])add(`${lane.id}-borda-${side}`,lane.label,'branco',.245,lineAlong(lane.from,lane.to,side*(lane.width/2-.06),.08),sourceCycles,'borda-ciclofaixa');
    for(const [i,position] of lane.symbols.entries())addBicycle(`${lane.id}-bicicleta-${i}`,lane.label,position,lane.direction,add);
  }
  const sidewalks=[...sourceSidewalks,...asphalt,...cycles];
  for(const sidewalk of roads.sidewalks){
    const polygon=deliveryRoadRectangle(sidewalk.from,sidewalk.to,sidewalk.width);
    add(sidewalk.id,sidewalk.label,'calcada',sidewalk.surfaceY,polygon,sidewalks);sidewalks.push(polygon);
  }
  for(const crossing of roads.crossings){
    const [x,z]=crossing.position,[dx,dz]=crossing.direction,nx=-dz,nz=dx;
    for(let i=-2;i<=2;i++){
      const p=[x+dx*i*.72,z+dz*i*.72];
      add(`${crossing.id}-faixa-${i}`,crossing.label,'branco',crossing.surfaceY,deliveryRoadRectangle([p[0]-nx*crossing.span/2,p[1]-nz*crossing.span/2],[p[0]+nx*crossing.span/2,p[1]+nz*crossing.span/2],.4),[],'travessia');
    }
  }
  return surfaces;
}
function orientedPolygon(points,position,direction){
  const [dx,dz]=direction,nx=-dz,nz=dx;
  return points.map(([across,along])=>[position[0]+nx*across+dx*along,position[1]+nz*across+dz*along]).reverse();
}
function addArrow(id,label,position,direction,surfaceY,add){
  add(`${id}-haste`,label,'branco',surfaceY,orientedPolygon([[-.12,-1],[.12,-1],[.12,.35],[-.12,.35]],position,direction),[],'seta');
  add(`${id}-ponta`,label,'branco',surfaceY,orientedPolygon([[-.6,.15],[.6,.15],[0,1]],position,direction),[],'seta');
}
function addBicycle(id,label,position,direction,add){
  const transform=p=>orientedPolygon([p],position,direction)[0];
  const stroke=(key,a,b)=>add(`${id}-${key}`,label,'branco',.249,deliveryRoadRectangle(transform(a),transform(b),.055),[],'bicicleta');
  for(const [index,center] of [[0,[0,-.58]],[1,[0,.58]]])for(let i=0;i<12;i++){
    const a=i*Math.PI/6,b=(i+1)*Math.PI/6;
    stroke(`roda-${index}-${i}`,[center[0]+Math.cos(a)*.27,center[1]+Math.sin(a)*.27],[center[0]+Math.cos(b)*.27,center[1]+Math.sin(b)*.27]);
  }
  const frame=[[[0,-.58],[.34,-.06]],[[.34,-.06],[0,.58]],[[0,-.58],[0,.18]],[[0,.18],[.34,-.06]],[[0,.58],[.38,.34]],[[.38,.34],[.38,.64]],[[-.12,-.06],[.47,-.06]]];
  frame.forEach(([a,b],i)=>stroke(`quadro-${i}`,a,b));
}
