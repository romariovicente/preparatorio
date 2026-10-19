import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { assetRegistry, cityKitUrl } from './assetRegistry.js';

function readGlb(url) {
  const bytes = readFileSync(new URL('../../public' + url, import.meta.url));
  assert.equal(bytes.toString('ascii', 0, 4), 'glTF');
  assert.equal(bytes.readUInt32LE(4), 2);
  assert.equal(bytes.readUInt32LE(8), bytes.length);
  const length = bytes.readUInt32LE(12);
  return JSON.parse(bytes.toString('utf8', 20, 20 + length));
}

test('all 32 registry entries reference real, centered GLBs with embedded PBR textures', () => {
  assert.equal(Object.keys(assetRegistry).length, 32);
  for (const [name, asset] of Object.entries(assetRegistry)) {
    const glb = readGlb(asset.url);
    assert.equal(glb.nodes.length, 1);
    assert.equal(glb.nodes[0].name, name);
    assert.deepEqual(glb.nodes[0].translation ?? [0, 0, 0], [0, 0, 0]);
    assert.ok(glb.meshes[0].primitives.every(p => p.attributes.NORMAL != null && p.attributes.TEXCOORD_0 != null));
    for (const m of glb.materials) {
      assert.ok(m.pbrMetallicRoughness.metallicRoughnessTexture);
      assert.equal(m.occlusionTexture.index, m.pbrMetallicRoughness.metallicRoughnessTexture.index);
    }
    assert.ok(glb.images.every(i => i.bufferView != null && !i.uri));
  }
});

test('catalog contains exactly the registered modules and no presentation objects', () => {
  const glb = readGlb(cityKitUrl);
  assert.deepEqual(glb.nodes.map(n => n.name).sort(), Object.keys(assetRegistry).sort());
  assert.equal(glb.meshes.length, 32);
  assert.equal(glb.materials.length, 10);
  assert.equal(glb.cameras, undefined);
});
