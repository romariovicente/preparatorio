import test from 'node:test';
import assert from 'node:assert/strict';
import {AnimationClip,QuaternionKeyframeTrack,VectorKeyframeTrack} from 'three';
import {createCarryAnimations,isCarryRotationTrack} from './carryAnimation.js';
const q=name=>new QuaternionKeyframeTrack(`${name}.quaternion`,[0,1],[0,0,0,1,0,0,0,1]);
const p=name=>new VectorKeyframeTrack(`${name}.position`,[0,1],[0,0,0,0,0,0]);
test('genuine Mixamo upper arms join the carry pose without masking the shoulder or legs',()=>{
  for(const side of ['Left','Right'])assert.equal(isCarryRotationTrack(q(`mixamorig${side}Arm`)),true);
  assert.equal(isCarryRotationTrack(q('mixamorigLeftShoulder')),false);
  assert.equal(isCarryRotationTrack(q('mixamorigLeftUpLeg')),false);
});
test('carrying samples only real Interact arm rotations and keeps locomotion leg tracks',()=>{
  const source=new AnimationClip('Interact',2,[q('L_upper_arm'),q('R_forearm'),q('L_hand'),q('hips'),q('L_thigh'),p('L_hand')]);
  const walk=new AnimationClip('Armature|Walk',1,[q('L_upper_arm'),q('L_thigh'),q('hips'),p('L_hand')]);
  const idle=new AnimationClip('Idle',1,[q('R_forearm'),q('head')]);
  const original=[source,walk,idle],result=createCarryAnimations(original);
  assert.equal(result.overlayTime,1);
  assert.deepEqual(result.clips.find(c=>c.name===result.overlayName).tracks.map(t=>t.name),['L_upper_arm.quaternion','R_forearm.quaternion','L_hand.quaternion']);
  assert.deepEqual(result.clips.find(c=>c.name===result.holdingNames.Walk).tracks.map(t=>t.name),['L_thigh.quaternion','hips.quaternion','L_hand.position']);
  assert.equal(walk.tracks.length,4);assert.equal(source.tracks.length,6);
  assert.notEqual(result.clips.find(c=>c.name===result.overlayName).tracks[0],source.tracks[0]);
});
test('a character with no Interact arm animation receives no invented carry overlay',()=>{
  const originals=[new AnimationClip('Idle',1,[q('hips')])];
  const result=createCarryAnimations(originals);
  assert.equal(result.clips,originals);assert.equal(result.overlayName,null);assert.deepEqual(result.holdingNames,{});
});
