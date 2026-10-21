import test from 'node:test';
import assert from 'node:assert/strict';
import {hospitalPatientRoute,sampleHospitalPatientRoute,validateHospitalPatientRoute} from './hospitalPatientFlow.js';

test('hospital patients follow a finite sidewalk route to the public triage entrance',()=>{
  assert.equal(validateHospitalPatientRoute(),true);
  const start=hospitalPatientRoute[0],entrance=hospitalPatientRoute.at(-1);
  assert.deepEqual(start,[55,.02,-8]);
  assert.ok(Math.hypot(entrance[0]-48,entrance[2]-(-25.85))<.5);
  for(let time=0;time<=90;time+=.25){
    const sample=sampleHospitalPatientRoute(time);
    assert.ok(sample.position.every(Number.isFinite));assert.ok(Number.isFinite(sample.heading));
    assert.ok(sample.progress>=0&&sample.progress<=1);
    assert.ok(['walking','waiting'].includes(sample.phase));
  }
});

test('patients wait at both endpoints and walk in both directions without leaving the route',()=>{
  assert.equal(sampleHospitalPatientRoute(0).phase,'waiting');
  const samples=Array.from({length:500},(_,index)=>sampleHospitalPatientRoute(index*.2));
  assert.ok(samples.some(sample=>sample.phase==='waiting'&&sample.progress===1));
  assert.ok(samples.some(sample=>sample.phase==='walking'&&sample.forward));
  assert.ok(samples.some(sample=>sample.phase==='walking'&&!sample.forward));
  assert.throws(()=>sampleHospitalPatientRoute(1,{route:[[0,0,0]]}),/inválida/);
});
