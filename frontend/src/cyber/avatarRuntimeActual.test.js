import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import {finiteDeformedVertices,loadTexturelessGLB,localTransformSnapshot} from '../../../scripts/actual_asset_inspection.mjs';

const root=new URL('../../',import.meta.url);
const readJson=url=>JSON.parse(readFileSync(url,'utf8'));
const digest=url=>createHash('sha256').update(readFileSync(url)).digest('hex');
const fileUrl=path=>new URL('public'+path,root);

function anatomy(scene){
 const bones=[],meshes=[];
 scene.traverse(object=>{
  if(object.isBone)bones.push(object.name);
  if(object.isMesh)meshes.push({name:object.name,vertices:object.geometry.attributes.position.count});
 });
 return {bones:bones.sort(),meshes:meshes.sort((a,b)=>a.name.localeCompare(b.name)),deformedVertices:finiteDeformedVertices(scene)};
}

async function compare(sourcePath,targetPath){
 const source=await loadTexturelessGLB(fileUrl(sourcePath));
 const target=await loadTexturelessGLB(fileUrl(targetPath));
 assert.deepEqual(anatomy(target.scene),anatomy(source.scene));
 const stableTransforms=scene=>localTransformSnapshot(scene).map(transform=>
  Object.fromEntries(Object.entries(transform).filter(([key])=>key!=='uuid')));
 assert.deepEqual(stableTransforms(target.scene),stableTransforms(source.scene));
 assert.deepEqual(target.animations.map(clip=>({name:clip.name,duration:clip.duration,tracks:clip.tracks.length})),
  source.animations.map(clip=>({name:clip.name,duration:clip.duration,tracks:clip.tracks.length})));
 return {source:source.scene,target:target.scene};
}

function scrubColors(scene){
 const colors=[];
 scene.traverse(object=>{
  if(!object.isMesh||!/^SCRUB_/.test(object.name)||/^SCRUB_(BRAND|NAME)_/.test(object.name))return;
  for(const material of Array.isArray(object.material)?object.material:[object.material])colors.push({mesh:object.name,material:material.name,color:material.color?.getHexString()});
 });
 return colors;
}

test('optimized Remy runtime files preserve articulation while the active uniform is white and earlier assets remain registered',async()=>{
 const validation=readJson(new URL('../../../reports/AVATAR_RUNTIME_VALIDATION_20261021.json',import.meta.url));
 const optimization=readJson(new URL('../../../reports/AVATAR_RUNTIME_OPTIMIZATION_20261021.json',import.meta.url));
 const reimport=readJson(new URL('../../../reports/costumes/REMY_WHITE_UNIFORM_SURFACE_REIMPORT_20261022.json',import.meta.url));
 const packageReport=readJson(new URL('../../../reports/costumes/REMY_WHITE_UNIFORM_SURFACE_PACKAGE_20261022.json',import.meta.url));
 assert.equal(validation.passed,true);assert.equal(optimization.passed,true);
 assert.equal(reimport.status,'reimport-passed');assert.equal(Object.values(reimport.checks).every(Boolean),true);
 assert.equal(packageReport.whiteScrubs,true);assert.equal(packageReport.imageBytesUnchangedFromApprovedWeb,true);
 const character=readJson(new URL('../config/mixamoAssets.json',import.meta.url)).find(asset=>asset.id==='CHR_Remy_Mixamo_20261005');
 const costume=readJson(new URL('../config/costumeAssets.json',import.meta.url)).find(asset=>asset.id==='COSTUME_Remy_White_Uniform_Surface_20261022');
 assert.equal(costume.baseId,character.id);assert.equal(costume.scrubColorPolicy,'fixed-white');
 assert.equal(packageReport.webSha256,costume.sha256);assert.equal(packageReport.webBytes,costume.bytes);
 assert.equal(packageReport.fullSha256,costume.sourceSha256);assert.equal(packageReport.fullBytes,costume.sourceBytes);
 assert.equal(reimport.sha256,costume.sha256);assert.equal(reimport.bytes,costume.bytes);
 assert.ok(reimport.maxGapMeters<=costume.uniformSurfaceAttachment.toleranceMeters);
 for(const record of [character,costume]){
  assert.equal(digest(fileUrl(record.url)),record.sha256);
  assert.equal(readFileSync(fileUrl(record.url)).length,record.bytes);
  assert.equal(digest(fileUrl(record.sourceAssetUrl??record.sourceUrl)),record.sourceAssetSha256??record.sourceSha256);
  assert.ok(record.bytes<(record.sourceAssetBytes??record.sourceBytes));
 }
 await compare(character.sourceAssetUrl,character.url);
 const current=await compare(costume.sourceUrl,costume.url);
 for(const [kind,scene] of Object.entries(current)){
  const colors=scrubColors(scene);
  assert.ok(colors.length>=3,`${kind} scrub materials`);
  assert.equal(colors.every(material=>material.color==='ffffff'),true,`${kind} scrub fabrics must be white`);
 }
 const historical=costume.history.find(item=>item.id==='COSTUME_Remy_Senac_20261013');
 assert.equal(digest(fileUrl(historical.url)),historical.sha256);
 assert.equal(digest(fileUrl(historical.sourceUrl)),historical.sourceSha256);
 const old=await loadTexturelessGLB(fileUrl(historical.sourceUrl));
 assert.equal(scrubColors(old.scene).some(material=>material.color!=='ffffff'),true,'the archived blue uniform must not be relabeled as white');
});
