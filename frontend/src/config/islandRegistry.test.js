import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { islandRegistry } from './islandRegistry.js';
import { locations, locationIds } from '../world/locations.js';
test('island variants contain only the map, valid embedded textures, and controlled triangle budgets',()=>{
  for(const [key,budget] of [['web',150000],['mobile',45000]]){
    const file=readFileSync(new URL('../../public'+islandRegistry[key].url,import.meta.url));
    assert.equal(file.toString('ascii',0,4),'glTF');assert.equal(file.readUInt32LE(8),file.length);
    const gltf=JSON.parse(file.toString('utf8',20,20+file.readUInt32LE(12)));
    assert.equal(gltf.nodes.length,1);assert.ok(gltf.nodes[0].name.startsWith('MAP_Preparatorio_Island_'));
    const prim=gltf.meshes[0].primitives[0];const triangles=gltf.accessors[prim.indices].count/3;
    assert.equal(triangles,islandRegistry[key].triangles);assert.ok(triangles<budget);
    assert.ok(prim.attributes.NORMAL!=null&&prim.attributes.TEXCOORD_0!=null);
    assert.equal(gltf.images.length,3);assert.ok(gltf.images.every(i=>i.bufferView!=null&&!i.uri));
    assert.ok(file.length<(key==='web'?8_000_000:2_500_000));
  }
});
test('all landmarks have unique IDs and positions inside the island game extent',()=>{
  assert.equal(new Set(locationIds).size,16);
  assert.ok(locations.every(p=>p.position.length===2&&p.position.every(Number.isFinite)&&Math.abs(p.position[0])<=181&&Math.abs(p.position[1])<=201));
});
