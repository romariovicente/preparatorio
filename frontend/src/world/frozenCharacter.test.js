import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {AnimationMixer,Box3,Vector3} from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {createFrozenCharacterClone} from './frozenCharacter.js';

async function loadGeometry(url){
  const buffer=readFileSync(new URL(`../../public${url}`,import.meta.url)),jsonLength=buffer.readUInt32LE(12);
  const json=JSON.parse(buffer.subarray(20,20+jsonLength).toString()),offset=28+jsonLength,binLength=buffer.readUInt32LE(20+jsonLength);
  json.buffers[0].uri=`data:application/octet-stream;base64,${buffer.subarray(offset,offset+binLength).toString('base64')}`;
  json.images=[];json.textures=[];json.materials=[];
  for(const mesh of json.meshes)for(const primitive of mesh.primitives)delete primitive.material;
  globalThis.ProgressEvent??=class{constructor(type,fields){this.type=type;Object.assign(this,fields);}};
  return {gltf:await new GLTFLoader().parseAsync(JSON.stringify(json),''),hash:createHash('sha256').update(buffer).digest('hex')};
}

function bounds(scene){
  const box=new Box3();scene.updateMatrixWorld(true);
  scene.traverse(object=>{
    if(object.isSkinnedMesh){object.skeleton.update();object.computeBoundingBox();object.computeBoundingSphere();}
    if(object.isMesh&&!object.userData.characterHelper)box.expandByObject(object,true);
  });return box;
}

test('actual anime native Idle/Walk keep finite skinned vertices, upright torso and stable scale',async()=>{
  const {gltf,hash}=await loadGeometry('/assets/supplied/SUP_lowpoly_anime_character_cyberstyle_Color_v2.glb');
  assert.equal(hash,'d470f6653b7407f5324c6df1500f7ada05fd8e6df2e4709d9d7aa3bbfc27dba8');
  const sourceState=gltf.scene.toJSON().object;
  const pose={clip:'Armature|Idle',time:0};
  const prepared=createFrozenCharacterClone(gltf.scene,1.7,gltf.animations,pose),standing=bounds(prepared.group);
  assert.ok(Math.abs(standing.min.y)<1e-5);assert.ok(Math.abs(standing.getSize(new Vector3()).y-1.7)<1e-5);
  let bones=0;prepared.group.traverse(object=>{if(object.isBone)bones++;});assert.equal(bones,145);
  const mixer=new AnimationMixer(prepared.group),heights=[];
  for(const name of ['Armature|Idle','Armature|Walk']){
    const clip=gltf.animations.find(clip=>clip.name===name);assert.ok(clip);
    const action=mixer.clipAction(clip).play();action.paused=true;
    for(const ratio of [0,.25,.5,.75,.99]){
      action.time=clip.duration*ratio;mixer.update(0);const box=bounds(prepared.group);heights.push(box.getSize(new Vector3()).y);
      let hips,head;
      prepared.group.traverse(object=>{
        if(object.isBone&&/Hips_02$/i.test(object.name))hips=object.getWorldPosition(new Vector3());
        if(object.isBone&&/Head_07$/i.test(object.name))head=object.getWorldPosition(new Vector3());
        if(object.isSkinnedMesh){
          const vertex=new Vector3();for(let index=0;index<object.geometry.attributes.position.count;index++){
            object.getVertexPosition(index,vertex);assert.ok(vertex.toArray().every(Number.isFinite));
          }
        }
      });
      assert.ok(hips&&head);const direction=head.sub(hips).normalize();assert.ok(direction.angleTo(new Vector3(0,1,0))<15*Math.PI/180);
      assert.ok(Math.abs(box.min.y)<.035,'animated shoes must stay near the grounded standing sample');
    }
    action.stop();
  }
  assert.ok(Math.max(...heights)/Math.min(...heights)<1.08);
  assert.deepEqual(gltf.scene.toJSON().object,sourceState);
});

test('actual cyberpunk fixed pose is grounded, upright and cannot modify cached source bones',async()=>{
  const {gltf,hash}=await loadGeometry('/assets/supplied/SUP_character_cyberpunk_free_3d_by_oscar_cre_Civilian_v1.glb');
  assert.equal(hash,'4aacf549b4e78361ad2a4d61bfd598760ac9db72774c0457b59f8c6bbf27e79c');
  const sourceState=gltf.scene.toJSON().object;
  const prepared=createFrozenCharacterClone(gltf.scene,1.7,gltf.animations,{clip:'motion',time:0}),box=bounds(prepared.group);
  assert.ok(Math.abs(box.min.y)<1e-5);assert.ok(Math.abs(box.getSize(new Vector3()).y-1.7)<1e-5);
  let bones=0,hips,head;
  prepared.group.traverse(object=>{
    if(object.isBone)bones++;
    if(/CC_Base_Hip_02$/i.test(object.name))hips=object.getWorldPosition(new Vector3());
    if(/CC_Base_Head_038$/i.test(object.name))head=object.getWorldPosition(new Vector3());
  });
  assert.equal(bones,107);assert.ok(head.sub(hips).normalize().angleTo(new Vector3(0,1,0))<15*Math.PI/180);
  assert.deepEqual(gltf.scene.toJSON().object,sourceState);
  assert.throws(()=>createFrozenCharacterClone(gltf.scene,1.7,gltf.animations,{clip:'Walk',time:0}),/pose revisada/);
});
