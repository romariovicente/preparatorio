import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
const assets=JSON.parse(readFileSync(new URL('./suppliedAssets.json',import.meta.url),'utf8'));
test('every supplied catalog entry matches delivered GLB bytes and triangle primitives',()=>{
  assert.equal(assets.length,150);
  assert.equal(new Set(assets.map(a=>a.sourceSha256)).size,assets.length);
  for(const a of assets){
    const bytes=readFileSync(new URL('../../public'+a.url,import.meta.url));
    assert.equal(bytes.toString('ascii',0,4),'glTF');
    assert.equal(bytes.readUInt32LE(8),bytes.length);
    assert.equal(createHash('sha256').update(bytes).digest('hex'),a.sha256);
    const doc=JSON.parse(bytes.toString('utf8',20,20+bytes.readUInt32LE(12)));
    const counts=doc.meshes.map(m=>m.primitives.reduce((n,p)=>n+(p.mode===undefined||p.mode===4?doc.accessors[p.indices].count/3:0),0));
    const countNode=index=>{const node=doc.nodes[index];return (node.mesh===undefined?0:counts[node.mesh])+(node.children??[]).reduce((sum,child)=>sum+countNode(child),0);};
    const triangles=doc.scenes[doc.scene??0].nodes.reduce((sum,index)=>sum+countNode(index),0);
    assert.equal(triangles,a.triangles,a.id);
    assert.equal(Boolean(a.heavyAsset),bytes.length>30*1024*1024,a.id+' heavy asset flag');
    assert.ok([...doc.images??[],...doc.buffers??[]].every(x=>!x.uri),'embedded resources');
    assert.ok(readFileSync(new URL('../../public'+a.preview,import.meta.url)).length>1000);
    if(a.animations.length){assert.ok(doc.animations.length>=a.animations.length);}
  }
});
test('original character rigs and supplied license restrictions remain explicit',()=>{
  const characters=assets.filter(a=>a.category==='Personagens');assert.equal(characters.length,18);
  assert.ok(characters.some(a=>a.animated));
  assert.equal(assets.find(a=>a.id==='SUP_hospital_03').licenseStatus,'noncommercial');
  assert.ok(assets.filter(a=>a.licenseStatus==='unknown').length>=2);
});
