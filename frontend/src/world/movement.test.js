import test from 'node:test';import assert from 'node:assert/strict';import {advancePosition} from './movement.js';
test('diagonal movement has the same speed and large frame gaps are bounded',()=>{
  const a=advancePosition({x:0,z:0},{x:1,z:0},.05);const b=advancePosition({x:0,z:0},{x:1,z:1},.05);
  assert.ok(Math.abs(Math.hypot(b.x,b.z)-a.x)<1e-10);assert.deepEqual(advancePosition({x:0,z:0},{x:1,z:0},10),a);
});
test('campus perimeter and solid display furniture block traversal',()=>{
  assert.equal(advancePosition({x:10,z:0},{x:1,z:0},.05).x,10);
  const p={x:0,z:-3.39};assert.deepEqual(advancePosition(p,{x:0,z:-1},.05),p);
});
