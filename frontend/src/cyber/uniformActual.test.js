import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {inspectUniform} from '../../../scripts/validate_remy_uniform_20261013.mjs';

test('historical fitted Remy uniform remains independently reproducible after the white surface uniform becomes active',async()=>{
 const record=await inspectUniform();
 assert.equal(record.cpuValidated,true);assert.equal(record.garmentMeshes,20);
 assert.equal(record.cases.length,20);assert.equal(record.identities.every(image=>image.byteIdentical),true);
 assert.ok(record.cases.some(pose=>pose.mode==='carrying Walk'));
 assert.ok(record.cases.some(pose=>pose.mode==='seated'));
 const catalog=JSON.parse(readFileSync(new URL('../config/costumeAssets.json',import.meta.url)));
 const costume=catalog.find(item=>item.id==='COSTUME_Remy_White_Uniform_Surface_20261022');
 assert.ok(costume?.reimportValidated&&costume.cpuValidated);
 const historical=costume.history?.find(item=>item.id==='COSTUME_Remy_Senac_20261013');
 assert.ok(historical,'the previous approved uniform must remain registered as history');
 assert.equal(historical.sourceUrl,record.url);assert.equal(historical.sourceSha256,record.sha256);
 assert.equal(historical.sourceBytes,record.bytes);
 assert.equal(historical.url,'/assets/characters/runtime/CHR_Remy_Senac_Uniform_Web_20261021.glb');
 assert.equal(historical.sha256,'4dd63fe6395a88ad502d87c6289d3c98d20eeccb76ce2de441a88d0d92997475');
 assert.equal(historical.bytes,13841868);
 assert.equal(costume.scrubColorPolicy,'fixed-white');
});
