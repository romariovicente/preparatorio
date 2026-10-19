import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {CYBER_BOUNDS} from './simulation.js';
import {macroWorldPlan as plan,footprint,containedBy,footprintsOverlap,polylineLengthMeters,
  plannedJourney,roadSegments,roadIntersectsFootprint,roadNetwork,pointOnSegment,routeUsesRoadNetwork} from './macroWorldPlan.js';

test('the macro plan stays inactive and preserves the real city and original character/classroom assets',()=>{
  assert.equal(plan.runtimeEnabled,false);assert.equal(plan.status,'planning-only');
  assert.deepEqual(CYBER_BOUNDS,plan.legacy.runtimeBounds);
  assert.deepEqual(plan.legacy.transform,{position:[0,0,0],rotation:[0,0,0],scale:[1,1,1]});
  const runtime=readFileSync(new URL('./CyberCity.jsx',import.meta.url),'utf8');
  assert.doesNotMatch(runtime,/import[^;]*macroWorldPlan/);
  for(const asset of plan.legacy.protectedAssets){
    const bytes=readFileSync(new URL('../../public'+asset.url,import.meta.url));
    assert.equal(bytes.length,asset.bytes,asset.role);
    assert.equal(createHash('sha256').update(bytes).digest('hex'),asset.sha256,asset.role);
  }
});

test('districts, buildable lots, runway reserve and coast fit the 4 km world without overlapping parcels',()=>{
  const bounds=plan.world.bounds;
  assert.equal((bounds.maxX-bounds.minX)*(bounds.maxZ-bounds.minZ),plan.world.terrainAreaM2);
  for(const [index,district]of plan.districts.entries()){
    const box=footprint(district);assert.ok(containedBy(box,bounds,20),district.id);
    for(const other of plan.districts.slice(index+1))assert.equal(footprintsOverlap(box,footprint(other)),false,`${district.id}/${other.id}`);
  }
  for(const [index,lot]of plan.lots.entries()){
    const district=plan.districts.find(item=>item.id===lot.districtId);assert.ok(district,lot.id);
    assert.ok(containedBy(footprint(lot),footprint(district),20),lot.id);
    assert.ok(containedBy(footprint({center:lot.center,size:[lot.buildingSize[0],lot.buildingSize[2]]}),footprint(lot),5),lot.id);
    for(const other of plan.lots.slice(index+1))assert.equal(footprintsOverlap(footprint(lot),footprint(other),10),false,`${lot.id}/${other.id}`);
  }
  assert.ok(containedBy(plan.world.coastalWater.bounds,bounds,20));
  for(const lot of plan.lots)assert.equal(footprintsOverlap(footprint(lot),plan.world.coastalWater.bounds),false,`${lot.id}/water`);
});

test('full road corridors clear preserved geometry, lots and world edges, with coherent street profiles',()=>{
  for(const profile of Object.values(plan.roadProfiles)){
    const total=profile.drivableWidth+profile.medianWidth+2*(profile.shoulderWidthEachSide+profile.sidewalkWidthEachSide+profile.cycleWidthEachSide);
    assert.ok(Math.abs(total-profile.rightOfWayWidth)<1e-7);
  }
  for(const segment of roadSegments()){
    assert.ok(polylineLengthMeters([segment.from,segment.to])>0,segment.roadId);
    for(const point of [segment.from,segment.to])assert.ok(containedBy(footprint({center:point,size:[segment.width,segment.width]}),plan.world.bounds,5),segment.roadId);
    assert.equal(roadIntersectsFootprint(segment,plan.legacy.visualTerrainBounds,10),false,`${segment.roadId}/legacy`);
    assert.equal(roadIntersectsFootprint(segment,plan.world.coastalWater.bounds,5),false,`${segment.roadId}/water`);
    for(const lot of plan.lots)assert.equal(roadIntersectsFootprint(segment,footprint(lot),5),false,`${segment.roadId}/${lot.id}`);
  }
});

test('the connected road network reaches every public entrance and planned journeys last 2–10 minutes',()=>{
  const network=roadNetwork(),first=network.keys().next().value,visited=new Set([first]),queue=[first];
  for(let index=0;index<queue.length;index++)for(const next of network.get(queue[index]).neighbors)if(!visited.has(next)){visited.add(next);queue.push(next);}
  assert.equal(visited.size,network.size,'No disconnected road fragment');
  const segments=roadSegments();
  for(const lot of plan.lots.filter(item=>item.approach)){
    const access=segments.filter(segment=>segment.roadId===lot.publicAccess);
    assert.ok(access.some(segment=>pointOnSegment(lot.approach,segment.from,segment.to)),lot.id);
  }
  for(const route of plan.plannedRoutes){
    assert.deepEqual(route.path[0],plan.lots.find(lot=>lot.id===route.fromLot).approach,route.id);
    assert.deepEqual(route.path.at(-1),plan.lots.find(lot=>lot.id===route.toLot).approach,route.id);
    assert.ok(routeUsesRoadNetwork(route),route.id);
    const journey=plannedJourney(route);assert.ok(journey.minutes>=2&&journey.minutes<=10,`${route.id}: ${journey.minutes}`);
  }
});

test('distance calculations use meters, reject invalid input and retain sensible human short trips',()=>{
  assert.equal(polylineLengthMeters([[0,0],[3,4],[3,16]]),17);
  assert.throws(()=>polylineLengthMeters([[0,0],[NaN,4]]),TypeError);
  assert.throws(()=>plannedJourney({path:[[0,0],[3,4]]},'unknown'),RangeError);
  assert.throws(()=>plannedJourney({path:[[0,0],[3,4]],plannedDwellSeconds:-1},'walk'),RangeError);
  assert.ok(plannedJourney({path:[[0,0],[200,0]],plannedDwellSeconds:0},'walk').minutes<2);
  assert.ok(plannedJourney({path:[[0,0],[1000,0]],plannedDwellSeconds:0},'walk').minutes<10);
  const near={from:[-5,-2],to:[5,-2],width:2},box={minX:-1,maxX:1,minZ:0,maxZ:2};
  assert.equal(roadIntersectsFootprint(near,box),false);
  assert.equal(roadIntersectsFootprint({...near,width:4},box),true,'A sidewalk grazing the lot must count');
});
