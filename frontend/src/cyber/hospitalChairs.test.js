import test from 'node:test';
import assert from 'node:assert/strict';
import {Group,Mesh,BoxGeometry,MeshStandardMaterial} from 'three';
import {hospitalOriginalChairRootNames,hideHospitalChairRoots,restoreHospitalChairRoots,createHospitalChairClone} from './hospitalChairs.js';

test('only the fourteen exact original chair roots are hidden, keeping colliders, doors and other furniture intact',()=>{
  const source=new Group();
  for(const name of hospitalOriginalChairRootNames){
    const chair=new Group();chair.name=name;
    const seat=new Mesh(new BoxGeometry(),new MeshStandardMaterial());seat.name=`${name}_SEAT`;chair.add(seat);source.add(chair);
  }
  const preserved=['HSP15_CHAIR_COLLIDER_0_0','HSP15_CHAIR_0_0_EXTRA','HSP15_CHAIR_ROOM_05','HSP15_DESK','HSP15_ROOM_DOOR_01','HSP15_PUBLIC_DOOR'];
  for(const name of preserved){const object=new Group();object.name=name;source.add(object);}
  const copy=source.clone(true),before=source.children.map(node=>[node.name,node.visible]);
  assert.deepEqual(hideHospitalChairRoots(copy).sort(),[...hospitalOriginalChairRootNames].sort());
  assert.equal(hospitalOriginalChairRootNames.length,14);
  for(const name of hospitalOriginalChairRootNames){
    const root=copy.getObjectByName(name);assert.equal(root.visible,false);assert.equal(root.children.length,1);
    assert.equal(root.children[0].parent,root,'descendant hierarchy is preserved beneath the hidden root');
  }
  for(const name of preserved)assert.equal(copy.getObjectByName(name).visible,true,name);
  restoreHospitalChairRoots(copy);
  for(const name of hospitalOriginalChairRootNames)assert.equal(copy.getObjectByName(name).visible,true,'originals remain available on replacement load failure');
  assert.deepEqual(source.children.map(node=>[node.name,node.visible]),before,'cached source was not mutated');
});

test('chair name metadata survives loader sanitization and a configuration cannot hide arbitrary hospital nodes',()=>{
  const scene=new Group(),chair=new Group(),door=new Group();
  chair.name='sanitized';chair.userData.name='HSP15_CHAIR_ROOM_01';door.name='HSP15_PUBLIC_DOOR';scene.add(chair,door);
  assert.deepEqual(hideHospitalChairRoots(scene,['HSP15_CHAIR_ROOM_01','HSP15_PUBLIC_DOOR']),['HSP15_CHAIR_ROOM_01']);
  assert.equal(chair.visible,false);assert.equal(door.visible,true);
  const another=new Group();another.name='HSP15_CHAIR_ROOM_02';another.userData.name='unrelated-override';scene.add(another);
  assert.deepEqual(hideHospitalChairRoots(scene,['HSP15_CHAIR_ROOM_02']),['HSP15_CHAIR_ROOM_02']);
  assert.equal(another.visible,false,'exact object name remains eligible when metadata has a different label');
});

test('fourteen chair instances have independent transforms while sharing immutable geometry and materials',()=>{
  const source=new Group(),seat=new Mesh(new BoxGeometry(.65,.12,.6),new MeshStandardMaterial({color:'#54756d'}));
  source.add(seat);const instances=hospitalOriginalChairRootNames.map(()=>createHospitalChairClone(source));
  assert.equal(new Set(instances.map(instance=>instance.uuid)).size,14);
  instances[0].position.x=8;instances[0].children[0].visible=false;
  for(const instance of instances){
    const mesh=instance.children[0];assert.equal(mesh.geometry,seat.geometry);assert.equal(mesh.material,seat.material);
    assert.equal(mesh.castShadow,true);assert.equal(mesh.receiveShadow,true);
  }
  assert.equal(instances[1].position.x,0);assert.equal(instances[1].children[0].visible,true);
  assert.equal(seat.visible,true);assert.equal(seat.castShadow,false);assert.equal(seat.receiveShadow,false);
  assert.equal(source.position.x,0);
});
