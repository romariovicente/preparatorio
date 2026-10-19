import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {BoxGeometry,Group,Mesh,MeshStandardMaterial,Quaternion,Vector3} from 'three';
import {animateCarRig,createCarRig,interactiveCarUrl} from './carArticulation.js';

test('steering and axle spin preserve centers and original orientation, with rear steering fixed',()=>{
  const source=new Group(),base=new Quaternion().setFromAxisAngle(new Vector3(0,0,1),.3);
  for(const side of ['FL','FR','RL','RR']) {
    const wheel=new Group();wheel.name=`Wheel_${side}`;wheel.position.set(side.endsWith('L')?1:-1,.5,side.startsWith('F')?1.5:-1.5);
    wheel.quaternion.copy(base);wheel.add(new Mesh(new BoxGeometry(.2,.8,.8),new MeshStandardMaterial()));source.add(wheel);
  }
  const rig=createCarRig(source),before=rig.wheels.map(w=>w.node.getWorldPosition(new Vector3()));
  animateCarRig(rig,{wheelAngle:Math.PI/2,steeringAngle:.4},.05);rig.outer.updateMatrixWorld(true);
  for(let i=0;i<rig.wheels.length;i++) {
    const wheel=rig.wheels[i],after=wheel.node.getWorldPosition(new Vector3());
    assert.ok(after.distanceTo(before[i])<1e-10,'wheel must remain centered on axle');
    const expected=new Quaternion().setFromAxisAngle(new Vector3(1,0,0),Math.PI/2).multiply(base);
    assert.ok(wheel.node.quaternion.angleTo(expected)<1e-7);
    assert.ok(wheel.steering.quaternion.angleTo(new Quaternion().setFromAxisAngle(new Vector3(0,1,0),wheel.front?.4:0))<1e-7);
  }
  assert.ok(source.children.every(w=>w.quaternion.angleTo(base)<1e-7),'shared original must remain unchanged');
});

test('only lateral glass lowers and reverses while windshield stays fixed',()=>{
  const source=new Group(),door=new Group();door.name='Door_FL';door.userData={opening_axis_gltf:'Y',opening_angle_gltf:-1.05};
  const glass=new Group();glass.name='Glass_FL';glass.position.y=.8;glass.userData.window_drop_m=.49;door.add(glass);source.add(door);
  const windshield=new Group();windshield.name='Windshield';windshield.position.y=1;source.add(windshield);
  source.add(new Mesh(new BoxGeometry(2,2,4),new MeshStandardMaterial()));
  const rig=createCarRig(source);animateCarRig(rig,{doorOpen:true,windowsOpen:true},1);
  assert.equal(rig.windows[0].node.position.y,.8-.49);assert.equal(rig.doors[0].angle,-1.05);
  assert.equal(rig.outer.getObjectByName('Windshield').position.y,1);
  animateCarRig(rig,{doorOpen:false,windowsOpen:false},1);
  assert.equal(rig.windows[0].node.position.y,.8);assert.equal(rig.doors[0].angle,0);
});

test('saved GLBs contain nonempty wheels, lateral glass and door metadata, preserving all faces',()=>{
  for(const [sourceId,file,expectedTriangles,windowCount] of [
    ['SUP_2010_mercedes_sls_amg','VEH_SLS_Interactive_20261005',159999,2],
    ['SUP_volkswagen_atlas_teramont_cross_sport_2025','VEH_Atlas_Interactive_20261005',487954,4],
  ]) {
    assert.equal(interactiveCarUrl({sourceId,url:'old.glb'}),`/assets/vehicles/${file}.glb`);
    const buffer=readFileSync(new URL(`../../public/assets/vehicles/${file}.glb`,import.meta.url));
    const doc=JSON.parse(buffer.subarray(20,20+buffer.readUInt32LE(12)).toString());
    const nodes=doc.nodes,byName=new Map(nodes.map(n=>[n.name,n]));
    for(const side of ['FL','FR','RL','RR']) {
      const wheel=byName.get(`Wheel_${side}`);assert.ok(wheel.children?.length);assert.equal(wheel.extras.rotation_axis_gltf,'X');
    }
    assert.equal(nodes.filter(n=>/^Glass_[FR][LR]$/.test(n.name)).length,windowCount);
    for(const glass of nodes.filter(n=>/^Glass_[FR][LR]$/.test(n.name))) {
      const parent=byName.get(`Door_${glass.name.slice(6)}`);
      assert.ok(parent.children.includes(nodes.indexOf(glass)));assert.ok(glass.extras.window_drop_m>0);
      assert.ok(parent.extras.opening_angle_gltf);assert.ok(glass.children?.length);
    }
    const triangles=doc.meshes.reduce((sum,m)=>sum+m.primitives.reduce((s,p)=>s+doc.accessors[p.indices].count/3,0),0);
    assert.equal(triangles,expectedTriangles);assert.equal(doc.scenes.length,1);
  }
});
