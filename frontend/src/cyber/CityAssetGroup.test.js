import test from 'node:test';
import assert from 'node:assert/strict';
import {createElement} from 'react';
import {renderToString} from 'react-dom/server';
import {CityAssetGroup} from './CityAssetBoundary.js';

const vehicle=key=>createElement('span',{key,'data-ready':'vehicle'},'VEHICLE_READY');
const building=createElement('span',{key:'building','data-ready':'building'},'BUILDING_READY');

test('the real city group keeps ready vehicles and buildings while one patient waits',()=>{
  function WaitingPatient(){throw new Promise(()=>{});}
  const html=renderToString(createElement(CityAssetGroup,null,
    building,[vehicle('car'),vehicle('truck')],createElement(WaitingPatient,{key:'patient'})));
  assert.equal((html.match(/VEHICLE_READY/g)??[]).length,2);
  assert.match(html,/BUILDING_READY/);
});

test('the real city group contains a failed feature without removing its ready peers',()=>{
  function FailedClassroom(){throw new Error('Classroom fixture unavailable');}
  const html=renderToString(createElement(CityAssetGroup,null,
    vehicle('car'),createElement(FailedClassroom,{key:'classroom'}),building));
  assert.match(html,/VEHICLE_READY/);
  assert.match(html,/BUILDING_READY/);
});

test('mapped city children have independent suspension limits, including later ready peers',()=>{
  function WaitingVehicle(){throw new Promise(()=>{});}
  const html=renderToString(createElement(CityAssetGroup,null,
    [createElement(WaitingVehicle,{key:'slow-bus'}),vehicle('ready-truck')],false,building));
  assert.match(html,/VEHICLE_READY/);
  assert.match(html,/BUILDING_READY/);
});
