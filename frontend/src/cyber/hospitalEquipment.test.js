import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {Box3,Vector3} from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import plan from '../config/hospitalEquipment.json' with {type:'json'};
import hospital from '../config/hospitalReception.json' with {type:'json'};

test('the ambient monitor rests on the real reception counter at its original human scale',async()=>{
  const bytes=readFileSync(new URL(`../../public${hospital.asset}`,import.meta.url));
  const gltf=await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');
  gltf.scene.updateMatrixWorld(true);
  const top=gltf.scene.getObjectByName('HSP15_RECEPTION_TOP');assert.ok(top);
  const bounds=new Box3().setFromObject(top),position=new Vector3().fromArray(plan.localPosition);
  assert.ok(Math.abs(position.y-bounds.max.y)<.005,'base touches the countertop within five millimetres');
  assert.ok(position.x-plan.dimensions[0]/2>bounds.min.x&&position.x+plan.dimensions[0]/2<bounds.max.x);
  assert.ok(position.z-plan.dimensions[2]/2>bounds.min.z&&position.z+plan.dimensions[2]/2<bounds.max.z);
  assert.ok(plan.height>.14&&plan.height<.15,'14 cm source was not enlarged into scenery');
  for(let axis=0;axis<3;axis++)assert.ok(Math.abs(plan.worldPosition[axis]-hospital.position[axis]-plan.localPosition[axis])<1e-6);
  assert.equal(plan.liveMeasurement,false);
  assert.match(plan.notice,/não medem o ambiente/);
});

test('the exported monitor retains its authored geometry, textures and source attribution',()=>{
  const bytes=readFileSync(new URL(`../../public${plan.asset}`,import.meta.url));
  assert.equal(bytes.length,plan.bytes);assert.equal(createHash('sha256').update(bytes).digest('hex'),plan.sha256);
  const length=bytes.readUInt32LE(12),doc=JSON.parse(bytes.subarray(20,20+length).toString());
  assert.equal(doc.scenes.length,1);assert.equal(doc.meshes.length,3);assert.equal(doc.images.length,2);
  let triangles=0;
  for(const mesh of doc.meshes)for(const primitive of mesh.primitives){
    assert.notEqual(primitive.attributes.NORMAL,undefined);assert.notEqual(primitive.attributes.TEXCOORD_0,undefined);
    triangles+=doc.accessors[primitive.indices].count/3;
  }
  assert.equal(triangles,13002);assert.equal(doc.animations,undefined);
  assert.ok(doc.nodes.some(node=>node.extras?.attribution_author===plan.credits.author));
  assert.match(plan.credits.license,/CC-BY-4.0/);
});
