import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {Box3,Group} from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import manifest from '../config/cyberWorldManifest.json' with {type:'json'};
import living from '../config/cityLivingWorld.json' with {type:'json'};
import {createSolidIndex,solidMovement} from './collisions.js';
import {livingWorldDecorationPolicy as policy,prepareLivingWorldDecorations,shouldHideLivingWorldDecoration} from './livingWorldDecorations.js';

// Browser textures are omitted only from this in-memory CPU fixture. The real
// positions, matrices, mesh hierarchy and source bytes remain intact.
async function fixture(){
  const original=readFileSync(new URL('../../public'+manifest.sceneUrl,import.meta.url));
  const view=new DataView(original.buffer,original.byteOffset,original.byteLength),length=view.getUint32(12,true);
  const document=JSON.parse(new TextDecoder().decode(original.subarray(20,20+length)));
  assert.ok((document.buffers??[]).every(buffer=>!buffer.uri));
  delete document.images;delete document.textures;delete document.materials;delete document.samplers;
  for(const mesh of document.meshes??[])for(const primitive of mesh.primitives){
    delete primitive.material;if(primitive.extensions)delete primitive.extensions.KHR_materials_variants;
  }
  if(document.extensions)delete document.extensions.KHR_materials_variants;
  for(const key of ['extensionsUsed','extensionsRequired'])if(document[key])document[key]=document[key].filter(name=>!name.startsWith('KHR_materials_')&&!name.startsWith('EXT_texture_')&&!['KHR_texture_transform','KHR_texture_basisu','MSFT_texture_dds'].includes(name));
  const encoded=new TextEncoder().encode(JSON.stringify(document)),paddedLength=Math.ceil(encoded.length/4)*4,tail=original.subarray(20+length),bytes=new Uint8Array(20+paddedLength+tail.length),header=new DataView(bytes.buffer);
  bytes.set(original.subarray(0,12));header.setUint32(8,bytes.length,true);header.setUint32(12,paddedLength,true);header.setUint32(16,0x4e4f534a,true);
  bytes.fill(32,20,20+paddedLength);bytes.set(encoded,20);bytes.set(tail,20+paddedLength);
  const gltf=await new GLTFLoader().parseAsync(bytes.buffer,'');
  gltf.scene.updateMatrixWorld(true);
  return {source:gltf.scene,original};
}
const sourceName=object=>object.userData?.name??object.userData?.asset_node_name??object.name;
const bounds=object=>new Box3().setFromObject(object,true);
const overlapXZ=(box,center,size)=>box.min.x<center[0]+size[0]/2&&box.max.x>center[0]-size[0]/2&&box.min.z<center[2]+size[1]/2&&box.max.z>center[2]-size[1]/2;

test('the actual city GLB has exactly one decorative tree intruding into the aquarium and no road/rail footprint conflict',async()=>{
  const {source,original}=await fixture();
  assert.equal(createHash('sha256').update(original).digest('hex'),policy.sourceSha256);
  const aquarium=living.habitats.find(h=>h.kind==='aquarium'),intruding=[],protectedHits=[];
  const access=living.district.access,regions=[...living.habitats.map(h=>({id:h.id,position:h.position,size:h.size})),
    {id:living.campus.id,position:living.campus.position,size:[living.campus.size[0],living.campus.size[2]]},
    {id:'access',position:[access.from[0],0,(access.from[2]+access.to[2])/2],size:[access.width,Math.abs(access.to[2]-access.from[2])]}];
  source.traverse(object=>{
    if(!object.isMesh)return;
    const name=sourceName(object),box=bounds(object);
    if(name.startsWith('TREE_')&&overlapXZ(box,aquarium.position,aquarium.size))intruding.push(name);
    if(/^(?:ROAD_|SIDEWALK_|CYCLE_|MARK_|TRAFFIC_|SIGN_|RAIL|TRACK|STATION|BLD_|HEA_|HANGAR_|LAB_)/.test(name))for(const region of regions)if(overlapXZ(box,region.position,region.size))protectedHits.push([name,region.id]);
  });
  assert.deepEqual(intruding.sort(),['TREE_Crown.004','TREE_Trunk.004']);
  assert.deepEqual(policy.hideNames,intruding);
  assert.deepEqual(protectedHits,[],'A raised habitat floor must not conceal a conflicting road or protected building.');
  assert.deepEqual(policy.protectedOrOtherIntrusionsRequiringLayoutReview,[]);
});

test('hiding the two audited decorative meshes on a private clone removes their real collision rays without touching the source',async()=>{
  const {source}=await fixture(),clone=source.clone(true),names=()=>{
    const rows=[];source.traverse(object=>{if(object.isMesh)rows.push([sourceName(object),object.visible]);});return rows;
  },sourceBefore=names();
  const from={x:-20,y:.23,z:-116},to={x:-18,y:.23,z:-116};
  const before=createSolidIndex(clone);
  assert.ok(before.some(row=>sourceName(row.mesh)==='TREE_Trunk.004'));
  assert.deepEqual(solidMovement(before,from,to,.32),from,'The original trunk really blocks the movement ray.');
  assert.equal(prepareLivingWorldDecorations(clone),clone);
  const hidden=[];clone.traverse(object=>{if(object.userData.livingWorldDecorationHidden)hidden.push(sourceName(object));});
  assert.deepEqual(hidden.sort(),policy.hideNames);
  const after=createSolidIndex(clone);
  assert.equal(after.some(row=>policy.hideNames.includes(sourceName(row.mesh))),false,'No hidden trunk or crown remains in the collision index.');
  assert.deepEqual(solidMovement(after,from,to,.32),to);
  assert.deepEqual(names(),sourceBefore,'Cached original meshes remain visible and unchanged.');
});

test('the preparation ignores protected objects, neighboring trees and another environment source',()=>{
  for(const name of ['ROAD_Main','SIGN_University','STATION_Building','BLD_Hospital','TREE_Trunk.003','TREE_Crown.005']){
    const object=new Group();object.name=name;assert.equal(shouldHideLivingWorldDecoration(object),false,name);
  }
  const trunk=new Group();trunk.name='loader_sanitized_name';trunk.userData.name='TREE_Trunk.004';
  assert.equal(shouldHideLivingWorldDecoration(trunk),true,'The exact original GLTF name survives loader sanitization.');
  assert.equal(shouldHideLivingWorldDecoration(trunk,'/assets/another-scene.glb'),false);
  const scene=new Group();scene.add(trunk);prepareLivingWorldDecorations(scene,'/assets/another-scene.glb');assert.equal(trunk.visible,true);
});
