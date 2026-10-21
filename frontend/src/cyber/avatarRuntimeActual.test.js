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
}

test('optimized Remy runtime files preserve the exact articulated character and animations while selecting smaller textures',async()=>{
 const validation=readJson(new URL('../../../reports/AVATAR_RUNTIME_VALIDATION_20261021.json',import.meta.url));
 const optimization=readJson(new URL('../../../reports/AVATAR_RUNTIME_OPTIMIZATION_20261021.json',import.meta.url));
 assert.equal(validation.passed,true);assert.equal(optimization.passed,true);
 const character=readJson(new URL('../config/mixamoAssets.json',import.meta.url)).find(asset=>asset.id==='CHR_Remy_Mixamo_20261005');
 const costume=readJson(new URL('../config/costumeAssets.json',import.meta.url)).find(asset=>asset.baseId===character.id);
 for(const record of [character,costume]){
  assert.equal(digest(fileUrl(record.url)),record.sha256);
  assert.equal(readFileSync(fileUrl(record.url)).length,record.bytes);
  assert.equal(digest(fileUrl(record.sourceAssetUrl??record.sourceUrl)),record.sourceAssetSha256??record.sourceSha256);
  assert.ok(record.bytes<(record.sourceAssetBytes??record.sourceBytes));
 }
 await compare(character.sourceAssetUrl,character.url);
 await compare(costume.sourceUrl,costume.url);
});
