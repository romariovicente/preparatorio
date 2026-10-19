import {assetUrl} from '../config/deploymentConfig.js';
import {Box3,Group,Quaternion,Vector3} from 'three';
import {setWorldShadows} from './modelLighting.js';

const AXLE=new Vector3(1,0,0),STEERING=new Vector3(0,1,0),rotation=new Quaternion();
const finite=value=>Number.isFinite(value)?value:0;
export function interactiveMotorcycleUrl(asset) {
  return asset.sourceId==='SUP_cyberpunk_kawasaki_ninja'?assetUrl('/assets/vehicles/VEH_Kawasaki_Interactive_20261007.glb'):asset.url;
}
export function createMotorcycleRig(source,height=1.3) {
  const copy=source.clone(true);copy.updateMatrixWorld(true);
  // Precise vertex bounds avoid sinking tilted authored wheel axles into the road.
  const box=new Box3().setFromObject(copy,true),size=box.getSize(new Vector3()),center=box.getCenter(new Vector3());
  const normalizer=new Group();normalizer.add(copy);normalizer.position.set(-center.x,-box.min.y,-center.z);
  const outer=new Group();outer.add(normalizer);
  if(Number.isFinite(height)&&height>0&&size.y>0)outer.scale.setScalar(height/size.y);
  const wheels=[];let steering=null;
  copy.traverse(node=>{
    const name=node.userData.asset_node_name??node.name;
    if(/^Wheel_[FR]$/.test(name))wheels.push({node,baseQuaternion:node.quaternion.clone()});
    if(name==='Steering_F')steering={node,baseQuaternion:node.quaternion.clone()};
  });
  setWorldShadows(outer);outer.userData.articulatedWheelCount=wheels.length;outer.userData.frontDirection='+Z';
  return {outer,wheels,steering};
}
export function animateMotorcycleRig(rig,{wheelAngle=0,steeringAngle=0}={}) {
  if(rig.steering) {
    const limit=rig.steering.node.userData.steering_limit_radians??.42;
    rotation.setFromAxisAngle(STEERING,Math.max(-limit,Math.min(limit,finite(steeringAngle))));
    rig.steering.node.quaternion.copy(rig.steering.baseQuaternion).multiply(rotation);
  }
  for(const wheel of rig.wheels) {
    rotation.setFromAxisAngle(AXLE,finite(wheelAngle));
    wheel.node.quaternion.copy(wheel.baseQuaternion).multiply(rotation);
  }
}
