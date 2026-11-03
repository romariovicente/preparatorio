import {Box3,Group,Quaternion,Vector3} from 'three';
import {setWorldShadows} from './modelLighting.js';

const up=new Vector3(0,1,0),axle=new Vector3(1,0,0),rotation=new Quaternion();
export function createTruckRig(source,height,sourceYaw=0,alreadyNormalized=false,coupled=false){
  const copy=source.clone(true),aligned=new Group();aligned.add(copy);if(!alreadyNormalized)copy.rotation.y+=sourceYaw;aligned.updateMatrixWorld(true);
  const box=new Box3().setFromObject(aligned,true),size=box.getSize(new Vector3()),center=box.getCenter(new Vector3()),normalized=new Group();
  normalized.add(aligned);if(!alreadyNormalized)normalized.position.set(-center.x,-box.min.y,-center.z);
  const outer=new Group();outer.add(normalized);if(!alreadyNormalized&&size.y>0&&height>0)outer.scale.setScalar(height/size.y);
  const nodes=[];copy.traverse(node=>nodes.push(node));const wheels=[];
  for(const node of nodes){
    if(coupled&&node.userData.hide_when_coupled)node.visible=false;
    const name=node.userData.runtime_node_name??node.userData.asset_node_name??node.name;
    if(!/^Wheel_\d+_[LR]$|^VEH_Wheel(?:\.\d+)?$/.test(name))continue;
    const steering=new Group();steering.position.copy(node.position);node.parent.add(steering);steering.add(node);node.position.set(0,0,0);
    wheels.push({name,node,steering,base:node.quaternion.clone(),front:Boolean(node.userData.steering_axle)});
  }
  outer.updateMatrixWorld(true);for(const wheel of wheels)wheel.lateralPosition=wheel.steering.getWorldPosition(new Vector3()).x;
  setWorldShadows(outer);outer.userData.articulatedWheelCount=wheels.length;outer.userData.frontDirection='+Z';
  return {outer,wheels};
}
export function animateTruckRig(rig,state={},profile={}){
  for(const wheel of rig.wheels){
    let angle=wheel.front&&Number.isFinite(state.steeringAngle)?state.steeringAngle:0;
    if(angle&&profile.wheelbase>0){const radius=profile.wheelbase/Math.tan(angle);angle=Math.atan(profile.wheelbase/(radius-wheel.lateralPosition));}
    wheel.steering.quaternion.setFromAxisAngle(up,angle);
    const definition=profile.wheels?.find(entry=>entry.name===wheel.name),radiusScale=profile.wheelRadius>0&&definition?.radius>0?profile.wheelRadius/definition.radius:1;
    rotation.setFromAxisAngle(axle,(Number.isFinite(state.wheelAngle)?state.wheelAngle:0)*radiusScale);wheel.node.quaternion.copy(wheel.base).premultiply(rotation);
  }
}
