import test from 'node:test';
import assert from 'node:assert/strict';
import {carMotion,wheelRotation,STEERING_LIMIT} from './vehicleMotion.js';
test('front steering turns the chassis only while travelling, including reversed steering in reverse',()=>{
  const right=carMotion(0,{w:true,d:true},.05),reverse=carMotion(0,{s:true,d:true},.05),stopped=carMotion(0,{d:true},.05);
  assert.equal(right.steeringAngle,-STEERING_LIMIT);assert.ok(right.heading<0);assert.ok(reverse.heading>0);assert.equal(stopped.heading,0);
  assert.equal(carMotion(0,{w:true},.05).heading,0);assert.equal(carMotion(0,{w:true,s:true},.05).speed,0);
});
test('wheel angle follows signed ground distance and remains fixed when collision stops travel',()=>{
  const a={x:0,z:0};assert.equal(wheelRotation(0,a,{x:0,z:.32},0),1);assert.equal(wheelRotation(0,a,{x:0,z:-.32},0),-1);assert.equal(wheelRotation(2,a,a,0),2);
});
