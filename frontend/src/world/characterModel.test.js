import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {Box3,BoxGeometry,Group,Mesh,MeshBasicMaterial,Vector3} from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {createCharacterClone,isCharacterHelper} from './characterModel.js';

test('localized auxiliary spheres cannot render or determine human scale and the source stays unchanged',()=>{
  const source=new Group();
  const body=new Mesh(new BoxGeometry(.5,1.7,.3),new MeshBasicMaterial());body.name='Body';body.position.y=.85;
  const helper=new Mesh(new BoxGeometry(3,3,3),new MeshBasicMaterial());helper.name='Esfera icosaédrica.001';helper.position.y=-1;
  source.add(body,helper);
  const prepared=createCharacterClone(source,1.7);
  assert.equal(isCharacterHelper(helper),true);
  assert.equal(prepared.scene.getObjectByName(helper.name).visible,false);
  assert.equal(helper.visible,true);
  assert.ok(Math.abs(prepared.authoredBounds.min.y)<1e-6);
  assert.ok(Math.abs(prepared.group.scale.y-1)<1e-6);
  assert.equal(isCharacterHelper({isMesh:true,isSkinnedMesh:true,name:'Icosphere',userData:{}}),false);
  assert.equal(isCharacterHelper({isMesh:true,name:'Head',userData:{}}),false);
});

async function geometryOnly(url){
  const buffer=readFileSync(new URL(`../../public${url}`,import.meta.url)),jsonLength=buffer.readUInt32LE(12);
  const gltf=JSON.parse(buffer.subarray(20,20+jsonLength).toString());
  const offset=28+jsonLength,binLength=buffer.readUInt32LE(20+jsonLength);
  gltf.buffers[0].uri=`data:application/octet-stream;base64,${buffer.subarray(offset,offset+binLength).toString('base64')}`;
  gltf.images=[];gltf.textures=[];gltf.materials=[];
  for(const mesh of gltf.meshes)for(const primitive of mesh.primitives)delete primitive.material;
  globalThis.ProgressEvent??=class{constructor(type,fields){this.type=type;Object.assign(this,fields);}};
  return new GLTFLoader().parseAsync(JSON.stringify(gltf),'');
}

test('actual original Remy and fitted uniform normalize to 1.70m without changing source geometry',async()=>{
  for(const url of ['/assets/characters/CHR_Remy_Mixamo_20261005.glb','/assets/characters/CHR_Remy_Senac_Uniform_20261013.glb']){
    const {scene}=await geometryOnly(url),prepared=createCharacterClone(scene,1.7),visibleBounds=new Box3();
    let originalHelpers=0,hiddenHelpers=0;
    scene.traverse(o=>{if(isCharacterHelper(o)){originalHelpers++;assert.equal(o.visible,true);}});
    prepared.group.traverse(o=>{
      if(isCharacterHelper(o)){hiddenHelpers++;assert.equal(o.visible,false);}
      else if(o.isMesh)visibleBounds.expandByObject(o,true);
    });
    assert.equal(hiddenHelpers,originalHelpers);
    assert.ok(Math.abs(visibleBounds.getSize(new Vector3()).y-1.7)<1e-5,url);
  }
});
