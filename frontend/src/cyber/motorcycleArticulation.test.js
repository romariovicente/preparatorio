import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {BoxGeometry,Group,Mesh,MeshStandardMaterial,Quaternion,Vector3} from 'three';
import {animateMotorcycleRig,createMotorcycleRig,interactiveMotorcycleUrl} from './motorcycleArticulation.js';

test('motorcycle wheels spin on their tilted local axles while steering turns the complete fork assembly',()=>{
  const source=new Group(),steer=new Group();steer.name='Steering_F';steer.position.set(0,1,1);steer.quaternion.setFromAxisAngle(new Vector3(1,0,0),.25);source.add(steer);
  for(const side of ['F','R']) {
    const wheel=new Group();wheel.name=`Wheel_${side}`;wheel.position.set(0,.4,side==='F'?-.8:-1);
    wheel.quaternion.setFromAxisAngle(new Vector3(0,1,0),.18);wheel.add(new Mesh(new BoxGeometry(.2,.7,.7),new MeshStandardMaterial()));
    (side==='F'?steer:source).add(wheel);
  }
  const rig=createMotorcycleRig(source),before=rig.wheels.map(w=>w.node.position.clone());
  animateMotorcycleRig(rig,{wheelAngle:Math.PI/2,steeringAngle:.3});
  for(let i=0;i<rig.wheels.length;i++) {
    const wheel=rig.wheels[i],expected=wheel.baseQuaternion.clone().multiply(new Quaternion().setFromAxisAngle(new Vector3(1,0,0),Math.PI/2));
    assert.ok(wheel.node.quaternion.angleTo(expected)<1e-7);assert.ok(wheel.node.position.distanceTo(before[i])<1e-10);
  }
  const expectedSteering=rig.steering.baseQuaternion.clone().multiply(new Quaternion().setFromAxisAngle(new Vector3(0,1,0),.3));
  assert.ok(rig.steering.node.quaternion.angleTo(expectedSteering)<1e-7);
  animateMotorcycleRig(rig,{wheelAngle:0,steeringAngle:0});
  assert.ok(rig.wheels.every(w=>w.node.quaternion.angleTo(w.baseQuaternion)<1e-7));
});

test('actual derived Kawasaki has front wheel under steering, two nonempty wheels, materials and all 160000 source triangles',()=>{
  const url=interactiveMotorcycleUrl({sourceId:'SUP_cyberpunk_kawasaki_ninja',url:'original.glb'});
  assert.equal(url,'/assets/vehicles/VEH_Kawasaki_Interactive_20261007.glb');
  const buffer=readFileSync(new URL(`../../public${url}`,import.meta.url));
  const doc=JSON.parse(buffer.subarray(20,20+buffer.readUInt32LE(12)).toString());
  const byName=new Map(doc.nodes.map(n=>[n.name,n])),steering=byName.get('Steering_F');
  for(const name of ['Wheel_F','Wheel_R']) {
    const wheel=byName.get(name);assert.ok(wheel.children?.length);assert.equal(wheel.extras.rotation_axis_local_gltf,'X');
  }
  assert.ok(steering.children.includes(doc.nodes.indexOf(byName.get('Wheel_F'))));assert.equal(steering.extras.steering_axis_local_gltf,'Y');
  assert.equal(doc.meshes.reduce((sum,m)=>sum+m.primitives.reduce((s,p)=>s+doc.accessors[p.indices].count/3,0),0),160000);
  assert.equal(doc.meshes.length,4);assert.ok(doc.images.length>=4);assert.equal(doc.scenes.length,1);
});
