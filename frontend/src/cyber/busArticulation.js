import {assetUrl} from '../config/deploymentConfig.js';
import {Box3,Group,Quaternion,Vector3} from 'three';
import {setWorldShadows} from './modelLighting.js';

const AXLE=new Vector3(1,0,0),UP=new Vector3(0,1,0),rotation=new Quaternion();
const finite=value=>Number.isFinite(value)?value:0;
const approach=(value,target,delta)=>value+Math.sign(target-value)*Math.min(Math.abs(target-value),Math.max(0,finite(delta))*1.8);
export const BRT_INTERACTIVE_URL=assetUrl('/assets/new-delivery/VEH_Bus_BRT_Interactive_20261009.glb');
export function interactiveBusUrl(asset){
  return (asset.sourceId??asset.id)==='VEH_Bus_BRT_20261006'?BRT_INTERACTIVE_URL:asset.url;
}

export function createBusRig(source,height){
  const copy=source.clone(true);copy.updateMatrixWorld(true);
  const box=new Box3().setFromObject(copy),size=box.getSize(new Vector3()),center=box.getCenter(new Vector3());
  const normalized=new Group();normalized.add(copy);normalized.position.set(-center.x,-box.min.y,-center.z);
  const outer=new Group();outer.add(normalized);
  if(Number.isFinite(height)&&height>0&&size.y>0)outer.scale.setScalar(height/size.y);
  const parts=[];copy.traverse(node=>parts.push(node));
  const wheels=[],doors=[],bellows=[];let rear=null;
  for(const node of parts){
    const name=node.userData.asset_node_name??node.name;
    if(/^Wheel_\d\d_[LR]$/.test(name)){
      const steering=new Group();steering.position.copy(node.position);node.parent.add(steering);steering.add(node);node.position.set(0,0,0);
      wheels.push({node,steering,base:node.quaternion.clone(),front:Boolean(node.userData.steering_axle)});
    }else if(/^Door_\d\d_[AB]$/.test(name)){
      doors.push({node,base:node.quaternion.clone(),angle:0,open:(name.endsWith('_A')?-1:1)*65*Math.PI/180});
    }else if(name==='RearSection')rear={node,base:node.quaternion.clone()};
    if(node.morphTargetDictionary?.ArticulationLeft!==undefined&&node.morphTargetDictionary?.ArticulationRight!==undefined){
      node.morphTargetInfluences=[...node.morphTargetInfluences];bellows.push(node);
    }
  }
  setWorldShadows(outer);outer.userData.frontDirection='+Z';outer.userData.articulatedWheelCount=wheels.length;
  return {outer,wheels,doors,rear,bellows};
}
export function animateBusRig(rig,state,delta){
  for(const wheel of rig.wheels){
    wheel.steering.quaternion.setFromAxisAngle(UP,wheel.front?finite(state.steeringAngle):0);
    rotation.setFromAxisAngle(AXLE,finite(state.wheelAngle));wheel.node.quaternion.copy(wheel.base).premultiply(rotation);
  }
  for(const door of rig.doors){
    door.angle=approach(door.angle,state.doorOpen?door.open:0,delta);
    rotation.setFromAxisAngle(UP,door.angle);door.node.quaternion.copy(door.base).premultiply(rotation);
  }
  const joint=Math.max(-25*Math.PI/180,Math.min(25*Math.PI/180,finite(state.articulationAngle)));
  if(rig.rear){rotation.setFromAxisAngle(UP,joint);rig.rear.node.quaternion.copy(rig.rear.base).premultiply(rotation);}
  for(const node of rig.bellows){
    node.morphTargetInfluences[node.morphTargetDictionary.ArticulationLeft]=Math.max(0,joint)/(25*Math.PI/180);
    node.morphTargetInfluences[node.morphTargetDictionary.ArticulationRight]=Math.max(0,-joint)/(25*Math.PI/180);
  }
}
