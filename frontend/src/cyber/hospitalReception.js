import {Box3} from 'three';
import config from '../config/hospitalReception.json' with {type:'json'};
import {assetUrl} from '../config/deploymentConfig.js';

export const hospitalReception=config;
export const HOSPITAL_PLATFORM_URL=assetUrl('/assets/environments/ENV_Hospital_Entrance_Platform_20261019.glb');
const worldCollider=box=>({...box,x:box.x+config.position[0],z:box.z+config.position[2],minY:box.minY+config.position[1],maxY:box.maxY+config.position[1]});
export const hospitalStaticColliders=config.staticColliders.filter(box=>box.maxY>.4&&box.minY<1.85).map(worldCollider);
export function createHospitalRuntime(){
  return {dynamicColliders:[...config.publicDoor.leaves,...config.roomDoors].map(door=>worldCollider(door.closedCollider))};
}
export function hospitalColliders(runtime){return [...hospitalStaticColliders,...((runtime?.current??runtime)?.dynamicColliders??createHospitalRuntime().dynamicColliders)];}
export function markHospitalFloors(scene){
  scene.traverse(object=>{
    if(!object.isMesh)return;
    for(let parent=object;parent;parent=parent.parent)if(config.floorPrefixes.some(prefix=>parent.name.startsWith(prefix))){object.userData.walkable=true;object.userData.hospitalFloor=true;break;}
  });
}
export function hospitalGroundSurfaces(surfaces,position){
  const inside=Math.abs(position.x-config.position[0])<config.width/2&&Math.abs(position.z-config.position[2])<config.depth/2;
  if(!inside)return surfaces;
  const interior=surfaces.filter(mesh=>mesh.userData.hospitalFloor);
  return interior.length?interior:surfaces;
}
export function markHospitalPlatformFloors(scene){
  scene.traverse(object=>{if(object.isMesh){object.userData.walkable=true;object.receiveShadow=true;}});
}
export function readHospitalDoorColliders(scene){
  scene.updateWorldMatrix(true,true);
  return [...config.publicDoor.leaves.map(leaf=>leaf.name),...config.roomDoors.map(room=>room.hingeName)].flatMap(name=>{
    const node=scene.getObjectByName(name);if(!node)return [];
    const box=new Box3().setFromObject(node);
    return box.isEmpty()?[]:[{id:name,x:(box.min.x+box.max.x)/2,z:(box.min.z+box.max.z)/2,w:box.max.x-box.min.x,d:box.max.z-box.min.z,minY:box.min.y,maxY:box.max.y}];
  });
}
export function roomDoorwayOccupied(room,positions,radius=.42){
  const a=room.closedCollider,b=room.openCollider;
  const minX=config.position[0]+Math.min(a.x-a.w/2,b.x-b.w/2)-radius,maxX=config.position[0]+Math.max(a.x+a.w/2,b.x+b.w/2)+radius;
  const minZ=config.position[2]+Math.min(a.z-a.d/2,b.z-b.d/2)-radius,maxZ=config.position[2]+Math.max(a.z+a.d/2,b.z+b.d/2)+radius;
  return positions.some(p=>p&&Math.abs((p.y??0)-config.position[1])<1.85&&p.x>minX&&p.x<maxX&&p.z>minZ&&p.z<maxZ);
}
