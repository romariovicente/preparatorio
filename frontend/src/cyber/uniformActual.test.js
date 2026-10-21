import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {inspectUniform} from '../../../scripts/validate_remy_uniform_20261013.mjs';

test('actual fitted Remy uniform preserves both source files, original logos and finite independent skins in all supplied and seated/carry poses',async()=>{
 const record=await inspectUniform();
 assert.equal(record.cpuValidated,true);assert.equal(record.garmentMeshes,20);
 assert.equal(record.cases.length,20);assert.equal(record.identities.every(image=>image.byteIdentical),true);
 assert.ok(record.cases.some(pose=>pose.mode==='carrying Walk'));
 assert.ok(record.cases.some(pose=>pose.mode==='seated'));
 const catalog=JSON.parse(readFileSync(new URL('../config/costumeAssets.json',import.meta.url)));
 const costume=catalog.find(item=>item.baseId==='CHR_Remy_Mixamo_20261005');
 assert.ok(costume?.reimportValidated&&costume.cpuValidated);
 assert.equal(costume.sourceUrl,record.url);assert.equal(costume.sourceSha256,record.sha256);
 assert.equal(costume.sourceBytes,record.bytes);
});
