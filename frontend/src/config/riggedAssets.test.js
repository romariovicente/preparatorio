import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
const originals=JSON.parse(readFileSync(new URL('./suppliedAssets.json',import.meta.url),'utf8'));
const rigs=JSON.parse(readFileSync(new URL('./riggedAssets.json',import.meta.url),'utf8'));
test('all 18 supplied characters retain or receive real weighted armatures',()=>{
 const characters=originals.filter(a=>a.category==='Personagens');assert.equal(characters.length,18);
 for(const original of characters){
  const rig=rigs.find(r=>r.id===original.id),asset=rig??original;
  const bytes=readFileSync(new URL('../../public'+asset.url,import.meta.url));
  assert.equal(createHash('sha256').update(bytes).digest('hex'),asset.sha256);
  const doc=JSON.parse(bytes.toString('utf8',20,20+bytes.readUInt32LE(12)));
  assert.ok(doc.skins?.length,original.id+' missing skin');
  for(const node of doc.nodes.filter(n=>n.skin!==undefined)){
   assert.ok(doc.skins[node.skin].joints.length>=10,original.id+' bone count');
   for(const primitive of doc.meshes[node.mesh].primitives){
    assert.ok(primitive.attributes.JOINTS_0!==undefined&&primitive.attributes.WEIGHTS_0!==undefined,original.id+' missing weights');
    assert.equal(doc.accessors[primitive.attributes.WEIGHTS_0].count,doc.accessors[primitive.attributes.POSITION].count);
   }
  }
  if(rig){
   assert.ok(rig.reimportValidated&&rig.actionsReimportValidated);
   assert.ok(rig.clips.every(name=>doc.animations.some(animation=>animation.name===name)),original.id+' declared clips');
   if(rig.quality==='prototype')assert.ok(rig.clips.includes('Dance')&&rig.clips.includes('Interact'));
   assert.equal(rig.weightCoverage,1);assert.equal(rig.maxInfluences,4);
  }
 }
});
test('limited poses cannot enter the playable walking selection',()=>{
 assert.equal(rigs.length,17);assert.equal(rigs.filter(r=>r.playable).length,12);
 assert.equal(rigs.filter(r=>r.quality==='prototype').length,14);
 assert.equal(rigs.filter(r=>r.quality==='retargeted').length,3);
 assert.equal(rigs.filter(r=>r.needsRepose).length,5);
 assert.ok(rigs.filter(r=>r.needsRepose).every(r=>!r.playable&&!r.clips.includes('Walk')));
});
