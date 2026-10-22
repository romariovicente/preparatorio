import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {existsSync,readFileSync} from 'node:fs';
import {isAbsolute,resolve} from 'node:path';
import {env} from 'node:process';
import {fileURLToPath} from 'node:url';
import {AnimationMixer,Texture,Vector3} from 'three';
import {loadTexturelessGLB} from '../../../scripts/actual_asset_inspection.mjs';
import {createCharacterClone} from '../world/characterModel.js';
import {applyUniformName,cloneUniformMaterials} from './uniformMaterials.js';

const costumes=JSON.parse(readFileSync(new URL('../config/costumeAssets.json',import.meta.url)));
const registered=costumes.find(record=>record.id==='COSTUME_Remy_White_Uniform_Surface_20261022');
const candidate=env.PREP_UNIFORM_SURFACE_GLB??registered?.url;
const expectedHash=(env.PREP_UNIFORM_SURFACE_SHA256??registered?.sha256)?.toLowerCase();
const attachments={
  COAT_BRAND_Remy_Crest:'COAT_Remy_FittedShell',
  COAT_BRAND_Remy_Senac:'COAT_Remy_FittedShell',
  COAT_NAME_Remy_Player:'COAT_Remy_FittedShell',
  SCRUB_BRAND_Remy_Crest:'SCRUB_Remy_Shirt',
  SCRUB_BRAND_Remy_Senac:'SCRUB_Remy_Shirt',
  SCRUB_NAME_Remy_Player:'SCRUB_Remy_Shirt',
};

function candidatePath(value){
  if(value.startsWith('/assets/'))return fileURLToPath(new URL(`../../public${value}`,import.meta.url));
  if(value.startsWith('file:'))return fileURLToPath(value);
  return isAbsolute(value)?value:resolve(value);
}

function values(attribute,index){
  return Array.from({length:attribute.itemSize},(_,component)=>attribute.getComponent(index,component));
}

function assertClose(actual,expected,tolerance,message){
  assert.equal(actual.length,expected.length,message);
  actual.forEach((value,index)=>assert.ok(Math.abs(value-expected[index])<=tolerance,`${message} component ${index}: ${value} != ${expected[index]}`));
}

function attachmentPairs(scene){
  return Object.entries(attachments).map(([decalName,surfaceName])=>{
    const decal=scene.getObjectByName(decalName),surface=scene.getObjectByName(surfaceName);
    assert.ok(decal?.isSkinnedMesh,`${decalName} must be a skinned mesh`);
    assert.ok(surface?.isSkinnedMesh,`${surfaceName} must be a skinned mesh`);
    assert.equal(decal.userData.uniformSurfaceAttachment,true,`${decalName} attachment flag`);
    assert.equal(decal.userData.uniformSurfaceMesh,surfaceName,`${decalName} surface name`);
    const map=decal.userData.uniformSurfaceVertexMap;
    assert.ok(Array.isArray(map),`${decalName} vertex map`);
    assert.equal(map.length,decal.geometry.attributes.position.count,`${decalName} map length`);
    assert.ok(map.every(index=>Number.isInteger(index)&&index>=0&&index<surface.geometry.attributes.position.count),`${decalName} valid mapped indices`);
    assert.equal(decal.bindMode,surface.bindMode,`${decalName} bind mode`);
    assertClose(decal.bindMatrix.elements,surface.bindMatrix.elements,1e-7,`${decalName} bind matrix`);
    assertClose(decal.bindMatrixInverse.elements,surface.bindMatrixInverse.elements,1e-7,`${decalName} inverse bind matrix`);
    const decalIndex=decal.geometry.getAttribute('skinIndex'),surfaceIndex=surface.geometry.getAttribute('skinIndex');
    const decalWeight=decal.geometry.getAttribute('skinWeight'),surfaceWeight=surface.geometry.getAttribute('skinWeight');
    assert.ok(decalIndex&&surfaceIndex&&decalWeight&&surfaceWeight,`${decalName} skin attributes`);
    map.forEach((surfaceVertex,decalVertex)=>{
      assert.deepEqual(values(decalIndex,decalVertex),values(surfaceIndex,surfaceVertex),`${decalName} joints ${decalVertex}`);
      assertClose(values(decalWeight,decalVertex),values(surfaceWeight,surfaceVertex),1e-6,`${decalName} weights ${decalVertex}`);
    });
    return {decal,surface,map};
  });
}

test('real Remy uniform surface attachments remain white and within 1 mm through Idle and Walk',{skip:candidate?false:'white surface uniform is awaiting registration'},async t=>{
    const path=candidatePath(candidate);
    assert.equal(existsSync(path),true,`Missing PREP_UNIFORM_SURFACE_GLB: ${path}`);
    const bytes=readFileSync(path),hash=createHash('sha256').update(bytes).digest('hex');
    assert.match(hash,/^[a-f0-9]{64}$/);
    if(expectedHash)assert.equal(hash,expectedHash,'approved GLB hash');
    else t.diagnostic(`candidate sha256 ${hash}`);
    const gltf=await loadTexturelessGLB(path);
    attachmentPairs(gltf.scene);
    const scrubMeshes=[];
    gltf.scene.traverse(object=>{
      if(!object.isMesh||!/^SCRUB_/.test(object.name)||/^SCRUB_(BRAND|NAME)_/.test(object.name))return;
      scrubMeshes.push(object.name);
      for(const material of Array.isArray(object.material)?object.material:[object.material])assert.equal(material.color?.getHexString(),'ffffff',`${object.name} white fabric`);
    });
    assert.ok(scrubMeshes.length>=3,'shirt, trouser lining and trousers use white fabric');
    const clips=Object.fromEntries(['Idle','Walk'].map(wanted=>{
      const clip=gltf.animations.find(item=>item.name===wanted||item.name.endsWith(`|${wanted}`));
      assert.ok(clip,`Missing ${wanted}`);return [wanted,clip];
    }));
    for(const [clipName,clip] of Object.entries(clips)){
      const {group}=createCharacterClone(gltf.scene,1.7),pairs=attachmentPairs(group),mixer=new AnimationMixer(group);
      mixer.clipAction(clip).reset().play();
      for(const fraction of [0,.25,.5,.75]){
        mixer.setTime(clip.duration*fraction);group.updateMatrixWorld(true);
        group.traverse(object=>{if(object.isSkinnedMesh)object.skeleton.update();});
        let maximum=0;
        for(const {decal,surface,map} of pairs){
          map.forEach((surfaceVertex,decalVertex)=>{
            const decalPoint=decal.getVertexPosition(decalVertex,new Vector3()).applyMatrix4(decal.matrixWorld);
            const surfacePoint=surface.getVertexPosition(surfaceVertex,new Vector3()).applyMatrix4(surface.matrixWorld);
            maximum=Math.max(maximum,decalPoint.distanceTo(surfacePoint));
          });
        }
        assert.ok(maximum<=.001,`${clipName} ${fraction}: attachment gap ${maximum} m`);
      }
    }
    const sourceNameMaterial=gltf.scene.getObjectByName('COAT_NAME_Remy_Player').material;
    const alice=createCharacterClone(gltf.scene,1.7).group,bruno=createCharacterClone(gltf.scene,1.7).group;
    const aliceMaterials=cloneUniformMaterials(alice),brunoMaterials=cloneUniformMaterials(bruno);
    const aliceTexture=new Texture(),brunoTexture=new Texture();
    assert.equal(applyUniformName(alice,aliceTexture),2);assert.equal(applyUniformName(bruno,brunoTexture),2);
    assert.equal(alice.getObjectByName('COAT_NAME_Remy_Player').material.map,aliceTexture);
    assert.equal(bruno.getObjectByName('COAT_NAME_Remy_Player').material.map,brunoTexture);
    assert.equal(sourceNameMaterial.map,null,'cached source name material remains unchanged');
    aliceMaterials.concat(brunoMaterials).forEach(material=>material.dispose());aliceTexture.dispose();brunoTexture.dispose();
});
