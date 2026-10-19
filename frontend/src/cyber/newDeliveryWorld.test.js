import test from 'node:test';
import assert from 'node:assert/strict';
import buildings from '../config/buildingDoors.json' with {type:'json'};
import originalWorld from '../config/cyberWorldManifest.json' with {type:'json'};
import {newDeliveryRuntimeAssets} from '../config/newDeliveryRuntimeAssets.js';
import {newDeliveryWorld,deliveryFootprint,getDeliveryReplacement,newDeliveryRoutes,resolveDeliveryParking,newDeliveryColliders} from './newDeliveryWorld.js';
const overlaps=(a,b,margin=0)=>Math.abs(a.x-b.x)<(a.w+b.w)/2+margin&&Math.abs(a.z-b.z)<(a.d+b.d)/2+margin;
const footprints=buildings.map(b=>({id:b.id,x:b.center[0],z:b.center[2],w:b.width,d:b.depth}));
test('six validated assets enter the gallery with credits and no invented character rigs',()=>{
 assert.equal(newDeliveryRuntimeAssets.length,6);
 for(const asset of newDeliveryRuntimeAssets){assert.ok(asset.name&&asset.credits&&asset.reimportValidated);assert.equal(asset.playable,false);assert.equal(asset.rigged,false);assert.deepEqual(asset.animations,[]);}
 const historical=newDeliveryRuntimeAssets.find(a=>a.sourceCategory==='character');assert.equal(historical.category,'Personagens');assert.match(historical.description,/Dois estudantes/);
 const buses=newDeliveryRuntimeAssets.filter(a=>a.sourceCategory==='bus');assert.ok(buses.every(a=>a.category==='Veículos'&&a.sourceLicenseStatus.includes('No license')));
});
test('bus replacement preserves the approved delivered source and returns independent records',()=>{
 const bus=getDeliveryReplacement('bus');assert.equal(bus.id,'bus');assert.equal(bus.sourceId,'VEH_Bus_City_20261006');assert.ok(bus.height>3&&bus.height<3.3);
 bus.dimensions[0]=0;assert.ok(getDeliveryReplacement('bus').dimensions[0]>2.8);assert.equal(getDeliveryReplacement('unknown'),null);
});
test('terminal and static stop footprints fit urban bounds and avoid every existing building',()=>{
 for(const record of newDeliveryWorld.compositions.filter(r=>['terminal','bus-stop','parked-vehicle','cultural-exhibit'].includes(r.role))){
  const shape=deliveryFootprint(record);assert.ok(Math.abs(shape.x)+shape.w/2<=118,record.id);assert.ok(Math.abs(shape.z)+shape.d/2<=118,record.id);
  assert.deepEqual(footprints.filter(b=>overlaps(shape,b)).map(b=>b.id),[],record.id);
 }
 const terminal=deliveryFootprint(newDeliveryWorld.compositions.find(r=>r.role==='terminal'));
 assert.equal(originalWorld.parking.filter(p=>p.id.startsWith('Centro-')&&overlaps(terminal,{x:p.position[0],z:p.position[2],w:5,d:3.6})).length,4);
 const parked=resolveDeliveryParking(originalWorld.parking);assert.equal(parked.length,originalWorld.parking.length);
 assert.deepEqual(parked.map(p=>p.id),originalWorld.parking.map(p=>p.id));
 assert.equal(parked.filter(p=>p.id.startsWith('Centro-')&&overlaps(terminal,{x:p.position[0],z:p.position[2],w:5,d:3.6})).length,0);
});
test('every stop fixture is reachable from its actual stop and the corrected bus path clears buildings',()=>{
 const route=newDeliveryRoutes.bus;
 for(const record of newDeliveryWorld.compositions.filter(r=>r.stopId)){
  const stop=route.stops.find(s=>s.id===record.stopId);assert.ok(stop,record.id);
  assert.ok(Math.hypot(record.position[0]-stop.position.x,record.position[2]-stop.position.z)<=12,record.id);
 }
 // Sample the actual road centerline with bus half-width and pedestrian margin.
 for(let i=0;i<route.points.length;i++){
  const a=route.points[i],b=route.points[(i+1)%route.points.length],length=Math.hypot(b.x-a.x,b.z-a.z);
  for(let sample=0;sample<=Math.ceil(length);sample++){
   const t=sample/Math.ceil(length),point={x:a.x+(b.x-a.x)*t,z:a.z+(b.z-a.z)*t,w:0,d:0};
   assert.equal(footprints.some(shape=>overlaps(point,shape,1.85)),false,`Road leg ${i}, sample ${sample}`);
  }
 }
 assert.equal(newDeliveryColliders.some(c=>c.w===52&&c.d>37),false,'Canopy must not become a fully blocked footprint');
});
test('anatomy stays inside the hospital and its approach avoids the display pedestal',()=>{
 const display=newDeliveryWorld.compositions.find(r=>r.role==='educational-exhibit'),hospital=buildings.find(b=>b.id==='hospital');
 assert.ok(Math.abs(display.position[0]-hospital.center[0])<hospital.width/2-1);
 assert.ok(Math.abs(display.position[2]-hospital.center[2])<hospital.depth/2-1);
 const zone=newDeliveryWorld.zones.find(z=>z.id===display.id),pedestal=newDeliveryColliders.find(c=>c.id===display.id);
 assert.ok(!overlaps({x:zone.approach[0],z:zone.approach[2],w:.8,d:.8},pedestal));
});
