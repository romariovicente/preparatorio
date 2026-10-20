import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';

test('the actual optimized conceptual engine preserves its source and stays inside its lab plinth',()=>{
  const report=JSON.parse(readFileSync(new URL('../../../reports/WARP_ENGINE_BLENDER_20261019.json',import.meta.url),'utf8'));
  const source=readFileSync(report.source);
  assert.equal(createHash('sha256').update(source).digest('hex'),report.sourceSha256);
  const data=readFileSync(new URL('../../public'+report.url,import.meta.url));
  assert.equal(createHash('sha256').update(data).digest('hex'),report.sha256);
  assert.ok(data.length<10_000_000);
  const doc=JSON.parse(data.subarray(20,20+data.readUInt32LE(12)).toString());
  assert.equal(doc.scenes.length,1);assert.equal(doc.meshes.length,1);assert.equal(doc.skins?.length??0,0);
  const primitive=doc.meshes[0].primitives[0],positions=doc.accessors[primitive.attributes.POSITION];
  assert.equal(doc.accessors[primitive.indices].count/3,170000);
  assert.ok([...positions.min,...positions.max].every(Number.isFinite));
  assert.equal(doc.images.length,3);
  assert.ok(doc.images.every(image=>Number.isInteger(image.bufferView)&&image.mimeType==='image/jpeg'));
  assert.ok(report.dimensionsBlender[0]<4&&report.dimensionsBlender[1]<4&&report.dimensionsBlender[2]<2.21);
  assert.ok(Math.abs(report.groundMin)<.001);
});
