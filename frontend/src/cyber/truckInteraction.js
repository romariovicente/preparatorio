import {resolveAssetReferences} from '../config/deploymentConfig.js';
import profilesRaw from '../config/truckVehicles.json' with {type:'json'};
import {playableCityBounds} from '../config/cityBounds.js';

const configuration=resolveAssetReferences(profilesRaw),profiles=configuration.vehicles;
const availableProfiles=profiles.filter(profile=>profile.ready!==false).map(profile=>Object.freeze({...profile,speed:profile.speed??8}));
const finite=value=>Number.isFinite(value)?value:0;
const clamp=(value,min,max)=>Math.max(min,Math.min(max,value));
const difference=(a,b)=>Math.atan2(Math.sin(a-b),Math.cos(a-b));
export const TRUCK_ARTICULATION_LIMIT=Math.PI/3;
// Dimensions enclose the normalized generated models. Hitch and axle offsets
// share the renderer's floor-centered +Z frame; they are not vehicle origins.
export const TRAILER_DEFINITIONS=Object.fromEntries(configuration.trailers.map(trailer=>[trailer.id,trailer]));

export function listTruckProfiles(){return availableProfiles.map(profile=>structuredClone(profile));}
export function resolveTruckProfile(sourceId='truck'){
  return availableProfiles.find(profile=>profile.id===sourceId||profile.sourceId===sourceId)||
    (sourceId==='truck'?availableProfiles[0]:null);
}
export function resolveTruckTrailer(truck,trailerId=truck.trailer){
  const trailer=TRAILER_DEFINITIONS[trailerId],profile=resolveTruckProfile(truck.sourceId);
  if(!trailer||!profile||!profile.compatibleTrailers?.includes(trailerId))return null;
  return {...trailer,hitch:trailer.hitches?.[profile.trailerMode]??trailer.hitch,
    articulationLimit:profile.trailerArticulationLimits?.[trailerId]??profile.articulationLimit??TRUCK_ARTICULATION_LIMIT};
}
export function truckLocalToWorld(truck,local){
  const heading=finite(truck.heading),c=Math.cos(heading),s=Math.sin(heading);
  return {x:truck.x+local[0]*c+local[2]*s,y:finite(truck.y)+(local[1]??0),z:truck.z-local[0]*s+local[2]*c};
}
export function truckTrailerPose(truck,trailerId=truck.trailer){
  const profile=resolveTruckProfile(truck.sourceId),trailer=resolveTruckTrailer(truck,trailerId);
  if(!profile||!trailer)return null;
  const hitch=truckLocalToWorld(truck,profile.hitch),heading=finite(truck.heading)+finite(truck.articulationAngle);
  return {x:hitch.x-Math.cos(heading)*trailer.hitch[0]-Math.sin(heading)*trailer.hitch[2],y:hitch.y-trailer.hitch[1],
    z:hitch.z+Math.sin(heading)*trailer.hitch[0]-Math.cos(heading)*trailer.hitch[2],heading};
}
function rectangle(pose,width,length,offsetZ=0){
  return [[-width/2,-length/2+offsetZ],[width/2,-length/2+offsetZ],[width/2,length/2+offsetZ],[-width/2,length/2+offsetZ]]
    .map(([x,z])=>{const point=truckLocalToWorld(pose,[x,0,z]);return [point.x,point.z];});
}
export function truckFootprintPolygons(truck){
  const profile=resolveTruckProfile(truck.sourceId);if(!profile)return [];
  const steeringClearance=2*profile.wheelRadius*Math.abs(Math.sin(finite(truck.steeringAngle)));
  const polygons=[rectangle(truck,profile.width+steeringClearance,profile.length)],trailer=resolveTruckTrailer(truck),pose=truckTrailerPose(truck);
  if(trailer&&pose){
    polygons.push(rectangle(pose,trailer.width,trailer.length));
    if(trailer.hitch[2]>trailer.length/2)polygons.push(rectangle(pose,.24,trailer.hitch[2]-trailer.length/2,(trailer.hitch[2]+trailer.length/2)/2));
  }
  return polygons;
}
export function truckColliders(truck){
  return truckFootprintPolygons(truck).map((polygon,index)=>{
    const xs=polygon.map(p=>p[0]),zs=polygon.map(p=>p[1]),minX=Math.min(...xs),maxX=Math.max(...xs),minZ=Math.min(...zs),maxZ=Math.max(...zs);
    return {id:index?'truck-trailer':'truck',x:(minX+maxX)/2,z:(minZ+maxZ)/2,w:maxX-minX,d:maxZ-minZ};
  });
}
function overlap(first,second){
  for(const polygon of [first,second])for(let index=0;index<polygon.length;index++){
    const a=polygon[index],b=polygon[(index+1)%polygon.length],nx=a[1]-b[1],nz=b[0]-a[0];
    if(Math.hypot(nx,nz)<1e-10)continue;
    const one=first.map(p=>p[0]*nx+p[1]*nz),two=second.map(p=>p[0]*nx+p[1]*nz);
    if(Math.max(...one)<=Math.min(...two)||Math.max(...two)<=Math.min(...one))return false;
  }
  return true;
}
export function truckPositionBlocked(truck,obstacles=[],bounds=playableCityBounds){
  const polygons=truckFootprintPolygons(truck);if(!polygons.length)return true;
  if(polygons.flat().some(([x,z])=>!Number.isFinite(x)||!Number.isFinite(z)||x<bounds.minX||x>bounds.maxX||z<bounds.minZ||z>bounds.maxZ))return true;
  return obstacles.some(obstacle=>{
    if(![obstacle.x,obstacle.z,obstacle.w,obstacle.d].every(Number.isFinite)||obstacle.w<=0||obstacle.d<=0)return true;
    return polygons.some(polygon=>overlap(polygon,rectangle({...obstacle,heading:0},obstacle.w,obstacle.d)));
  });
}
export function truckSweepBlocked(previous,next,obstacles=[],bounds=playableCityBounds){
  const yaw=difference(next.heading,previous.heading),joint=finite(next.articulationAngle)-finite(previous.articulationAngle);
  const steps=Math.max(1,Math.ceil(Math.hypot(next.x-previous.x,next.z-previous.z)/.15),Math.ceil(Math.abs(yaw)/.02),Math.ceil(Math.abs(joint)/.02));
  for(let step=1;step<=steps;step++){
    const t=step/steps,pose={...next,x:previous.x+(next.x-previous.x)*t,z:previous.z+(next.z-previous.z)*t,
      heading:previous.heading+yaw*t,articulationAngle:finite(previous.articulationAngle)+joint*t};
    if(truckPositionBlocked(pose,obstacles,bounds))return true;
  }
  return false;
}
export function moveTruck(previous,keys={},delta=0,obstacles=[],bounds=playableCityBounds){
  const profile=resolveTruckProfile(previous.sourceId);if(!profile)return {...previous,speed:0};
  const dt=clamp(finite(delta),0,.05),throttle=(keys.w?1:0)-(keys.s?1:0),steeringAngle=((keys.a?1:0)-(keys.d?1:0))*.48;
  const speed=throttle*(throttle<0?profile.speed*.35:profile.speed),travel=speed*dt;
  const yaw=travel/profile.wheelbase*Math.tan(steeringAngle),heading=finite(previous.heading)+yaw,rearAxleZ=profile.rearAxleZ??-profile.wheelbase/2;
  const axle=truckLocalToWorld(previous,[0,0,rearAxleZ]);
  const next={...previous,x:axle.x+Math.sin(previous.heading+yaw/2)*travel-Math.sin(heading)*rearAxleZ,
    z:axle.z+Math.cos(previous.heading+yaw/2)*travel-Math.cos(heading)*rearAxleZ,
    heading,steeringAngle,speed,wheelAngle:finite(previous.wheelAngle)+travel/profile.wheelRadius,articulationAngle:0};
  const trailer=resolveTruckTrailer(previous),oldPose=truckTrailerPose(previous);
  if(trailer&&oldPose){
    const before=truckLocalToWorld(previous,profile.hitch),after=truckLocalToWorld(next,profile.hitch),dx=after.x-before.x,dz=after.z-before.z,L=trailer.hitch[2]-trailer.axleZ;
    const first=(dx*Math.cos(oldPose.heading)-dz*Math.sin(oldPose.heading))/L;
    const trailerHeading=oldPose.heading+(dx*Math.cos(oldPose.heading+first/2)-dz*Math.sin(oldPose.heading+first/2))/L;
    next.articulationAngle=difference(trailerHeading,heading);
    if(Math.abs(next.articulationAngle)>trailer.articulationLimit)return {...previous,speed:0,blocked:'articulation'};
    const newPose=truckTrailerPose(next),oldAxle=truckLocalToWorld(oldPose,[0,0,trailer.axleZ]),newAxle=truckLocalToWorld(newPose,[0,0,trailer.axleZ]);
    const axleTravel=(newAxle.x-oldAxle.x)*Math.sin(trailerHeading)+(newAxle.z-oldAxle.z)*Math.cos(trailerHeading);
    next.trailerWheelAngle=finite(previous.trailerWheelAngle)+axleTravel/trailer.wheelRadius;
  }
  if(truckSweepBlocked(previous,next,obstacles,bounds))return {...previous,speed:0,blocked:'obstacle'};
  return {...next,blocked:null};
}
export function stopTruck(truck){return {...truck,speed:0,steeringAngle:0};}
export function truckExitPosition(truck,obstacles=[],bounds=playableCityBounds){
  const profile=resolveTruckProfile(truck.sourceId);if(!profile)return null;
  const boxes=[...truckColliders(truck),...obstacles];
  for(const distance of [profile.width/2+.8,3,4,5,7])for(const side of [1,-1])for(const z of [profile.length*.25,0,profile.length/2+.8]){
    const point=truckLocalToWorld(truck,[side*distance,0,z]);
    if(point.x-.4<bounds.minX||point.x+.4>bounds.maxX||point.z-.4<bounds.minZ||point.z+.4>bounds.maxZ)continue;
    if(boxes.some(box=>Math.abs(point.x-box.x)<box.w/2+.45&&Math.abs(point.z-box.z)<box.d/2+.45))continue;
    return point;
  }
  return null;
}
export function safeTruckCopy(position,heading=0,sourceId='truck',trailer='flatbed',obstacles=[],bounds=playableCityBounds){
  const profile=resolveTruckProfile(sourceId);if(!profile)return null;
  const coupled=profile.compatibleTrailers?.includes(trailer)?trailer:'none';
  const blockers=[{x:position.x,z:position.z,w:.8,d:.8},...obstacles];
  for(const step of [5,8,12,16])for(const [dx,dz]of [[step,0],[-step,0],[0,step],[0,-step],[step,step],[-step,step],[step,-step],[-step,-step]]){
    const truck={x:position.x+dx,y:0,z:position.z+dz,heading,sourceId,trailer:coupled,articulationAngle:0,wheelAngle:0,trailerWheelAngle:0,steeringAngle:0,speed:0};
    if(!truckPositionBlocked(truck,blockers,bounds))return truck;
  }
  return null;
}
