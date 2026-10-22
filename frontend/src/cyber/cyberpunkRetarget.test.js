import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import {AnimationMixer,Vector3} from 'three';
import {createFrozenCharacterClone} from '../world/frozenCharacter.js';
import {finiteDeformedVertices,joint,loadTexturelessGLB,localTransformSnapshot,synchronizeSkinnedBounds} from '../../../scripts/actual_asset_inspection.mjs';

// Independent Blender QA accepted this derivative. Inspect the delivered
// runtime copy by default; the override can recheck the preserved source.
const candidateUrl=globalThis.process.env.PREP_CYBERPUNK_RETARGET_GLB
  ?pathToFileURL(resolve(globalThis.process.env.PREP_CYBERPUNK_RETARGET_GLB))
  :new URL('../../public/assets/characters/CHR_Cyberpunk_Remy_Retarget_20261022_v5.glb',import.meta.url);
const approvedHash='ad3aa0b0ac66f6f8cc47c749dd24890f517b3e2d78ebd228ec8ee2782f4d3fc5';
const up=new Vector3(0,1,0);
const weaponSignal=/(?:^|[_\s.-])(smg|guns?|rifle|sniper|pistol|weapon|mag(?:azine)?|trigger)(?:[_\s.-]|$)/i;
const model=loadTexturelessGLB(candidateUrl);
const remyModel=loadTexturelessGLB(new URL('../../public/assets/characters/runtime/CHR_Remy_Mixamo_Web_20261021.glb',import.meta.url));

function clip(gltf,name){
  const animation=gltf.animations.find(animation=>animation.name===name);
  assert.ok(animation,`${name} must exist in the delivered GLB`);
  assert.ok(animation.duration>0&&Number.isFinite(animation.duration));
  assert.ok(animation.tracks.length>0,`${name} must animate the articulated character`);
  return animation;
}

function privateIdle(gltf,height){
  const prepared=createFrozenCharacterClone(gltf.scene,height,gltf.animations,{clip:'Idle',time:0});
  prepared.poseMixer.stopAllAction();prepared.poseMixer.uncacheRoot(prepared.group);
  const mixer=new AnimationMixer(prepared.group),action=mixer.clipAction(clip(gltf,'Idle')).play();
  action.paused=true;mixer.update(0);
  return {prepared,mixer};
}

function checkPose(group,label){
  const bounds=synchronizeSkinnedBounds(group),size=bounds.getSize(new Vector3());
  assert.ok([...bounds.min.toArray(),...bounds.max.toArray()].every(Number.isFinite),`${label}: finite animated bounds`);
  assert.ok(Math.abs(bounds.min.y)<=.02,`${label}: shoes are ${bounds.min.y.toFixed(6)}m from the floor`);
  const torso=joint(group,'CCBaseHead038').sub(joint(group,'CCBaseHip02')).normalize();
  assert.ok(torso.angleTo(up)<=15*Math.PI/180,`${label}: torso must remain upright`);
  for(const [hand,shoulder] of [['CCBaseLHand055','CCBaseLUpperarm050'],['CCBaseRHand083','CCBaseRUpperarm078']]){
    assert.ok(joint(group,hand).y<joint(group,shoulder).y-.1,`${label}: both hands must remain below the shoulders`);
  }
  assert.ok(finiteDeformedVertices(group)>0,`${label}: real deformed vertices must be finite`);
  return {height:size.y,leftFoot:joint(group,'CCBaseLFoot06'),rightFoot:joint(group,'CCBaseRFoot021')};
}

function legLengths(group){
  group.updateMatrixWorld(true);
  const lengths=[];
  for(const [side,thigh,knee,ankle] of [['left','CCBaseLThigh04','CCBaseLCalf05','CCBaseLFoot06'],['right','CCBaseRThigh018','CCBaseRCalf019','CCBaseRFoot021']]){
    const hipPoint=joint(group,thigh),kneePoint=joint(group,knee),anklePoint=joint(group,ankle);
    lengths.push({name:`${side} thigh`,length:hipPoint.distanceTo(kneePoint)},{name:`${side} shin`,length:kneePoint.distanceTo(anklePoint)});
  }
  return lengths;
}

function headAlignment(group){
  group.updateMatrixWorld(true);
  const leftShoulder=joint(group,'CCBaseLUpperarm050'),rightShoulder=joint(group,'CCBaseRUpperarm078');
  const center=leftShoulder.clone().add(rightShoulder).multiplyScalar(.5);
  const lateral=leftShoulder.clone().sub(rightShoulder).normalize();
  const chain=['CCBaseNeckTwist01036','CCBaseNeckTwist02037','CCBaseHead038'].map(name=>({name,point:joint(group,name)}));
  const centers=chain.map(({name,point})=>({name,offset:Math.abs(point.clone().sub(center).dot(lateral))}));
  const segments=chain.slice(1).map(({name,point},index)=>{
    const direction=point.clone().sub(chain[index].point).normalize();
    return {name:`${chain[index].name} to ${name}`,degrees:Math.asin(Math.min(1,Math.abs(direction.dot(lateral))))*180/Math.PI};
  });
  const eyeLine=joint(group,'CCBaseLEye046').sub(joint(group,'CCBaseREye045')).normalize();
  const torsoUp=center.clone().sub(joint(group,'CCBaseHip02'));
  torsoUp.addScaledVector(lateral,-torsoUp.dot(lateral)).normalize();
  // Check eye roll rather than the full angle to the shoulder line: looking
  // left or right is a valid head motion and must not be rejected as a kink.
  const eyeDegrees=Math.asin(Math.min(1,Math.abs(eyeLine.dot(torsoUp))))*180/Math.PI;
  return {centers,segments,eyeDegrees};
}

test('Cyberpunk Idle keeps the neck and head centered above the shoulders without a sideways kink',async()=>{
  const gltf=await model,source=localTransformSnapshot(gltf.scene),{prepared,mixer}=privateIdle(gltf,1.7);
  try{
    const {centers,segments,eyeDegrees}=headAlignment(prepared.group);
    // Measure delivered joint positions in meters, independently of the
    // retarget mapping. A clone or wrapper cannot hide a displaced neck.
    const displaced=centers.filter(({offset})=>offset>.01);
    assert.equal(displaced.length,0,`Idle first frame: cervical joints must be within 1cm of the shoulder center plane; ${centers.map(({name,offset})=>`${name}=${(offset*100).toFixed(2)}cm`).join(', ')}`);
    const tilted=segments.filter(({degrees})=>degrees>3);
    assert.equal(tilted.length,0,`Idle first frame: neck/head segments must be within 3 degrees of the torso center plane; ${segments.map(({name,degrees})=>`${name}=${degrees.toFixed(2)}deg`).join(', ')}`);
    assert.ok(eyeDegrees<=3,`Idle first frame: the eyes are tilted ${eyeDegrees.toFixed(2)}deg relative to the shoulders`);
    assert.deepEqual(localTransformSnapshot(gltf.scene),source,'head alignment QA must preserve the cached source');
  }finally{
    mixer.stopAllAction();mixer.uncacheRoot(prepared.group);
  }
});

test('Cyberpunk Walk keeps a coherent neck/head chain while allowing natural gait sway',async()=>{
  const gltf=await model,source=localTransformSnapshot(gltf.scene),{prepared,mixer}=privateIdle(gltf,1.7);
  mixer.stopAllAction();
  const walk=clip(gltf,'Walk'),action=mixer.clipAction(walk).play();action.paused=true;
  try{
    for(const phase of [0,.25,.5,.75]){
      action.time=walk.duration*phase;mixer.update(0);
      const {segments,eyeDegrees}=headAlignment(prepared.group);
      for(const {name,degrees} of segments)assert.ok(degrees<=15,`Walk ${phase}: ${name} has ${degrees.toFixed(2)}deg of sideways inclination; at most 15deg allows gait sway`);
      assert.ok(eyeDegrees<=15,`Walk ${phase}: the eyes are tilted ${eyeDegrees.toFixed(2)}deg relative to the shoulders`);
    }
    assert.deepEqual(localTransformSnapshot(gltf.scene),source,'walking head QA must preserve the cached source');
  }finally{
    mixer.stopAllAction();mixer.uncacheRoot(prepared.group);
  }
});

test('Cyberpunk Idle right fingers are as relaxed as the left hand',async()=>{
  const gltf=await model,source=localTransformSnapshot(gltf.scene),{prepared,mixer}=privateIdle(gltf,1.7);
  try{
    prepared.group.updateMatrixWorld(true);
    const leftPalm=joint(prepared.group,'CCBaseLIndex1065').add(joint(prepared.group,'CCBaseLPinky1056')).multiplyScalar(.5);
    const rightPalm=joint(prepared.group,'CCBaseRIndex1093').add(joint(prepared.group,'CCBaseRPinky1096')).multiplyScalar(.5);
    const fingertips=[['Index','067','095'],['Mid','064','089'],['Ring','061','086'],['Pinky','058','098'],['Thumb','070','092']];
    const samples=fingertips.map(([finger,left,right])=>({
      finger,
      left:joint(prepared.group,`CCBaseL${finger}3${left}`).distanceTo(leftPalm),
      right:joint(prepared.group,`CCBaseR${finger}3${right}`).distanceTo(rightPalm),
    }));
    // Distal-joint distance from each palm measures the visible finger curl;
    // it is independent of arm direction and bone quaternion conventions.
    const mismatches=samples.filter(({left,right})=>Math.abs(left-right)>.008);
    assert.equal(mismatches.length,0,`Idle: right fingers must match the relaxed left hand within 8mm; ${samples.map(({finger,left,right})=>`${finger}: L=${(left*100).toFixed(2)}cm, R=${(right*100).toFixed(2)}cm`).join('; ')}`);
    assert.deepEqual(localTransformSnapshot(gltf.scene),source,'hand QA must preserve the cached source');
  }finally{
    mixer.stopAllAction();mixer.uncacheRoot(prepared.group);
  }
});

test('Cyberpunk Walk ankle separation stays within a natural width relative to the hips',async()=>{
  const gltf=await model,source=localTransformSnapshot(gltf.scene),{prepared,mixer}=privateIdle(gltf,1.7);
  mixer.stopAllAction();
  const walk=clip(gltf,'Walk'),action=mixer.clipAction(walk).play();action.paused=true;
  try{
    const samples=[];
    for(let index=0;index<8;index++){
      const phase=index/8;action.time=walk.duration*phase;mixer.update(0);prepared.group.updateMatrixWorld(true);
      const leftHip=joint(prepared.group,'CCBaseLThigh04'),rightHip=joint(prepared.group,'CCBaseRThigh018');
      const hipSpan=leftHip.distanceTo(rightHip),lateral=leftHip.clone().sub(rightHip).normalize();
      const ankleWidth=Math.abs(joint(prepared.group,'CCBaseLFoot06').sub(joint(prepared.group,'CCBaseRFoot021')).dot(lateral));
      samples.push({phase,ankleWidth,limit:hipSpan*1.5+.03});
    }
    const wide=samples.filter(({ankleWidth,limit})=>ankleWidth>limit);
    assert.equal(wide.length,0,`Walk must not keep the legs splayed: lateral ankle width is limited to 1.5 times hip width plus 3cm; ${samples.map(({phase,ankleWidth,limit})=>`${phase}: ${(ankleWidth*100).toFixed(2)}cm / ${(limit*100).toFixed(2)}cm`).join('; ')}`);
    assert.deepEqual(localTransformSnapshot(gltf.scene),source,'leg QA must preserve the cached source');
  }finally{
    mixer.stopAllAction();mixer.uncacheRoot(prepared.group);
  }
});

test('Cyberpunk retargeted Idle has Remy height in authored meters and in the runtime wrapper',async()=>{
  const gltf=await model,source=localTransformSnapshot(gltf.scene);
  clip(gltf,'Walk');
  for(const height of [0,1.7]){
    const {prepared,mixer}=privateIdle(gltf,height);
    const sample=checkPose(prepared.group,height===0?'authored Idle':'normalized Idle');
    assert.ok(Math.abs(sample.height-1.7)<=.02,`Idle height ${sample.height.toFixed(6)}m must match Remy within 2cm`);
    mixer.stopAllAction();mixer.uncacheRoot(prepared.group);
  }
  assert.deepEqual(localTransformSnapshot(gltf.scene),source,'Idle QA must not change cached source transforms');
});

test('Cyberpunk retargeted Walk stays grounded and follows Remy gait height without stretching the legs',async()=>{
  const gltf=await model,source=localTransformSnapshot(gltf.scene),{prepared,mixer}=privateIdle(gltf,1.7);
  const remy=await remyModel,remySource=localTransformSnapshot(remy.scene),reference=privateIdle(remy,1.7);
  const standingLegLengths=legLengths(prepared.group);
  mixer.stopAllAction();
  const walk=clip(gltf,'Walk'),action=mixer.clipAction(walk).play();action.paused=true;
  reference.mixer.stopAllAction();
  const remyWalk=clip(remy,'Walk'),referenceAction=reference.mixer.clipAction(remyWalk).play();referenceAction.paused=true;
  const deltas=walk.tracks.flatMap(track=>Array.from(track.times).slice(1).map((time,index)=>time-track.times[index]).filter(delta=>delta>1e-6));
  assert.ok(deltas.length>0,'Walk needs multiple time samples');
  const frameStep=Math.min(...deltas),phases=[0,.125,.25,.375,.5,.625,.75,.875],samples=[];
  try{
    for(const phase of phases)for(const offset of [0,frameStep/2]){
      const time=Math.min(walk.duration,walk.duration*phase+offset),label=`Walk ${phase}+${offset.toFixed(6)}s`;
      action.time=time;mixer.update(0);
      referenceAction.time=remyWalk.duration*time/walk.duration;reference.mixer.update(0);
      const sample=checkPose(prepared.group,label);
      const referenceHeight=synchronizeSkinnedBounds(reference.prepared.group).getSize(new Vector3()).y;
      // Walking lowers the head as the knees flex. Compare the real Remy
      // motion at the same phase instead of treating that flexion as scaling.
      assert.ok(Math.abs(sample.height-referenceHeight)<=.02,`${label}: animated height ${sample.height.toFixed(6)}m must follow real Remy ${referenceHeight.toFixed(6)}m within 2cm`);
      for(const [index,segment] of legLengths(prepared.group).entries()){
        assert.ok(Math.abs(segment.length-standingLegLengths[index].length)<=.001,`${label}: ${segment.name} must preserve its Idle length within 1mm`);
      }
      samples.push(sample);
    }
    assert.equal(samples.length,16,'eight keyed phases and eight half-frame interpolated phases are checked');
    for(const side of ['leftFoot','rightFoot']){
      const movement=Math.max(...samples.map(sample=>sample[side].distanceTo(samples[0][side])));
      assert.ok(movement>.05,`${side} must perform a real step instead of sliding in one fixed pose`);
    }
    assert.deepEqual(localTransformSnapshot(gltf.scene),source,'Walk QA must not change cached source transforms');
    assert.deepEqual(localTransformSnapshot(remy.scene),remySource,'Walk QA must not change the cached Remy reference');
  }finally{
    mixer.stopAllAction();mixer.uncacheRoot(prepared.group);
    reference.mixer.stopAllAction();reference.mixer.uncacheRoot(reference.prepared.group);
  }
});

test('Cyberpunk retarget uses private skeletons and contains no firearm mesh or material',async()=>{
  const gltf=await model,source=localTransformSnapshot(gltf.scene),sourceBones=new Set();
  gltf.scene.traverse(object=>{if(object.isBone)sourceBones.add(object);});
  assert.ok(sourceBones.size>=90,'the complete articulated Cyberpunk rig must be retained');
  const {prepared,mixer}=privateIdle(gltf,1.7);let skins=0;
  prepared.group.traverse(object=>{
    if(!object.isSkinnedMesh)return;
    skins++;
    assert.ok(object.skeleton.bones.every(bone=>!sourceBones.has(bone)),'each skin must bind only to cloned bones');
  });
  assert.ok(skins>0,'the delivered derivative must retain skinned geometry');
  const bytes=readFileSync(candidateUrl),jsonLength=bytes.readUInt32LE(12),doc=JSON.parse(bytes.toString('utf8',20,20+jsonLength));
  assert.equal(createHash('sha256').update(bytes).digest('hex'),approvedHash,'the exact independently reimported GLB must be used');
  // Retained empty gun attachment bones do not render a weapon. Inspect only
  // actual mesh and material definitions rather than rejecting rig node names.
  for(const item of [...doc.meshes??[],...doc.materials??[]])assert.equal(weaponSignal.test(item.name??''),false,item.name);
  assert.deepEqual(localTransformSnapshot(gltf.scene),source);
  mixer.stopAllAction();mixer.uncacheRoot(prepared.group);
});
