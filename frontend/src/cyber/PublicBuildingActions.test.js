import test from 'node:test';
import assert from 'node:assert/strict';
import buildings from '../config/buildingDoors.json' with {type:'json'};
import PublicBuildingActions from './PublicBuildingActions.js';
import {changeLocalDoor,publicDoorCapabilities,publicDoorScopeLabel} from './localDoors.js';

const hospital=buildings.find(building=>building.id==='hospital');
const position={x:48,y:.26,z:-22.6};

test('public offline hospital controls open the actual local door and then permit entry',()=>{
  let doors={},entered=false;
  const props={building:hospital,position,mode:'foot',connected:false,onVisit:()=>{},onToggle:building=>{
    const result=changeLocalDoor(doors,building,{position});assert.equal(result.ok,true);doors=result.doors;
  },onEnter:()=>{entered=true;}};
  let buttons=PublicBuildingActions({...props,open:false}).props.children;
  assert.equal(buttons[1].props.disabled,false);
  assert.equal(buttons[2].props.disabled,true);
  buttons[1].props.onClick();
  assert.equal(doors.hospital.open,true);
  buttons=PublicBuildingActions({...props,open:doors.hospital.open}).props.children;
  assert.equal(buttons[2].props.disabled,false);
  buttons[2].props.onClick();assert.equal(entered,true);
});

test('public door capability preserves shared operation while rejecting private, remote, malformed and other-floor access',()=>{
  assert.deepEqual(publicDoorCapabilities(hospital,{position,connected:true,open:true}),{canToggle:true,canEnter:true,nearby:true,scope:'shared'});
  for(const overrides of [{position:{...position,x:80}},{position:{...position,y:6}},{position:{...position,x:NaN}},{mode:'car'}]){
    const actions=PublicBuildingActions({building:hospital,position,mode:'foot',open:true,...overrides}).props.children;
    assert.equal(actions[1].props.disabled,true);assert.equal(actions[2].props.disabled,true);
  }
  assert.equal(publicDoorCapabilities({id:'creator-home'},{position}).canToggle,false);
  assert.equal(changeLocalDoor({},hospital,{position:{x:NaN,z:-22.6}}).ok,false);
  assert.match(publicDoorScopeLabel(false),/nesta sessão/);
  assert.doesNotMatch(publicDoorScopeLabel(false),/compartilhada/);
  assert.match(publicDoorScopeLabel(true),/conectados/);
});
