import test from 'node:test';
import assert from 'node:assert/strict';
import world from '../config/realisticWorldManifest.json' with {type:'json'};
import catalog from '../config/suppliedAssets.json' with {type:'json'};
import {canEnterCar,listInteractiveCars,nearbyInteractiveCars,nearestInteractiveCar,resolveCarSource,safeVehicleCopy} from './carInteraction.js';

test('only approved validated vehicle placements enter the interaction list; originals are preserved',()=>{
  const original=JSON.stringify(world),cars=listInteractiveCars();
  assert.equal(cars.length,7);
  assert.deepEqual(resolveCarSource('car').position,{x:20,y:0,z:44});
  assert.ok(cars.every(car=>['SUP_2010_mercedes_sls_amg','SUP_volkswagen_atlas_teramont_cross_sport_2025','SUP_transparency_mercedes_amg_one'].includes(car.asset.sourceId)));
  cars[0].position.x=500;cars[0].asset.height=900;
  assert.equal(resolveCarSource('car').position.x,20);
  assert.equal(resolveCarSource('car').asset.height,1.26);
  assert.equal(JSON.stringify(world),original);
  assert.equal(resolveCarSource('invented'),null);
});

test('all reachable car choices remain available, including AMG beside an existing car',()=>{
  const choices=nearbyInteractiveCars({x:23.5,y:0,z:44},null);
  assert.deepEqual(choices.map(car=>car.id),['car','plaza-amg-one']);
  assert.equal(choices[1].label,'Mercedes-AMG ONE');
  assert.equal(choices[1].asset.sourceId,'SUP_transparency_mercedes_amg_one');
  choices[1].asset.height=999;
  assert.equal(resolveCarSource('plaza-amg-one').asset.height,1.26);
  assert.deepEqual(nearbyInteractiveCars({x:NaN,z:44}),[]);
});

test('click eligibility and nearby prompt stop outside seven metres or on another floor',()=>{
  const car=resolveCarSource('car'),state={mode:'foot',position:{x:13,y:0,z:44}};
  assert.equal(canEnterCar(state,car),true);
  assert.equal(nearestInteractiveCar(state.position,null)?.id,'car');
  assert.equal(canEnterCar({...state,position:{x:12.99,y:0,z:44}},car),false);
  assert.equal(nearestInteractiveCar({x:12.99,y:0,z:44},null),null);
  assert.equal(canEnterCar({...state,position:{x:20,y:1.61,z:44}},car),false);
  assert.equal(nearestInteractiveCar({x:20,y:6,z:44},null),null);
  assert.equal(canEnterCar({...state,sitting:true},car),false);
  assert.equal(canEnterCar({...state,mode:'car'},car),false);
  assert.equal(canEnterCar({...state,elevator:{to:0}},car),false);
});

test('a personal SUV resolves its original placement, height and yaw rather than changing to a sports car',()=>{
  const personal={sourceId:'dealer-suv',x:8,y:0,z:11,heading:Math.PI/2};
  const car=nearestInteractiveCar({x:8,y:0,z:12},personal);
  const source=catalog.find(asset=>asset.id==='SUP_volkswagen_atlas_teramont_cross_sport_2025');
  assert.equal(car.id,'personal-car');
  assert.equal(car.asset.sourceId,source.id);
  assert.equal(car.asset.height,1.73);
  const scale=1.73/source.dimensions[2];
  assert.ok(Math.abs(car.w-source.dimensions[1]*scale)<1e-9);
  assert.ok(Math.abs(car.d-source.dimensions[0]*scale)<1e-9);
  assert.equal(nearestInteractiveCar({x:8,y:0,z:12},{...personal,sourceId:'invented'}),null);
});

test('a vehicle copy clears the source footprint and radius without moving the original',()=>{
  const car=resolveCarSource('car'),original=JSON.stringify(car),radius=1.3;
  const copy=safeVehicleCopy(car,[],radius);
  assert.ok(copy);
  assert.ok(Math.abs(copy.x-car.position.x)>=car.w+radius||Math.abs(copy.z-car.position.z)>=car.d+radius);
  assert.equal(copy.heading,car.heading);
  assert.equal(JSON.stringify(car),original);
});

test('blocked copy positions return null, and edge positions stay wholly inside city bounds',()=>{
  const car=resolveCarSource('car');
  assert.equal(safeVehicleCopy(car,[{x:20,z:44,w:80,d:80}]),null);
  assert.equal(safeVehicleCopy(car,[{x:20,z:44,w:NaN,d:1}]),null);
  const edge={...car,position:{x:116,y:0,z:116}},copy=safeVehicleCopy(edge);
  assert.ok(copy);
  assert.ok(Math.abs(copy.x)+car.w/2+1.3<=118);
  assert.ok(Math.abs(copy.z)+car.d/2+1.3<=118);
});
