import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import buildings from '../config/buildingDoors.json' with {type:'json'};
import delivery from '../config/newDeliveryWorld.json' with {type:'json'};
import catalog from '../config/newDeliveryAssets.json' with {type:'json'};
import {advanceCityPosition} from './simulation.js';
import {classroomWorld,classroomApproach,classroomEntry,createClassroomRuntime,stepClassroomDoor,
  toggleClassroomDoor,classroomColliders,classroomDoorLeaf,insideClassroom} from './classroomWorld.js';

function walk(from,to,obstacles){
  let position={...from};
  for(let i=0;i<500;i++){
    const direction={x:to.x-position.x,z:to.z-position.z},distance=Math.hypot(direction.x,direction.z);
    if(distance<.01)return position;
    const next=advanceCityPosition(position,direction,Math.min(.02,distance/5),5,obstacles,.4);
    if(Math.hypot(next.x-position.x,next.z-position.z)<1e-8)return position;
    position=next;
  }
  return position;
}
function glbDocument(url){
  const bytes=readFileSync(new URL('../../public'+url,import.meta.url));
  assert.equal(bytes.readUInt32LE(0),0x46546c67);
  return {bytes,doc:JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)).toString())};
}
test('classroom hashes, real skins, textures and interactive node names match the delivered GLBs',()=>{
  for(const asset of [...classroomWorld.assets,classroomWorld.educational]){
    const {bytes,doc}=glbDocument(asset.url);
    assert.equal(bytes.length,asset.bytes);
    assert.equal(createHash('sha256').update(bytes).digest('hex'),asset.sha256);
    assert.equal(doc.meshes.length,asset.meshCount);
    if(asset.skins!==undefined)assert.equal(doc.skins?.length??0,asset.skins);
    if(asset.students){
      assert.equal(doc.nodes.filter(node=>/^RIG_Classroom_Remy_\d{2}$/.test(node.name??'')).length,12);
      assert.ok(doc.images.length>=21);
      assert.ok(doc.skins.every(skin=>skin.joints.length===55));
      assert.equal(doc.animations?.length??0,0);
    }else if(asset.id){
      assert.ok(doc.nodes.some(node=>node.name===classroomWorld.door.leafNode));
      assert.ok(doc.nodes.some(node=>node.name===classroomWorld.door.handleNode));
    }
  }
});
test('lot clears existing buildings, terminal, educational campus, and street corridors',()=>{
  const lot={x:16,z:60,w:14,d:12.02};
  const overlaps=other=>Math.abs(lot.x-other.x)<(lot.w+other.w)/2&&Math.abs(lot.z-other.z)<(lot.d+other.d)/2;
  for(const building of buildings)assert.equal(overlaps({x:building.center[0],z:building.center[2],w:building.width,d:building.depth}),false,building.id);
  for(const item of delivery.compositions){
    const source=catalog.find(asset=>asset.id===item.assetId),yaw=item.rotation?.[1]??0;
    const [w,d]=source.dimensions;
    assert.equal(overlaps({x:item.position[0],z:item.position[2],w:Math.abs(Math.cos(yaw))*w+Math.abs(Math.sin(yaw))*d,d:Math.abs(Math.sin(yaw))*w+Math.abs(Math.cos(yaw))*d}),false,item.id);
  }
  for(const other of [{id:'elevator',x:-17,z:56,w:8,d:8},{id:'training-campus',x:51,z:-12,w:25,d:9},
    {id:'east-collector-with-sidewalk',x:35,z:0,w:21.8,d:230},{id:'south-access-with-sidewalk',x:0,z:80,w:230,d:21.8},
    {id:'east-west-with-sidewalk',x:0,z:35,w:230,d:21.8},{id:'farm',x:0,z:100,w:44,d:28}]){
    assert.equal(overlaps(other),false,other.id);
  }
});
test('closed leaf blocks entry; fully opened leaf and side aisle allow walking to the lesson',()=>{
  const runtime=createClassroomRuntime(),closed=walk(classroomApproach,classroomEntry,classroomColliders(runtime));
  assert.ok(closed.z<classroomEntry.z-1);
  toggleClassroomDoor(runtime);
  for(let i=0;i<30;i++)stepClassroomDoor(runtime,classroomApproach,.05);
  assert.equal(runtime.progress,1);
  let position=classroomApproach;
  for(const [x,y,z] of classroomWorld.aislePath.slice(1)){
    position=walk(position,{x,y,z},classroomColliders(runtime));
    assert.ok(Math.hypot(position.x-x,position.z-z)<.01,`Walk reaches ${x}, ${z}`);
  }
  assert.ok(insideClassroom(position));
  const leaf=classroomDoorLeaf(1);
  assert.ok(leaf.w<.21&&leaf.d>1.62);
});
test('proximity opens, closing waits for an occupied opening, and manual close resets after leaving',()=>{
  const runtime=createClassroomRuntime();
  stepClassroomDoor(runtime,classroomApproach,.1);assert.equal(runtime.open,true);
  for(let i=0;i<14;i++)stepClassroomDoor(runtime,classroomApproach,.1);
  assert.equal(runtime.progress,1);
  const doorway={x:21.53,y:0,z:54.08};
  stepClassroomDoor(runtime,doorway,.1);toggleClassroomDoor(runtime);
  for(let i=0;i<40;i++)stepClassroomDoor(runtime,doorway,.1);
  assert.equal(runtime.open,true);assert.equal(runtime.progress,1);
  stepClassroomDoor(runtime,classroomApproach,.1);assert.equal(runtime.open,false);
  for(let i=0;i<14;i++)stepClassroomDoor(runtime,{x:21.53,y:0,z:45},.1);
  assert.equal(runtime.progress,0);assert.equal(runtime.manualOpen,null);
  stepClassroomDoor(runtime,classroomApproach,.1);assert.equal(runtime.open,true);
});
test('walls, the visible doorway infill, students and desks block traversal without sealing the room',()=>{
  const colliders=classroomColliders({progress:1});
  const before={x:18,y:0,z:63.8},after=walk(before,{x:24,y:0,z:63.8},colliders);
  assert.ok(after.x>21.5&&after.x<22.1);
  const bypass=walk({x:20.15,y:0,z:52.8},{x:20.15,y:0,z:54.8},colliders);
  assert.ok(bypass.z<54);
  assert.equal(colliders.filter(item=>item.id.startsWith('classroom-desk-')).length,12);
  assert.equal(colliders.filter(item=>item.id.startsWith('classroom-seat-')).length,12);
  assert.equal(colliders.some(item=>item.w===14&&item.d===12),false);
});
