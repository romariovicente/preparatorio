import test from 'node:test';
import assert from 'node:assert/strict';
import {characterNpcMotionSample} from './characterNpcMotion.js';

test('reviewed walking residents move continuously around their safe authored anchor',()=>{
  const entry={id:'resident-a',position:[12,0,-8],heading:.4,walkingAnimationAvailable:true};
  const samples=[0,.5,1,2].map(time=>characterNpcMotionSample(entry,time));
  for(const sample of samples){
    assert.equal(sample.moving,true);assert.ok(sample.position.every(Number.isFinite));assert.ok(Number.isFinite(sample.heading));
    assert.ok(Math.abs(Math.hypot(sample.position[0]-12,sample.position[2]+8)-.32)<1e-9);
  }
  assert.equal(new Set(samples.map(sample=>sample.position.join(','))).size,samples.length);
  assert.deepEqual(entry.position,[12,0,-8]);
});

test('unreviewed static residents keep their authored pose and placement',()=>{
  const entry={id:'resident-static',position:[3,.2,4],heading:-.7,walkingAnimationAvailable:false};
  assert.deepEqual(characterNpcMotionSample(entry,20),{position:[3,.2,4],heading:-.7,moving:false});
  assert.deepEqual(characterNpcMotionSample({...entry,walkingAnimationAvailable:true},Number.NaN),{position:[3,.2,4],heading:-.7,moving:false});
});
