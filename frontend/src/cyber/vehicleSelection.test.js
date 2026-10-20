import test from 'node:test';
import assert from 'node:assert/strict';
import {nearbyVehicleChoices,chooseNearbyVehicle,worldVehicleClickHandler} from './vehicleSelection.js';
import NearbyVehiclePicker from './NearbyVehiclePicker.js';
import {applyCyberAction,createCyberState,tickCyberState,DRIVE_VEHICLES} from './simulation.js';
import {resolveCarSource,listInteractiveCars} from './carInteraction.js';
import {nearbyMotorcycles,listMotorcycles} from './motorcycleInteraction.js';
import {activeWorldPlacements} from './vehiclePlacements.js';
import world from '../config/realisticWorldManifest.json' with {type:'json'};
import buildings from '../config/buildingDoors.json' with {type:'json'};
import city from '../config/cyberWorldManifest.json' with {type:'json'};
import delivery from '../config/newDeliveryWorld.json' with {type:'json'};

test('picker exposes every nearby vehicle and explicit AMG selection wins over a nearer car',()=>{
  const state={...createCyberState(),position:{x:22,y:0,z:44}},choices=nearbyVehicleChoices(state);
  assert.deepEqual(choices.map(choice=>choice.id),['car','plaza-amg-one']);
  let selected;
  const picker=NearbyVehiclePicker({choices,onSelect:choice=>{selected=choice;},selectedKey:'car:plaza-amg-one'});
  const buttons=picker.props.children[1].props.children;
  assert.equal(buttons.length,2);assert.equal(buttons[1].props['aria-pressed'],true);
  buttons[1].props.onClick();
  assert.equal(chooseNearbyVehicle(state,selected).id,'plaza-amg-one');
  assert.equal(chooseNearbyVehicle(state).id,'car');
  assert.equal(chooseNearbyVehicle(state,{kind:'car',id:'hospital-suv'}),null,'unreachable selected car must not silently become another car');
  assert.equal(chooseNearbyVehicle(state,null).id,'car','clearing stale selection immediately restores proximity selection');
  assert.equal(chooseNearbyVehicle(state,{kind:'car',id:'personal-car'}),null,'a stale personal selection does not enter another car');
});

test('AMG personal copy suppresses only its own static rendering/collision source until parking',()=>{
  const records=world.environmentReplacements,original=JSON.stringify(records);
  const personal={car:{sourceId:'plaza-amg-one',x:31,y:0,z:44}};
  const active=activeWorldPlacements(records,personal);
  assert.equal(active.some(record=>record.id==='plaza-amg-one'),false);
  assert.equal(active.length,records.length-1);
  assert.equal(active.some(record=>record.id==='dealer-sports'),true);
  assert.ok(activeWorldPlacements(records,{}).some(record=>record.id==='plaza-amg-one'));
  assert.equal(JSON.stringify(records),original);
});

test('every approved authored car and motorcycle has its own click target instead of selecting a single default',()=>{
  const calls=[];let stopped=0;
  for(const car of listInteractiveCars()){
    const handler=worldVehicleClickHandler(car.id,{onSelectCar:id=>calls.push(['car',id])});
    assert.equal(typeof handler,'function');handler({stopPropagation:()=>{stopped++;}});
    assert.deepEqual(calls.at(-1),['car',car.id]);
  }
  for(const moto of listMotorcycles()){
    const handler=worldVehicleClickHandler(moto.id,{onSelectMoto:id=>calls.push(['moto',id])});
    assert.equal(typeof handler,'function');handler({stopPropagation:()=>{stopped++;}});
    assert.deepEqual(calls.at(-1),['moto',moto.id]);
  }
  assert.equal(stopped,listInteractiveCars().length+listMotorcycles().length);
  assert.equal(worldVehicleClickHandler('invented',{onSelectCar:()=>{throw new Error('unknown vehicle selected');}}),undefined);
});

test('nearby personal motorcycle and both cars are selectable without duplicate source vehicles or other-floor access',()=>{
  const state={...createCyberState(),position:{x:23.5,y:0,z:44},personalVehicles:{mototaxi:{sourceId:'mototaxi',x:24,y:0,z:44,heading:0}}};
  const choices=nearbyVehicleChoices(state);
  assert.deepEqual(new Set(choices.map(choice=>choice.key)),new Set(['moto:personal-moto','car:car','car:plaza-amg-one']));
  assert.equal(chooseNearbyVehicle(state,{kind:'moto',id:'personal-moto'}).id,'personal-moto');
  assert.deepEqual(nearbyVehicleChoices({...state,position:{...state.position,y:6}}),[]);
  assert.deepEqual(nearbyVehicleChoices({...state,mode:'car'}),[]);
  assert.deepEqual(nearbyVehicleChoices({...state,position:{x:NaN,z:44}}),[]);
  assert.ok(nearbyVehicleChoices({...state,jump:{}}).every(choice=>!choice.canEnter));
  assert.deepEqual(nearbyMotorcycles(state.position,{sourceId:'invented',x:24,z:44}),[]);
});

test('bus, truck and agricultural choices preserve their existing vehicle handlers',()=>{
  const state={...createCyberState(),position:{x:91,y:0,z:50}};
  assert.equal(nearbyVehicleChoices(state,7,DRIVE_VEHICLES).find(choice=>choice.kind==='drive')?.id,'truck');
  assert.equal(chooseNearbyVehicle(state,{kind:'drive',id:'truck'},7,DRIVE_VEHICLES).id,'truck');
  const bus={id:'bus',control:'player',x:20,y:0,z:44,heading:0,stopped:true,doorOpen:true};
  const busState={...state,position:{x:20,y:0,z:45},liveBuses:{bus}};
  assert.ok(nearbyVehicleChoices(busState).some(choice=>choice.kind==='bus'&&choice.id==='bus'&&choice.canEnter));
});

test('AMG entry, engine, movement and parking retain the selected model and a single personal vehicle',()=>{
  const source=resolveCarSource('plaza-amg-one'),original=JSON.stringify(source);
  let state={...createCyberState(),position:{x:29,y:0,z:44}};
  let result=applyCyberAction(state,{type:'CAR_ENTER',carId:source.id});
  assert.equal(result.ok,true,result.message);state=result.state;
  assert.equal(state.carControls.doorOpen,true);
  for(let i=0;i<3;i++)state=tickCyberState(state,.5);
  assert.equal(state.mode,'car');assert.equal(state.personalVehicles.car.sourceId,source.id);
  assert.equal(state.carControls.engineOn,false);
  result=applyCyberAction(state,{type:'CAR_ENGINE'});assert.equal(result.ok,true);state=result.state;
  const moved=applyCyberAction(state,{type:'MOVE',position:{x:state.position.x,y:state.position.y,z:state.position.z+1}});
  assert.equal(moved.ok,true);state=moved.state;
  result=applyCyberAction(state,{type:'STORE_VEHICLE'},{parking:[{id:'test',position:[state.position.x,0,state.position.z]}]});
  assert.equal(result.ok,true);assert.deepEqual(result.state.personalVehicles,{});
  assert.equal(result.state.garage.car.sourceId,source.id);
  assert.equal(JSON.stringify(resolveCarSource(source.id)),original);
  const summoned=applyCyberAction({...createCyberState(),position:{x:23,y:0,z:44}},{type:'SUMMON_VEHICLE',vehicle:'car',sourceId:source.id});
  assert.equal(summoned.ok,true);assert.equal(summoned.state.personalVehicles.car.sourceId,source.id);
  assert.equal(Object.keys(summoned.state.personalVehicles).length,1);
});

test('AMG placement clears public building volumes and authored solid obstacles at realistic supplied scale',()=>{
  const car=resolveCarSource('plaza-amg-one');
  assert.ok(car.w>2&&car.w<2.3);assert.ok(car.d>4.5&&car.d<5);
  const boxes=[...city.colliders,...delivery.colliders,...buildings.map(building=>({id:building.id,x:building.center[0],z:building.center[2],w:building.width,d:building.depth}))];
  for(const box of boxes)assert.ok(Math.abs(box.x-car.position.x)>=(box.w+car.w)/2+.4||Math.abs(box.z-car.position.z)>=(box.d+car.d)/2+.4,`AMG overlaps ${box.id}`);
});
