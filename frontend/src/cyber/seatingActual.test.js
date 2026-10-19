import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import {createSeatedClone} from './seating.js';
import {finiteDeformedVertices,joint,loadTexturelessGLB,localTransformSnapshot,synchronizeSkinnedBounds} from '../../../scripts/actual_asset_inspection.mjs';

const remyUrl=new URL('../../public/assets/characters/CHR_Remy_Mixamo_20261005.glb',import.meta.url);

test('real Remy seated clone retains all skinned meshes and leaves every original transform untouched',async()=>{
  const catalog=JSON.parse(readFileSync(new URL('../../src/config/mixamoAssets.json',import.meta.url)));
  const record=catalog.find(asset=>asset.id==='CHR_Remy_Mixamo_20261005');
  assert.equal(createHash('sha256').update(readFileSync(remyUrl)).digest('hex'),record.sha256,'the validated original Remy GLB is preserved');
  const {scene}=await loadTexturelessGLB(remyUrl),original=localTransformSnapshot(scene);
  const sourceBones=new Set(),sourceSkins=[];
  scene.traverse(object=>{if(object.isBone)sourceBones.add(object);if(object.isSkinnedMesh)sourceSkins.push(object);});
  assert.ok(sourceBones.size>30,'exercise the actual articulated character');
  assert.equal(sourceSkins.length,7,'all supplied Remy skin and garment meshes are loaded');
  for(const riding of [false,true]){
    const pose=createSeatedClone(scene,1.7,riding),clonedSkins=[];
    pose.group.traverse(object=>{if(object.isSkinnedMesh)clonedSkins.push(object);});
    assert.equal(pose.posed,true);
    assert.equal(clonedSkins.length,sourceSkins.length);
    for(const mesh of clonedSkins){
      assert.ok(mesh.skeleton.bones.length>0);
      assert.ok(mesh.skeleton.bones.every(bone=>!sourceBones.has(bone)),'posed skin must bind only to cloned bones');
      assert.equal(mesh.frustumCulled,false,'posed skin remains visible after it moves outside authored bounds');
    }
    synchronizeSkinnedBounds(pose.group);
    assert.equal(finiteDeformedVertices(pose.group),21459,'all real skinned vertices remain finite after posing');
    assert.deepEqual(localTransformSnapshot(scene),original);
  }
});

test('real Remy sits on a 0.48m bench with knees forward, ankles above the floor and finite bounds',async()=>{
  const {scene}=await loadTexturelessGLB(remyUrl),pose=createSeatedClone(scene,1.7);
  pose.group.position.y=.48+pose.offset;
  const bounds=synchronizeSkinnedBounds(pose.group),hips=joint(pose.group,'Hips');
  assert.ok([...bounds.min.toArray(),...bounds.max.toArray()].every(Number.isFinite));
  assert.ok(hips.y>.50&&hips.y<.60,'pelvis rests just above the bench');
  // A small sole tolerance records the provisional FK shoe fit explicitly.
  assert.ok(bounds.min.y>-.025,'shoe geometry must stay within 2.5cm of the floor');
  for(const side of ['Left','Right']){
    const thigh=joint(pose.group,`${side}UpLeg`),knee=joint(pose.group,`${side}Leg`),ankle=joint(pose.group,`${side}Foot`);
    assert.ok(knee.z>thigh.z+.3);
    assert.ok(Math.abs(knee.y-thigh.y)<.01);
    assert.ok(ankle.y>.05&&ankle.y<knee.y-.3);
  }
});

test('real Remy riding pose sits above the measured Kawasaki saddle, spreads the knees and leans toward the grips',async()=>{
  const {scene}=await loadTexturelessGLB(remyUrl),pose=createSeatedClone(scene,1.7,true);
  pose.group.position.set(0,.94+pose.offset,-.4);
  const bounds=synchronizeSkinnedBounds(pose.group),hips=joint(pose.group,'Hips');
  assert.ok(hips.y>.97&&hips.y<1.04);
  assert.ok(Math.abs(hips.z+.4)<.04,'pelvis stays over the rear saddle instead of inside the tank');
  assert.ok(bounds.min.y>.3,'riding shoes remain above the road');
  assert.ok(joint(pose.group,'Spine2').z>joint(pose.group,'Spine').z+.08,'the actual Mixamo chest inclines toward +Z');
  for(const side of ['Left','Right']){
    const thigh=joint(pose.group,`${side}UpLeg`),knee=joint(pose.group,`${side}Leg`),ankle=joint(pose.group,`${side}Foot`);
    const shoulder=joint(pose.group,`${side}Arm`),hand=joint(pose.group,`${side}Hand`);
    assert.ok(knee.z>thigh.z+.3);
    assert.ok(Math.abs(knee.x)>Math.abs(thigh.x)+.05);
    assert.ok(ankle.y>.35&&ankle.y<knee.y-.3);
    assert.ok(hand.z>shoulder.z+.3,'both forearms extend forward');
    assert.ok(hand.y>1&&hand.y<1.35,'hands are near the handlebar height');
  }
});
