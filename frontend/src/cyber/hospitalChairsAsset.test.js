import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import chairs from '../config/hospitalChairs.json' with {type:'json'};
import reception from '../config/hospitalReception.json' with {type:'json'};
import {hospitalOriginalChairRootNames,hideHospitalChairRoots,restoreHospitalChairRoots} from './hospitalChairs.js';

test('the real hospital exposes exactly ten waiting and four room chair roots without changing doors or source objects',async()=>{
  const bytes=readFileSync(new URL('../../public/assets/environments/ENV_Hospital_Reception_Module_20261015.glb',import.meta.url));
  const gltf=await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');
  const copy=gltf.scene.clone(true),roots=[];copy.traverse(object=>{if(hospitalOriginalChairRootNames.includes(object.name))roots.push(object);});
  assert.equal(roots.length,14);assert.equal(roots.filter(root=>/^HSP15_CHAIR_[01]_/.test(root.name)).length,10);
  assert.equal(roots.filter(root=>root.name.startsWith('HSP15_CHAIR_ROOM_')).length,4);
  assert.equal(chairs.placements.length,14);assert.equal(new Set(chairs.placements.map(placement=>placement.originalRoot)).size,14);
  for(const placement of chairs.placements){
    const original=gltf.scene.getObjectByName(placement.originalRoot);assert.ok(original,placement.originalRoot);
    assert.ok(Math.abs(original.position.x-placement.position[0])<1e-5);assert.ok(Math.abs(original.position.z-placement.position[2])<1e-5);
    assert.equal(placement.position[1],reception.floorY);assert.ok(placement.rotation.every(Number.isFinite));
  }
  const protectedObjects=[];copy.traverse(object=>{if(!/^HSP15_CHAIR_(?:[01]_[0-4]|ROOM_0[1-4])(?:_|$)/.test(object.name))protectedObjects.push([object,object.visible]);});
  const animations=gltf.animations.map(clip=>[clip.name,clip.duration]);
  assert.equal(hideHospitalChairRoots(copy,chairs.placements.map(placement=>placement.originalRoot)).length,14);
  for(const root of roots)assert.equal(root.visible,false);
  for(const [object,visible] of protectedObjects)assert.equal(object.visible,visible,object.name);
  for(const name of hospitalOriginalChairRootNames)assert.equal(gltf.scene.getObjectByName(name).visible,true,'cached source retained');
  assert.deepEqual(gltf.animations.map(clip=>[clip.name,clip.duration]),animations);
  assert.ok(animations.some(([name])=>name==='Door_Open'));assert.ok(animations.some(([name])=>name==='Room_Open_01'));
  restoreHospitalChairRoots(copy);for(const root of roots)assert.equal(root.visible,true);
});

test('the prepared replacement file matches the Blender contract and remains an unapproved clinical illustration',()=>{
  const bytes=readFileSync(new URL(`../../public${chairs.asset}`,import.meta.url));
  assert.equal(bytes.length,chairs.bytes);assert.equal(createHash('sha256').update(bytes).digest('hex'),chairs.sha256);
  assert.equal(bytes.subarray(0,4).toString(),'glTF');const jsonLength=bytes.readUInt32LE(12),gltf=JSON.parse(bytes.subarray(20,20+jsonLength).toString());
  const triangles=gltf.meshes.reduce((sum,mesh)=>sum+mesh.primitives.reduce((subtotal,primitive)=>subtotal+(primitive.indices!==undefined?gltf.accessors[primitive.indices].count:gltf.accessors[primitive.attributes.POSITION].count)/3,0),0);
  assert.equal(triangles,chairs.triangles);assert.ok(gltf.meshes.length>0);
  assert.ok(chairs.dimensions[0]>.8&&chairs.dimensions[0]<1);assert.ok(chairs.dimensions[1]>.9&&chairs.dimensions[1]<1.1);
  assert.equal(chairs.certifiedClinicalOrArchitectural,false);
});
