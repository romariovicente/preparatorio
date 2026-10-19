import test from 'node:test';
import assert from 'node:assert/strict';
import { Bone, Group, Mesh, BoxGeometry, MeshBasicMaterial, Vector3 } from 'three';
import { createSeatedClone } from './seating.js';

test('FK seating bends the cloned legs forward and keeps source skeleton untouched', () => {
  const source=new Group(),hips=new Bone(),thigh=new Bone(),shin=new Bone(),foot=new Bone();
  hips.position.y=.9;thigh.name='L_thigh';shin.name='L_shin';foot.name='L_foot';
  shin.position.y=-.45;foot.position.y=-.4;hips.add(thigh);thigh.add(shin);shin.add(foot);source.add(hips);
  source.add(new Mesh(new BoxGeometry(.5,1.7,.3),new MeshBasicMaterial()));source.updateMatrixWorld(true);
  const original=thigh.quaternion.clone(),seat=createSeatedClone(source),clonedThigh=seat.group.getObjectByName('L_thigh'),clonedShin=seat.group.getObjectByName('L_shin'),clonedFoot=seat.group.getObjectByName('L_foot');
  seat.group.updateMatrixWorld(true);
  const hipPosition=clonedThigh.getWorldPosition(new Vector3()),kneePosition=clonedShin.getWorldPosition(new Vector3()),anklePosition=clonedFoot.getWorldPosition(new Vector3());
  assert.equal(seat.posed,true);assert.ok(kneePosition.z>hipPosition.z+.4);assert.ok(Math.abs(kneePosition.y-hipPosition.y)<1e-6);assert.ok(anklePosition.y<kneePosition.y-.3);
  assert.deepEqual(thigh.quaternion.toArray(),original.toArray());
});

test('Mixamo leg names can use the seating pose without altering the original rig', () => {
  const source=new Group(),hips=new Bone(),thigh=new Bone(),shin=new Bone(),foot=new Bone();
  hips.position.y=.9;thigh.name='mixamorig:LeftUpLeg';shin.name='mixamorig:LeftLeg';foot.name='mixamorig:LeftFoot';
  shin.position.y=-.45;foot.position.y=-.4;hips.add(thigh);thigh.add(shin);shin.add(foot);source.add(hips);
  source.add(new Mesh(new BoxGeometry(.5,1.7,.3),new MeshBasicMaterial()));source.updateMatrixWorld(true);
  const original=thigh.quaternion.clone(),seat=createSeatedClone(source);
  seat.group.updateMatrixWorld(true);
  const seatedThigh=seat.group.getObjectByName(thigh.name),seatedShin=seat.group.getObjectByName(shin.name),seatedFoot=seat.group.getObjectByName(foot.name);
  const hipPosition=seatedThigh.getWorldPosition(new Vector3()),kneePosition=seatedShin.getWorldPosition(new Vector3()),anklePosition=seatedFoot.getWorldPosition(new Vector3());
  assert.equal(seat.posed,true);assert.ok(kneePosition.z>hipPosition.z+.4);assert.ok(Math.abs(kneePosition.y-hipPosition.y)<1e-6);assert.ok(anklePosition.y<kneePosition.y-.3);
  assert.deepEqual(thigh.quaternion.toArray(),original.toArray());
});
