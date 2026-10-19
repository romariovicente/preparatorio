import {assetUrl} from '../config/deploymentConfig.js';
import {Box3,Group,Quaternion,Vector3} from 'three';
import {setWorldShadows} from './modelLighting.js';

const INTERACTIVE_CARS={
  SUP_2010_mercedes_sls_amg:assetUrl('/assets/vehicles/VEH_SLS_Interactive_20261005.glb'),
  SUP_volkswagen_atlas_teramont_cross_sport_2025:assetUrl('/assets/vehicles/VEH_Atlas_Interactive_20261005.glb'),
};
const AXES={X:new Vector3(1,0,0),Y:new Vector3(0,1,0),Z:new Vector3(0,0,1)};
const rotation=new Quaternion();
const finite=value=>Number.isFinite(value)?value:0;
const approach=(current,goal,delta,speed)=>current+Math.sign(goal-current)*Math.min(Math.abs(goal-current),Math.max(0,finite(delta))*speed);

export function interactiveCarUrl(asset) {
  return INTERACTIVE_CARS[asset.sourceId??asset.id]??asset.url;
}

export function createCarRig(source,height) {
  const copy=source.clone(true);copy.updateMatrixWorld(true);
  const box=new Box3().setFromObject(copy),size=box.getSize(new Vector3()),center=box.getCenter(new Vector3());
  const normalizer=new Group();normalizer.add(copy);
  normalizer.position.set(-center.x,-box.min.y,-center.z);
  const outer=new Group();outer.add(normalizer);
  if(Number.isFinite(height)&&height>0&&size.y>0)outer.scale.setScalar(height/size.y);
  const wheels=[],doors=[],windows=[],parts=[];
  copy.traverse(node=>parts.push(node));
  for(const node of parts) {
    const name=node.userData.asset_node_name??node.name;
    if(/^Wheel_[FR][LR]$/.test(name)) {
      const steering=new Group();steering.name=`Steering_${name.slice(6)}`;
      steering.position.copy(node.position);node.parent.add(steering);
      steering.add(node);node.position.set(0,0,0);
      wheels.push({node,steering,baseQuaternion:node.quaternion.clone(),front:name.startsWith('Wheel_F')});
    } else if(/^Door_[FR][LR]$/.test(name)) {
      doors.push({node,baseQuaternion:node.quaternion.clone(),axis:AXES[node.userData.opening_axis_gltf]??AXES.Y,
        openAngle:finite(node.userData.opening_angle_gltf),angle:0});
    } else if(/^Glass_[FR][LR]$/.test(name)) {
      windows.push({node,basePosition:node.position.clone(),drop:Math.max(0,finite(node.userData.window_drop_m)),offset:0});
    }
  }
  setWorldShadows(outer);
  outer.userData.articulatedWheelCount=wheels.length;
  outer.userData.frontDirection='+Z';
  return {outer,wheels,doors,windows};
}

export function animateCarRig(rig,state,delta) {
  // Steering is outside the original wheel quaternion; spin uses the real axle.
  for(const wheel of rig.wheels) {
    wheel.steering.quaternion.setFromAxisAngle(AXES.Y,wheel.front?finite(state.steeringAngle):0);
    rotation.setFromAxisAngle(AXES.X,finite(state.wheelAngle));
    wheel.node.quaternion.copy(wheel.baseQuaternion).premultiply(rotation);
  }
  for(const door of rig.doors) {
    door.angle=approach(door.angle,state.doorOpen?door.openAngle:0,delta,1.8);
    rotation.setFromAxisAngle(door.axis,door.angle);
    door.node.quaternion.copy(door.baseQuaternion).premultiply(rotation);
  }
  for(const glass of rig.windows) {
    glass.offset=approach(glass.offset,state.windowsOpen?glass.drop:0,delta,.7);
    glass.node.position.copy(glass.basePosition);glass.node.position.y-=glass.offset;
  }
}
