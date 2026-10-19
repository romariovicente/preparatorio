import test from 'node:test';
import assert from 'node:assert/strict';
import {BoxGeometry,Group,Mesh,MeshBasicMaterial} from 'three';
import {createSolidIndex,solidMovement} from './collisions.js';
test('real mesh collision stops passage through a solid object and permits a clear path',()=>{
  const scene=new Group(),block=new Mesh(new BoxGeometry(2,2,2),new MeshBasicMaterial());block.position.y=1;scene.add(block);
  const floor=new Mesh(new BoxGeometry(30,.2,30),new MeshBasicMaterial());floor.userData.walkable=true;scene.add(floor);
  const index=createSolidIndex(scene);assert.equal(index.length,1);
  const from={x:0,y:0,z:1.6};assert.deepEqual(solidMovement(index,from,{x:0,y:0,z:1.3}),from);
  assert.equal(solidMovement(index,{x:4,y:0,z:1.6},{x:4,y:0,z:1.3}).z,1.3);
  block.visible=false;assert.equal(createSolidIndex(scene).length,0);
});
