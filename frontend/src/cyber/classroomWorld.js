import {resolveAssetReferences} from '../config/deploymentConfig.js';
import configRaw from '../config/classroomAssets.json' with {type:'json'};
const config=resolveAssetReferences(configRaw);

export const classroomWorld=config;
export const CLASSROOM_DOOR_ID=config.door.id;
export const classroomZones=[{id:config.id,label:config.label,position:config.center,approach:config.approach}];
export const classroomApproach={x:config.approach[0],y:config.approach[1],z:config.approach[2]};
export const classroomEntry={x:config.entry[0],y:config.entry[1],z:config.entry[2]};
const clamp01=value=>Math.max(0,Math.min(1,Number.isFinite(value)?value:0));
const stateOf=runtime=>runtime?.current??runtime;

export function createClassroomRuntime(){
  return {open:false,progress:0,manualOpen:null,quietSeconds:0,occupied:false};
}
export function classroomLocalPoint(position){
  return {x:position.x-config.center[0],y:(position.y??0)-config.center[1],z:position.z-config.center[2]};
}
export function insideClassroom(position){
  if(!position)return false;
  const local=classroomLocalPoint(position);
  return Math.abs(local.x)<6.8&&Math.abs(local.z)<5.8&&local.y>-.3&&local.y<3.9;
}
export function classroomDoorOccupied(position,radius=.4){
  if(!position)return false;
  const p=classroomLocalPoint(position),door=config.door;
  return Math.abs(p.y)<1.8&&Math.abs(p.x-door.center[0])<door.width/2+radius&&Math.abs(p.z-door.center[2])<1.05;
}
export function toggleClassroomDoor(runtime){
  const state=stateOf(runtime);if(!state)return false;
  state.manualOpen=!state.open;
  state.open=state.manualOpen||state.occupied;
  state.quietSeconds=0;
  return state.open;
}
export function openClassroomDoor(runtime){
  const state=stateOf(runtime);if(!state)return;
  state.manualOpen=true;state.open=true;state.quietSeconds=0;
}

// Mutable Three.js runtime data is shared between the animation and movement
// loops. Proximity opens the real leaf; closing waits until the opening is clear.
export function stepClassroomDoor(runtime,position,delta,mode='foot'){
  const state=stateOf(runtime);if(!state)return null;
  const elapsed=Math.max(0,Math.min(.1,Number.isFinite(delta)?delta:0));
  const local=position?classroomLocalPoint(position):null,door=config.door;
  const distance=local?Math.hypot(local.x-door.center[0],local.z-door.center[2]):Infinity;
  const sameLevel=local&&Math.abs(local.y)<1.8&&mode==='foot';
  const near=sameLevel&&distance<=door.proximityMeters;
  state.occupied=Boolean(sameLevel&&classroomDoorOccupied(position));
  if(state.manualOpen===false&&distance>door.releaseMeters)state.manualOpen=null;
  state.quietSeconds=near||state.occupied?0:state.quietSeconds+elapsed;
  const automatic=near||(state.open&&state.quietSeconds<door.closeDelaySeconds);
  state.open=state.occupied||(state.manualOpen??automatic);
  const target=state.open?1:0,difference=target-state.progress;
  state.progress=clamp01(state.progress+Math.sign(difference)*Math.min(Math.abs(difference),elapsed/door.durationSeconds));
  return state;
}
export function classroomDoorLeaf(progress=0){
  const door=config.door,angle=door.angleRadians*clamp01(progress),c=Math.cos(angle),s=Math.sin(angle);
  const localX=door.hinge[0]+c*door.width/2,localZ=door.hinge[2]-s*door.width/2;
  return {id:door.id,x:config.center[0]+localX,z:config.center[2]+localZ,
    w:Math.abs(c)*door.width+Math.abs(s)*door.thickness,
    d:Math.abs(s)*door.width+Math.abs(c)*door.thickness,angle};
}
const at=(id,x,z,w,d)=>({id,x:config.center[0]+x,z:config.center[2]+z,w,d});
const staticColliders=[
  at('classroom-front-wall',0,5.92,14,.16),
  at('classroom-rear-wall-left',-1.65,-5.92,10.7,.16),
  at('classroom-rear-wall-right',6.72,-5.92,.56,.16),
  at('classroom-door-infill',4.1515,-5.92,.903,.16),
  at('classroom-door-frame-left',4.65,-5.92,.095,.16),
  at('classroom-door-frame-right',6.41,-5.92,.095,.16),
  ...[-1,1].flatMap(sign=>[
    at('classroom-side-wall-'+sign,sign*6.92,0,.16,11.9),
    at('classroom-side-bench-'+sign,sign*6.64,0,.45,11.5),
    at('classroom-plant-'+sign,sign*5.7,4.7,.62,.62),
  ]),
  ...[-2.05,.1,2.25,4.4].flatMap((row,ri)=>[-4,0,4].flatMap((x,ci)=>[
    at(`classroom-desk-${ri*3+ci+1}`,x,-row+.73,1.35,.78),
    at(`classroom-seat-${ri*3+ci+1}`,x,-row,.7,.7),
  ])),
  at('classroom-lecturer-desk',0,4.29,2,.76),
  at('classroom-anatomy-exhibit',config.educational.position[0],config.educational.position[2],.96,.75),
];
export function classroomColliders(runtime){
  return [...staticColliders,classroomDoorLeaf(stateOf(runtime)?.progress??0)];
}
