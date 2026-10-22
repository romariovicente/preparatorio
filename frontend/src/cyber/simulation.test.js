import test from 'node:test';
import assert from 'node:assert/strict';
import { advanceCityPosition, applyCyberAction, createCyberState, DRIVE_VEHICLES, FARM_PLOTS, FLOWER_BASES, restoreCyberState, sampleTransit, sampleWorldClock, tickCyberState, TRANSIT_ROUTES } from './simulation.js';

test('a single accelerated clock agrees on phone text, phase and Earth orbit', () => {
  const first=sampleWorldClock(0),later=sampleWorldClock(90),cycle=sampleWorldClock(240);
  assert.equal(first.text,'09:00'); assert.equal(first.phase,'Manhã'); assert.equal(later.text,'18:00'); assert.equal(later.night,true);
  assert.equal(cycle.text,first.text); assert.equal(cycle.day,1); assert.ok(Math.abs(cycle.earthPosition[0]-first.earthPosition[0])<1e-9);
  assert.deepEqual(sampleWorldClock(NaN),first);
});
test('transport preserves stopped boarding and safe exit, and moves passengers with the vehicle', () => {
  let state=createCyberState();
  assert.equal(applyCyberAction(state,{type:'BOARD',vehicle:'bus'}).ok,false);
  state={...state,position:{x:0,y:0,z:35}};
  state=applyCyberAction(state,{type:'BOARD',vehicle:'bus'}).state;
  for(let i=0;i<24;i++)state=tickCyberState(state,.5);
  assert.equal(sampleTransit(TRANSIT_ROUTES.bus,state.elapsed).stopped,false);
  assert.equal(applyCyberAction(state,{type:'EXIT'}).ok,false);
  assert.equal(state.position.y,1.1); assert.ok(state.position.x>0);
  state={...state,elapsed:0};
  const exit=applyCyberAction(state,{type:'EXIT'});assert.equal(exit.ok,true);assert.equal(exit.state.mode,'foot');assert.equal(exit.state.position.y,0);
});
test('flower copies preserve authored garden; farming and fishing require reach and elapsed time', () => {
  let state={...createCyberState(),position:{...FLOWER_BASES[0].position}};
  const original=JSON.stringify(FLOWER_BASES),pick=applyCyberAction(state,{type:'FLOWER',flowerId:FLOWER_BASES[0].id});
  assert.equal(pick.state.inventory.flowers,1);assert.equal(JSON.stringify(FLOWER_BASES),original);
  assert.equal(applyCyberAction(pick.state,{type:'FLOWER',flowerId:FLOWER_BASES[0].id}).ok,false);
  state={...pick.state,position:{...FARM_PLOTS[0].position}};
  state=applyCyberAction(state,{type:'PLANT',plotId:'plot-1'}).state;
  assert.equal(state.inventory.seeds,5);assert.equal(applyCyberAction(state,{type:'HARVEST',plotId:'plot-1'}).ok,false);
  state={...state,elapsed:20};state=applyCyberAction(state,{type:'HARVEST',plotId:'plot-1'}).state;
  assert.equal(state.inventory.harvest,1);assert.equal(state.inventory.seeds,6);
  state={...state,position:{x:100,y:0,z:0}};state=applyCyberAction(state,{type:'CAST'}).state;
  assert.equal(applyCyberAction(state,{type:'REEL'}).ok,false);
  state={...state,elapsed:28};state=applyCyberAction(state,{type:'REEL'}).state;assert.equal(state.inventory.fish,1);assert.equal(state.fishing,null);
});
test('movement, lift, teleport and restoration reject invalid state safely', () => {
  const moved=advanceCityPosition({x:117.9,y:0,z:0},{x:10,y:0,z:0},5,10);assert.equal(moved.x,118);
  const blocked=advanceCityPosition({x:0,y:0,z:0},{x:1,y:0,z:0},.05,10,[{x:.5,z:0,w:1,d:1}]);assert.equal(blocked.x,0);
  let state={...createCyberState(),position:{x:-17,y:0,z:56}};
  state=applyCyberAction(state,{type:'ELEVATOR',floor:-1}).state;
  for(let i=0;i<8;i++)state=tickCyberState(state,.5);
  assert.equal(state.position.y,-6);assert.equal(state.elevator,null);
  assert.equal(applyCyberAction(state,{type:'TELEPORT',zoneId:'unknown'},{zones:[]}).ok,false);
  const restored=restoreCyberState({getItem:()=>JSON.stringify({version:1,inventory:{seeds:-10,flowers:3,fish:Infinity},outfit:{scrubs:false,coat:true,color:'#247fba'}})});
  assert.equal(restored.inventory.seeds,6);assert.equal(restored.inventory.flowers,3);assert.equal(restored.outfit.coat,true);assert.equal(restored.outfit.scrubs,false);assert.equal(restored.outfit.color,'#ffffff');
});
test('driving and parking affect a personal vehicle copy while authored models remain unchanged',()=>{
  const original=JSON.stringify(DRIVE_VEHICLES);
  let state=createCyberState();assert.equal(applyCyberAction(state,{type:'DRIVE',vehicle:'truck'}).ok,false);
  state={...state,position:{x:90,y:0,z:50}};state=applyCyberAction(state,{type:'DRIVE',vehicle:'truck'}).state;
  assert.equal(state.mode,'truck');assert.equal(state.sitting,true);assert.equal(state.position.y,1.5);
  state=applyCyberAction(state,{type:'MOVE',position:{x:90,y:1.5,z:52},heading:1}).state;
  assert.equal(state.personalVehicles.truck.z,52);assert.equal(applyCyberAction(state,{type:'PARK'},{parking:[]}).ok,false);
  const result=applyCyberAction(state,{type:'PARK'},{parking:[{id:'utility',position:[90,.1,50],size:[6,16]}]});
  assert.equal(result.ok,true);assert.equal(result.state.mode,'foot');assert.deepEqual(result.state.personalVehicles,{});
  assert.equal(result.state.garage.truck.parkingId,'utility');
  assert.equal(JSON.stringify(DRIVE_VEHICLES),original);
  assert.equal(applyCyberAction(result.state,{type:'TRAILER',trailer:'unknown'}).ok,false);
});
test('object interaction plays a bounded action without interrupting a vehicle or elevator',()=>{
  const initial=createCyberState(),result=applyCyberAction(initial,{type:'INTERACT'});
  assert.equal(result.ok,true);assert.equal(result.state.action,'Interact');
  assert.equal(result.state.actionUntil,2);assert.deepEqual(result.state.inventory,initial.inventory);
  let state=result.state;for(let i=0;i<5;i++)state=tickCyberState(state,.5);
  assert.equal(state.action,'Idle');assert.equal(state.actionUntil,null);
  assert.equal(applyCyberAction({...initial,mode:'bus',sitting:true},{type:'INTERACT'}).ok,false);
  assert.equal(applyCyberAction({...initial,elevator:{from:0,to:-6,startedAt:0}},{type:'INTERACT'}).ok,false);
});
