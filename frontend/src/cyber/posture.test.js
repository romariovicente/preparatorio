import test from 'node:test';
import assert from 'node:assert/strict';
import {Bone,Group,Vector3} from 'three';
import {createUprightPosture} from './posture.js';
test('upright adjustment reduces torso lean without moving the feet or changing a dance pose',()=>{
  const root=new Group(),hip=new Bone(),spine=new Bone(),neck=new Bone(),head=new Bone(),foot=new Bone();
  spine.name='mixamorig:Spine1';neck.name='mixamorig:Neck';head.name='mixamorig:Head';
  root.add(hip);hip.add(spine,foot);spine.add(neck);neck.add(head);
  spine.position.y=1;neck.position.set(0,.5,.13);head.position.set(0,.2,.035);
  root.updateMatrixWorld(true);const before=neck.getWorldPosition(new Vector3()).z,feet=foot.getWorldPosition(new Vector3());
  const adjust=createUprightPosture(root);adjust('Dance');assert.equal(neck.getWorldPosition(new Vector3()).z,before);
  adjust('Idle');assert.ok(neck.getWorldPosition(new Vector3()).z<before);assert.deepEqual(foot.getWorldPosition(new Vector3()).toArray(),feet.toArray());
});

test('upright adjustment also recognizes the lowercase bones used by preliminary character rigs',()=>{
  const root=new Group(),hips=new Bone(),spine=new Bone(),neck=new Bone(),head=new Bone();
  spine.name='spine';neck.name='neck';head.name='head';root.add(hips);hips.add(spine);spine.add(neck);neck.add(head);
  spine.position.y=1;neck.position.set(0,.45,.11);head.position.set(0,.2,.03);root.updateMatrixWorld(true);
  const before=neck.getWorldPosition(new Vector3()).z;
  createUprightPosture(root)('Walk');
  assert.ok(neck.getWorldPosition(new Vector3()).z<before);
});
