import test from 'node:test';
import assert from 'node:assert/strict';
import {applyCyberAction,createCyberState,tickCyberState,JUMP_PHYSICS} from './simulation.js';
test('a grounded jump rises, reaches its apex and lands without sinking or changing the floor',()=>{
  let state=applyCyberAction(createCyberState(),{type:'JUMP'}).state;let max=0;
  for(let i=0;i<80;i++){state=tickCyberState(state,1/60);max=Math.max(max,state.jumpHeight);assert.ok(state.jumpHeight>=0);assert.equal(state.position.y,0);}
  assert.ok(Math.abs(max-JUMP_PHYSICS.velocity**2/(2*JUMP_PHYSICS.gravity))<.001);
  assert.equal(state.jump,null);assert.equal(state.jumpHeight,0);assert.equal(applyCyberAction(state,{type:'JUMP'}).ok,true);
});
test('no double jump, seated jump, vehicle jump, lift jump or pending car entry jump',()=>{
  const initial=createCyberState(),jump=applyCyberAction(initial,{type:'JUMP'}).state;
  for(const state of [jump,{...initial,sitting:true},{...initial,mode:'car'},{...initial,elevator:{}},{...initial,carEntry:{}}])assert.equal(applyCyberAction(state,{type:'JUMP'}).ok,false);
  assert.equal(applyCyberAction({...jump,position:{x:23,y:0,z:46}},{type:'CAR_ENTER',carId:'car'}).ok,false);
});
