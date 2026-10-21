import test from 'node:test';
import assert from 'node:assert/strict';
import {existsSync,readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';

const assets=JSON.parse(readFileSync(new URL('./suppliedAssets.json',import.meta.url),'utf8'));
const publicUrl=path=>new URL('../../public'+path,import.meta.url);
const weaponSignal=/(?:^|[_-])(smg|guns?|rifle|sniper|pistol|weapon|mag|trigger)(?:[_-]|$)/i;

test('standalone firearms are absent from the game catalog and public build inputs',()=>{
  assert.ok(assets.every(asset=>!/^Armas[\\/]/i.test(asset.sourceRelative??'')));
  assert.ok(assets.every(asset=>!/(?:sniper|niper|rifle|pistol|weapon)/i.test(`${asset.id} ${asset.name}`)));
  assert.equal(existsSync(publicUrl('/assets/supplied/SUP_es_niper.glb')),false);
  assert.equal(existsSync(publicUrl('/assets/supplied/SUP_es_niper.jpg')),false);
});

test('the selectable cyberpunk character uses the validated civilian Blender derivative',()=>{
  const asset=assets.find(item=>item.id==='SUP_character_cyberpunk_free_3d_by_oscar_cre');
  assert.match(asset.url,/Civilian_v1\.glb$/);assert.match(asset.preview,/Civilian_v1\.jpg$/);
  assert.equal(existsSync(publicUrl('/assets/supplied/SUP_character_cyberpunk_free_3d_by_oscar_cre_BodyRig.glb')),false);
  const bytes=readFileSync(publicUrl(asset.url));
  assert.equal(createHash('sha256').update(bytes).digest('hex'),asset.sha256);
  const length=bytes.readUInt32LE(12),doc=JSON.parse(bytes.toString('utf8',20,20+length));
  const visibleNames=[...doc.meshes??[],...doc.materials??[]].map(item=>item.name??'');
  assert.ok(visibleNames.every(name=>!weaponSignal.test(name)),visibleNames.filter(name=>weaponSignal.test(name)).join(', '));
  assert.equal(doc.meshes.length,35);assert.equal(doc.skins.length,1);
  assert.deepEqual(doc.animations.map(animation=>animation.name),['motion']);
});
