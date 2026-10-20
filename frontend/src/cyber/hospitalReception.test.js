import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {BoxGeometry,Group,Mesh,MeshStandardMaterial,Raycaster} from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import buildings from '../config/buildingDoors.json' with {type:'json'};
import delivery from '../config/newDeliveryWorld.json' with {type:'json'};
import {createDoorController,inspectHospitalModel} from '../hospital/hospitalModel.js';
import {collectGroundSurfaces,sampleGroundHeight} from './groundSupport.js';
import {advanceCityPosition,TRANSIT_ROUTES} from './simulation.js';
import {buildingColliders} from './doorGeometry.js';
import {createHospitalRuntime,hospitalColliders,hospitalReception,hospitalGroundSurfaces,markHospitalFloors,markHospitalPlatformFloors,readHospitalDoorColliders,roomDoorwayOccupied} from './hospitalReception.js';

async function fixture(){
  const bytes=readFileSync(new URL('../../public/assets/environments/ENV_Hospital_Reception_Module_20261015.glb',import.meta.url));
  const gltf=await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');
  const source=gltf.scene,scene=source.clone(true),world=new Group();world.position.fromArray(hospitalReception.position);world.add(scene);
  markHospitalFloors(scene);
  const info=inspectHospitalModel(scene,gltf.animations),doors=createDoorController(scene,info.doorClips),rooms=createDoorController(scene,info.roomClips);
  world.updateMatrixWorld(true);
  return {source,scene,world,doors,rooms};
}
const overlaps=(a,b)=>Math.abs(a.x-b.x)<(a.w+b.w)/2&&Math.abs(a.z-b.z)<(a.d+b.d)/2;
test('the Blender reception replaces the same hospital at metre scale with an actual walkable floor',async()=>{
  const {source,scene,doors,rooms}=await fixture();
  try{
    const definition=buildings.find(b=>b.id==='hospital');
    assert.deepEqual(definition.center,hospitalReception.position);assert.equal(definition.depth,24);assert.equal(definition.opening,2.4);
    assert.deepEqual(scene.scale.toArray(),[1,1,1]);
    const floors=collectGroundSurfaces(scene);assert.ok(floors.length>=2);
    assert.ok(Math.abs(sampleGroundHeight(new Raycaster(),floors,{x:48,y:hospitalReception.position[1],z:-30})-(hospitalReception.position[1]+.012))<.00001);
    assert.equal(collectGroundSurfaces(source).length,0,'cached source was not tagged or mutated');
    assert.equal(hospitalReception.staticColliders.length,44);
  }finally{doors.dispose();rooms.dispose();}
});
test('hospital support prefers its own floor inside the lot while outside terrain remains eligible',async()=>{
  const {scene,doors,rooms}=await fixture();
  const legacy=new Mesh(new BoxGeometry(36,.1,24),new MeshStandardMaterial());legacy.position.set(48,.55,-38);legacy.userData.walkable=true;legacy.updateMatrixWorld(true);
  try{
    const floors=[legacy,...collectGroundSurfaces(scene)],position={x:48,y:hospitalReception.position[1],z:-30};
    assert.equal(hospitalGroundSurfaces(floors,{x:48,y:0,z:-20}),floors);
    const chosen=hospitalGroundSurfaces(floors,position);assert.ok(chosen.every(mesh=>mesh.userData.hospitalFloor));
    assert.ok(Math.abs(sampleGroundHeight(new Raycaster(),chosen,position)-(hospitalReception.position[1]+.012))<.00001);
  }finally{doors.dispose();rooms.dispose();legacy.geometry.dispose();legacy.material.dispose();}
});
test('all automatic transit centerlines retain a conservative ten-metre clearance around the hospital and the tutor stays outside',()=>{
  for(const [id,route] of Object.entries(TRANSIT_ROUTES))for(let leg=0;leg<route.points.length;leg++){
    const from=route.points[leg],to=route.points[(leg+1)%route.points.length],steps=Math.ceil(Math.hypot(to.x-from.x,to.z-from.z)*2);
    for(let index=0;index<=steps;index++){
      const x=from.x+(to.x-from.x)*index/steps,z=from.z+(to.z-from.z)*index/steps;
      assert.equal(Math.abs(x-48)<18+10&&Math.abs(z+38)<12+10,false,`${id} leg ${leg}`);
    }
  }
  assert.ok(Math.abs(-20+38)>12+.4,'hospital tutor at [43,0,-20] stays beyond the facade');
});
test('the actual entrance platform supports continuous ramp walking from street to the raised hospital floor',async()=>{
  const bytes=readFileSync(new URL('../../public/assets/environments/ENV_Hospital_Entrance_Platform_20261019.glb',import.meta.url));
  const gltf=await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');
  const snapshot=()=>{const rows=[];gltf.scene.traverse(object=>{if(object.isMesh)rows.push([object.uuid,object.receiveShadow,JSON.stringify(object.userData)]);});return rows;};
  const original=snapshot();
  const scene=gltf.scene.clone(true),world=new Group();world.position.fromArray(hospitalReception.position);world.add(scene);markHospitalPlatformFloors(scene);world.updateMatrixWorld(true);
  const floors=collectGroundSurfaces(scene),ray=new Raycaster();assert.ok(floors.length>=2);
  let previous=0;
  for(let index=0;index<=40;index++){
    const localZ=16.05-index*3.9/40;
    const height=sampleGroundHeight(ray,floors,{x:48,y:.26,z:-38+localZ},{radius:0});
    assert.ok(height>=previous-.00001,`ramp goes down toward entrance at ${localZ}`);
    assert.ok(height-previous<.035,`ramp has an abrupt step at ${localZ}`);
    previous=height;
  }
  assert.ok(previous>.26&&previous<.28);
  assert.deepEqual(snapshot(),original,'shared platform source and its Blender-authored walkable flags stay unchanged');
});
test('real exported public and internal doors change collision bounds, and the clear entrance-to-triage route remains walkable',async()=>{
  const {scene,doors,rooms}=await fixture();
  const runtime=createHospitalRuntime();
  try{
    doors.update(false,2);rooms.update(false,2);runtime.dynamicColliders=readHospitalDoorColliders(scene);
    const outside={x:48,y:0,z:-25.35};
    assert.equal(advanceCityPosition(outside,{x:0,z:-1},.05,5,hospitalColliders(runtime)).z,outside.z);
    doors.update(true,2);rooms.update(true,2);runtime.dynamicColliders=readHospitalDoorColliders(scene);
    const room=runtime.dynamicColliders.find(c=>c.id==='HSP15_DOOR_ROOM_01_HINGE');
    assert.ok(Math.abs(room.x-(48-2.6))<.01);assert.ok(room.w>1.5&&room.d<.1);
    const obstacles=[...buildingColliders(buildings.find(b=>b.id==='hospital'),{open:true}),...hospitalColliders(runtime)];
    for(const path of [[[48,-24.5],[48,-29.5],[41,-29.5],[41,-30.2]],[[48,-24.5],[48,-38],[45,-38]],[[48,-24.5],[48,-38],[51,-38]]]){
      for(let segment=1;segment<path.length;segment++){
        const [x,z]=path[segment-1],[tx,tz]=path[segment],length=Math.hypot(tx-x,tz-z),count=Math.ceil(length/.1);
        for(let index=0;index<count;index++){
          const from={x:x+(tx-x)*index/count,y:0,z:z+(tz-z)*index/count},to=advanceCityPosition(from,{x:tx-x,z:tz-z},length/count/5,5,obstacles);
          assert.ok(Math.hypot(to.x-from.x,to.z-from.z)>.001,`walk blocked at ${from.x}, ${from.z}`);
        }
      }
    }
    doors.update(false,2);rooms.update(false,2);runtime.dynamicColliders=readHospitalDoorColliders(scene);
    assert.equal(advanceCityPosition(outside,{x:0,z:-1},.05,5,hospitalColliders(runtime)).z,outside.z);
  }finally{doors.dispose();rooms.dispose();}
});
test('room doors refuse closing on their swept space and the preserved anatomy exhibit clears the Blender furniture',()=>{
  const room=hospitalReception.roomDoors[0];
  assert.equal(roomDoorwayOccupied(room,[{x:46.2,y:0,z:-38}]),true);
  assert.equal(roomDoorwayOccupied(room,[{x:48,y:0,z:-38}]),false);
  assert.equal(roomDoorwayOccupied(room,[{x:46.2,y:-6,z:-38}]),false);
  const exhibit=delivery.colliders.find(record=>record.id==='delivery-anatomy');
  const exhibitModel=delivery.compositions.find(record=>record.id==='delivery-anatomy');
  assert.equal(exhibitModel.pedestal.baseY,hospitalReception.position[1]);
  assert.ok(exhibitModel.position[1]>hospitalReception.position[1]+exhibitModel.pedestal.height);
  const fixed=hospitalColliders(createHospitalRuntime()).filter(record=>!record.id.includes('DOOR_'));
  assert.deepEqual(fixed.filter(record=>overlaps(exhibit,record)).map(record=>record.id),[]);
});
test('new lounge chairs block their actual curved arms while hospital passages stay clear',()=>{
  const chairs=hospitalColliders(createHospitalRuntime()).filter(box=>box.id.startsWith('HSP15_CHAIR_COLLIDER_'));
  assert.equal(chairs.length,14);assert.equal(new Set(chairs.map(box=>box.id)).size,14);
  for(const chair of chairs){
    assert.ok(chair.w>.87&&chair.w<1.05);
    assert.ok(chair.d>.89&&chair.d<1.05);
    assert.ok(chair.minY>.26&&chair.maxY<1.3);
    assert.ok(Math.abs(chair.x-48)>4,'the central corridor remains clear');
  }
  const chair=chairs.find(box=>box.id==='HSP15_CHAIR_COLLIDER_0_0');
  const from={x:chair.x+.6,y:chair.minY,z:chair.z};
  const next=advanceCityPosition(from,{x:-1,z:0},.1,5,chairs);
  assert.equal(next.x,from.x,'the wider arm is solid');
});
