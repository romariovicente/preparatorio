import test from 'node:test';
import assert from 'node:assert/strict';
import {applyCyberAction,createCyberState} from './simulation.js';
import {resolveTruckProfile,truckLocalToWorld} from './truckInteraction.js';
import {changeVehicleLights,lowBeamMaskLevel,vehicleLightingProfile,vehicleLightOutputs} from './vehicleLighting.js';

const scania=vehicleLightingProfile('scania');
const sls=vehicleLightingProfile('SUP_2010_mercedes_sls_amg');

test('SLS position and powered DRL illuminate the lenses without projecting a beam',()=>{
  assert.deepEqual(vehicleLightOutputs(sls,null,true,true),{lamps:[],beams:[]});
  assert.deepEqual(vehicleLightOutputs(sls,null,true,true,true),{lamps:['marker'],beams:[]});
  assert.deepEqual(vehicleLightOutputs(sls,null,false,true,true),{lamps:[],beams:[]});
  assert.deepEqual(vehicleLightOutputs(sls,{mode:'off'},true,true,true),{lamps:[],beams:[]});
  assert.deepEqual(vehicleLightOutputs(sls,{mode:'position'},false,true),{lamps:['marker'],beams:[]});
  assert.deepEqual(vehicleLightOutputs(sls,{mode:'drl'},false,true),{lamps:[],beams:[]});
  assert.deepEqual(vehicleLightOutputs(sls,{mode:'drl'},true,true),{lamps:['marker'],beams:[]});
  assert.equal(changeVehicleLights(sls,null,{auxiliary:'fog',enabled:true}),null);
});

test('the main beam keeps the measured lens pair and reaches farther in high mode',()=>{
  for(const profile of [sls,scania]){
    const low=vehicleLightOutputs(profile,{mode:'low'},true,true);
    const high=vehicleLightOutputs(profile,{mode:'high'},true,true);
    assert.deepEqual(low.lamps,['main','marker']);
    assert.deepEqual(high.lamps,low.lamps);
    assert.ok(high.beams[0].reach>low.beams[0].reach);
    assert.ok(high.beams[0].target[2]>low.beams[0].target[2]);
    assert.deepEqual(vehicleLightOutputs(profile,{mode:'high'},true,false).beams,[]);
    const heading=Math.PI/2;
    const origin=truckLocalToWorld({x:10,z:20,heading},low.beams[0].origin);
    const aim=truckLocalToWorld({x:10,z:20,heading},low.beams[0].target);
    assert.ok(aim.x>origin.x);
    assert.ok(Math.abs(aim.z-origin.z)<1e-8);
  }
});

test('low beam cuts off at the horizon and rises slightly toward the road shoulder',()=>{
  for(const profile of [sls,scania]){
    const [beam]=vehicleLightOutputs(profile,{mode:'low'},true,true).beams;
    const pitch=Math.atan2(beam.origin[1]-beam.target[1],beam.target[2]-beam.origin[2]);
    const horizon=.5+.5*Math.tan(pitch)/Math.tan(beam.angle);
    for(const u of [.25,.75]){
      assert.equal(lowBeamMaskLevel(pitch,beam.angle,u,horizon),0);
      assert.equal(lowBeamMaskLevel(pitch,beam.angle,u,.5),1);
    }
    const shoulder=horizon-.012;
    assert.ok(lowBeamMaskLevel(pitch,beam.angle,.75,shoulder)>lowBeamMaskLevel(pitch,beam.angle,.25,shoulder));
  }
});

test('Scania auxiliaries operate independently and the work light aims back at the hitch',()=>{
  const profile=resolveTruckProfile('scania');
  const state={mode:'off',auxiliaries:{fog:true,driving:true,bar:true,work:true}};
  const output=vehicleLightOutputs(scania,state,true,true);
  assert.deepEqual(output.lamps,['fog','driving','bar','work']);
  assert.equal(output.beams.length,4);
  const work=output.beams.find(beam=>beam.id==='work');
  assert.ok(work.target[2]<work.origin[2]&&work.target[1]<work.origin[1]);
  assert.ok(work.target.every((coordinate,index)=>Math.abs(coordinate-profile.hitch[index])<.002));
  assert.ok(output.beams.find(beam=>beam.id==='fog').angle>output.beams.find(beam=>beam.id==='driving').angle);
  const next=changeVehicleLights(scania,state,{auxiliary:'bar',enabled:false});
  assert.deepEqual(vehicleLightOutputs(scania,next,true,true).lamps,['fog','driving','work']);
});

test('light controls belong to the personal instance and preserve truck movement and trailer swaps',()=>{
  const base={...createCyberState(),position:{x:0,y:0,z:60},trailer:'tanker'};
  const initial=applyCyberAction(base,{type:'SUMMON_VEHICLE',vehicle:'truck',sourceId:'scania'}).state;
  const toggle={type:'VEHICLE_LIGHTS',mode:'low'};
  assert.equal(applyCyberAction(initial,toggle).ok,false);
  const driving={...initial,mode:'truck'};
  const result=applyCyberAction(driving,toggle);
  assert.equal(result.ok,true);
  assert.equal(driving.personalVehicles.truck.lights,undefined);
  const truck=result.state.personalVehicles.truck;
  assert.equal(truck.trailer,'tanker');
  const moved=applyCyberAction(result.state,{type:'TRUCK_DRIVE',keys:{w:true},delta:.1});
  assert.ok(moved.state.personalVehicles.truck.speed>0);
  assert.equal(moved.state.personalVehicles.truck.lights.mode,'low');
  assert.equal(applyCyberAction(moved.state,{type:'TRAILER',trailer:'flatbed'}).ok,false);
  const parked=applyCyberAction(result.state,{type:'TRAILER',trailer:'flatbed'});
  assert.equal(parked.ok,true);
  assert.equal(parked.state.personalVehicles.truck.lights.mode,'low');
  const calledCar=applyCyberAction({...parked.state,mode:'foot'},{type:'SUMMON_VEHICLE',vehicle:'car',sourceId:'car'});
  assert.equal(calledCar.ok,true);
  assert.equal(calledCar.state.personalVehicles.car.lights,undefined);
  const car={...calledCar.state,mode:'car'};
  assert.equal(applyCyberAction(car,{type:'VEHICLE_LIGHTS',auxiliary:'work',enabled:true}).ok,false);
  assert.equal(applyCyberAction(car,{type:'VEHICLE_LIGHTS',mode:'drl'}).state.personalVehicles.car.lights.mode,'drl');
});
