import assert from 'node:assert/strict';
import {readFileSync,writeFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {AnimationMixer} from '../frontend/node_modules/three/build/three.module.js';
import {loadTexturelessGLB,finiteDeformedVertices,synchronizeSkinnedBounds,localTransformSnapshot,joint} from './actual_asset_inspection.mjs';
import {createCharacterClone} from '../frontend/src/world/characterModel.js';
import {createSeatedClone} from '../frontend/src/cyber/seating.js';
import {createCarryAnimations} from '../frontend/src/world/carryAnimation.js';
import {applyUniformOutfit} from '../frontend/src/cyber/uniformMaterials.js';

export async function inspectUniform(){
 const target=new URL('../frontend/public/assets/characters/CHR_Remy_Senac_Uniform_20261013.glb',import.meta.url);
 const report=JSON.parse(readFileSync(new URL('../reports/costumes/remy_senac_uniform_20261013.json',import.meta.url)));
 const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
 const raw=readFileSync(target),length=raw.readUInt32LE(12),doc=JSON.parse(raw.subarray(20,20+length));
 assert.equal(hash(raw),report.sha256);
 assert.equal(hash(readFileSync(new URL('../frontend/public/assets/characters/CHR_Remy_Mixamo_20261005.glb',import.meta.url))),report.sourceSha256);
 assert.equal(hash(readFileSync(new URL('../frontend/public/assets/characters/CHR_Remy_Senac_Uniform_20261009.glb',import.meta.url))),report.previousDerivativeSha256);
 const binStart=20+length+8;
 const identities=doc.images.filter(image=>['senac-logo','nursing-crest'].includes(image.name)).map(image=>{
  const view=doc.bufferViews[image.bufferView],bytes=raw.subarray(binStart+(view.byteOffset??0),binStart+(view.byteOffset??0)+view.byteLength);
  const ref=report.original2dReferences.find(reference=>reference.name===image.name+'.png');
  assert.equal(hash(bytes),ref.sha256);return {name:image.name,sha256:ref.sha256,bytes:bytes.length,byteIdentical:true};
 });
 assert.equal(identities.length,2);
 const gltf=await loadTexturelessGLB(target),sourceSnapshot=localTransformSnapshot(gltf.scene),sourceBones=new Set();
 gltf.scene.traverse(o=>{if(o.isBone)sourceBones.add(o);});
 const garments=[];gltf.scene.traverse(o=>{if(o.isMesh&&/^(COAT_|SCRUB_)/.test(o.name))garments.push(o);});
 assert.equal(garments.length,20);assert.equal(sourceBones.size,55);
 const total=finiteDeformedVertices(gltf.scene),cases=[];
 const sample=(group,mode,time=null)=>{
  const bounds=synchronizeSkinnedBounds(group),vertices=finiteDeformedVertices(group);
  assert.equal(vertices,total);assert.ok([...bounds.min.toArray(),...bounds.max.toArray()].every(Number.isFinite));
  group.traverse(o=>{if(o.isSkinnedMesh)assert.ok(o.skeleton.bones.every(bone=>!sourceBones.has(bone)));});
  cases.push({mode,time,vertices,min:bounds.min.toArray(),max:bounds.max.toArray()});
 };
 for(const clip of gltf.animations){
  const {group}=createCharacterClone(gltf.scene,1.7),mixer=new AnimationMixer(group);
  applyUniformOutfit(group,{coat:true,scrubs:true,color:'#247fba'},report.replacedMeshes);
  const action=mixer.clipAction(clip);action.play();
  for(const fraction of [0,.25,.5,.75]){mixer.setTime(clip.duration*fraction);sample(group,clip.name,clip.duration*fraction);}
 }
 const carry=createCarryAnimations(gltf.animations);
 assert.ok(carry.clips.find(c=>c.name===carry.overlayName).tracks.some(t=>/LeftArm\.quaternion$/.test(t.name)));
 for(const name of ['Idle','Walk']){
  const {group}=createCharacterClone(gltf.scene,1.7),mixer=new AnimationMixer(group);
  mixer.clipAction(carry.clips.find(c=>c.name===carry.holdingNames[name])).play();
  const overlay=mixer.clipAction(carry.clips.find(c=>c.name===carry.overlayName));overlay.play();overlay.time=carry.overlayTime;overlay.paused=true;
  mixer.update(.4);sample(group,'carrying '+name,.4);
 }
 for(const riding of [false,true]){
  const pose=createSeatedClone(gltf.scene,1.7,riding);assert.equal(pose.posed,true);
  pose.group.position.y=(riding?.94:.48)+pose.offset;sample(pose.group,riding?'riding':'seated');
  const hips=joint(pose.group,'Hips');assert.ok(Math.abs(hips.y-(riding?1:.54))<.0001);
  assert.ok(cases.at(-1).min[1]>(riding?.3:-.025));
 }
 assert.deepEqual(localTransformSnapshot(gltf.scene),sourceSnapshot);
 return {date:'2026-10-13',url:report.url,sha256:report.sha256,bytes:raw.length,bones:55,garmentMeshes:garments.length,
  vertexCount:total,clips:gltf.animations.map(c=>c.name),identities,sourcePreserved:true,previousDerivativePreserved:true,
  clonedSourceUnchanged:true,cpuValidated:true,cases,
  limits:['Finite-vertex and FK checks validate rig integrity; they do not prove zero clothing collisions.',
   'Seated/riding coat is a weighted prototype without cloth simulation. Visual pose previews are part of the review.']};
}
if(process.argv[1] && new URL('file:///'+process.argv[1].replaceAll('\\','/')).href===import.meta.url){
 const record=await inspectUniform();
 writeFileSync(new URL('../reports/costumes/remy_uniform_cpu_20261013.json',import.meta.url),JSON.stringify(record,null,2)+'\n');
 console.log(JSON.stringify({status:'validated',bytes:record.bytes,sha256:record.sha256,vertices:record.vertexCount,poses:record.cases.length}));
}
