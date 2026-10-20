import test from 'node:test';
import assert from 'node:assert/strict';
import {characterRoster,characterOptions,rosterPlan,rosterObstacles,rosterZones,rosterPlacementExclusions} from './characterCityPlan.js';

const overlap=(a,b)=>Math.abs(a.x-b.x)<(a.w+b.w)/2-1e-6&&Math.abs(a.z-b.z)<(a.d+b.d)/2-1e-6;

test('actual city roster represents twenty assets and twenty-one figures with honest control modes',()=>{
  assert.equal(characterRoster.length,20);assert.equal(characterRoster.reduce((sum,entry)=>sum+entry.figures,0),21);
  assert.equal(characterOptions.length,20);assert.equal(rosterPlan.allRepresented,true);assert.deepEqual(rosterPlan.unplaced,[]);
  assert.equal(rosterPlan.placements.length,20);assert.equal(rosterZones.length,20);assert.equal(rosterObstacles.length,20);
  assert.equal(characterRoster.filter(entry=>entry.controlMode==='native').length,2);
  assert.equal(characterRoster.filter(entry=>entry.controlMode==='fixed-pose').length,1);
  assert.ok(characterRoster.filter(entry=>entry.asset.quality==='prototype').every(entry=>!entry.controllable));
});

test('actual NPC footprints avoid roads, buildings, classroom, habitats, engine and each other',()=>{
  for(let index=0;index<rosterObstacles.length;index++){
    const collider=rosterObstacles[index];
    assert.ok([collider.x,collider.z,collider.w,collider.d].every(Number.isFinite));
    for(const exclusion of rosterPlacementExclusions)assert.equal(overlap(collider,exclusion),false,`${collider.id} overlaps ${exclusion.id??JSON.stringify(exclusion)}`);
    for(const prior of rosterObstacles.slice(0,index))assert.equal(overlap(collider,prior),false,`${collider.id} overlaps ${prior.id}`);
  }
  const roads=rosterPlacementExclusions.filter(box=>/^roster-.*-road$/.test(box.id??''));assert.equal(roads.length,4);
  for(const actor of rosterPlan.placements){
    assert.ok(actor.position[0]>-118&&actor.position[0]<118&&actor.position[2]>-118&&actor.position[2]<118);
    assert.ok(actor.position.every(Number.isFinite));assert.ok(Number.isFinite(actor.heading));
  }
});

test('player arrival and NPC approach points remain clear instead of trapping a player inside an NPC',()=>{
  const arrival={x:0,z:25,w:.8,d:.8};
  for(const obstacle of rosterObstacles)assert.equal(overlap(arrival,obstacle),false,obstacle.id);
  for(const zone of rosterZones){
    const approach={x:zone.position[0],z:zone.position[2],w:.8,d:.8};
    for(const obstacle of [...rosterPlacementExclusions,...rosterObstacles]){
      if(obstacle.id==='roster-player-arrival')continue;
      assert.equal(overlap(approach,obstacle),false,`${zone.id} approach overlaps ${obstacle.id??JSON.stringify(obstacle)}`);
    }
  }
});
