import test from 'node:test';
import assert from 'node:assert/strict';
import {playableCityBounds} from '../config/cityBounds.js';
import {createCyberState,applyCyberAction,tickCyberState,CYBER_BOUNDS} from './simulation.js';
import {safeVehicleCopy,resolveCarSource,listInteractiveCars} from './carInteraction.js';
import {livingWorldColliders} from './cityLivingWorld.js';
import {activeWorldPlacements,baseVehicleIsVisible} from './vehiclePlacements.js';
import {nearbyVehicleChoices,chooseNearbyVehicle} from './vehicleSelection.js';
import world from '../config/realisticWorldManifest.json' with {type:'json'};

const overlaps=(a,b,margin=0)=>Math.abs(a.x-b.x)<(a.w+b.w)/2+margin&&Math.abs(a.z-b.z)<(a.d+b.d)/2+margin;

test('campus garage calls, entry and configured parking use the same expanded perimeter as movement',()=>{
  assert.equal(CYBER_BOUNDS,playableCityBounds);
  assert.deepEqual(CYBER_BOUNDS,{minX:-118,maxX:118,minZ:-190,maxZ:118});
  for(const [x,z]of [[-49,-132],[-48,-150]])for(const vehicle of ['car','mototaxi','truck']){
    const initial={...createCyberState(),position:{x,y:.23,z}};
    const sourceId=vehicle==='car'?'plaza-amg-one':vehicle;
    const called=applyCyberAction(initial,{type:'SUMMON_VEHICLE',vehicle,sourceId},{obstacles:livingWorldColliders});
    assert.equal(called.ok,true,`${vehicle} at ${z}: ${called.message}`);
    const own=called.state.personalVehicles[vehicle];
    assert.equal(own.sourceId,sourceId);assert.equal(Object.keys(called.state.personalVehicles).length,1);
    assert.ok(own.z<-118&&own.z>CYBER_BOUNDS.minZ);
    const car=vehicle==='car'?resolveCarSource(sourceId):null;
    if(car)for(const obstacle of livingWorldColliders)assert.equal(overlaps({...own,w:car.w,d:car.d},obstacle,1.3),false,obstacle.id);
    const approached={...called.state,position:{x:own.x,y:.23,z:own.z}};
    const entered=applyCyberAction(approached,{type:vehicle==='car'?'CAR_ENTER':vehicle==='mototaxi'?'MOTO_ENTER':'DRIVE',vehicle,carId:'personal-car',motoId:'personal-moto'},{obstacles:livingWorldColliders});
    assert.equal(entered.ok,true,entered.message);
    let driven=entered.state;
    if(vehicle==='car')for(let step=0;step<3;step++)driven=tickCyberState(driven,.5);
    assert.equal(driven.mode,vehicle);assert.equal(driven.personalVehicles[vehicle].sourceId,sourceId);
    const notAtParking=applyCyberAction(driven,{type:'STORE_VEHICLE'});
    assert.equal(notAtParking.ok,false,'Campus does not silently become an unconfigured parking lot.');
    const stored=applyCyberAction(driven,{type:'STORE_VEHICLE'},{parking:[{id:'campus-test-parking',position:[own.x,0,own.z]}]});
    assert.equal(stored.ok,true,stored.message);assert.deepEqual(stored.state.personalVehicles,{});
    assert.equal(stored.state.garage[vehicle].sourceId,sourceId);assert.equal(stored.state.garage[vehicle].parkingId,'campus-test-parking');
  }
});

test('garage copies retain full footprint margins on every city edge and refuse occupied campus space',()=>{
  const car=resolveCarSource('plaza-amg-one'),radius=1.3;
  for(const position of [{x:-116,y:0,z:-188},{x:116,y:0,z:-188},{x:-116,y:0,z:116},{x:116,y:0,z:116}]){
    const copy=safeVehicleCopy({...car,position},[],radius);assert.ok(copy,JSON.stringify(position));
    assert.ok(copy.x-car.w/2-radius>=CYBER_BOUNDS.minX&&copy.x+car.w/2+radius<=CYBER_BOUNDS.maxX);
    assert.ok(copy.z-car.d/2-radius>=CYBER_BOUNDS.minZ&&copy.z+car.d/2+radius<=CYBER_BOUNDS.maxZ);
  }
  assert.equal(safeVehicleCopy({...car,position:{x:-48,y:0,z:-150}},[{x:-48,z:-150,w:80,d:80}]),null);
});

test('every selected car keeps its authored source through campus summoning instead of becoming the default car',()=>{
  for(const source of listInteractiveCars()){
    const result=applyCyberAction({...createCyberState(),position:{x:-49,y:.23,z:-132}},{type:'SUMMON_VEHICLE',vehicle:'car',sourceId:source.id});
    assert.equal(result.ok,true,result.message);assert.equal(result.state.personalVehicles.car.sourceId,source.id);
    const resolved=resolveCarSource(result.state.personalVehicles.car.sourceId);
    assert.equal(resolved.asset.sourceId,source.asset.sourceId);assert.equal(resolved.asset.sha256,source.asset.sha256);
  }
});

test('AMG and original car remain independently visible, selectable and solid when only one is personal',()=>{
  const car=resolveCarSource('car'),amg=resolveCarSource('plaza-amg-one');
  assert.deepEqual([car.position.x,car.position.z],[20,44]);assert.deepEqual([amg.position.x,amg.position.z],[27,44]);
  const staticVehicles=[car,amg].map(source=>({id:source.id,x:source.position.x,z:source.position.z,w:source.w,d:source.d}));
  const choiceState={...createCyberState(),position:{x:23.5,y:0,z:44}};
  for(const source of [car,amg]){
    assert.equal(chooseNearbyVehicle(choiceState,{kind:'car',id:source.id}).id,source.id);
    const entered=applyCyberAction(choiceState,{type:'CAR_ENTER',carId:source.id},{obstacles:staticVehicles});
    assert.equal(entered.ok,true,entered.message);const personal=entered.state.personalVehicles;
    assert.equal(personal.car.sourceId,source.id);assert.equal(Object.keys(personal).length,1);
    const other=source.id==='car'?amg:car;
    assert.equal(baseVehicleIsVisible('car',personal),source.id!=='car');
    assert.ok(nearbyVehicleChoices({...entered.state,carEntry:null}).some(choice=>choice.id===other.id));
    assert.equal(activeWorldPlacements(world.environmentReplacements,personal).some(record=>record.id==='plaza-amg-one'),source.id!=='plaza-amg-one');
    assert.equal(overlaps({...personal.car,w:source.w,d:source.d},staticVehicles.find(vehicle=>vehicle.id===other.id),1.3),false);
  }
  assert.equal(baseVehicleIsVisible('car',{}),true);
  assert.equal(baseVehicleIsVisible('mototaxi',{mototaxi:{sourceId:'mototaxi'}}),false);
  assert.equal(baseVehicleIsVisible('truck',{truck:{sourceId:'truck'}}),false);
});
