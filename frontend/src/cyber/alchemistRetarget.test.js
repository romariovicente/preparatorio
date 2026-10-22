import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import {AnimationMixer,Vector3} from 'three';
import {createFrozenCharacterClone} from '../world/frozenCharacter.js';
import {finiteDeformedVertices,joint,loadTexturelessGLB,localTransformSnapshot,synchronizeSkinnedBounds} from '../../../scripts/actual_asset_inspection.mjs';

const characterId='SUP_plague_doctor_alchemist___glass_beak_mask';
const expectedUrl='/assets/characters/CHR_Alchemist_Anime_Retarget_20261022.glb';
const candidateUrl=globalThis.process.env.PREP_ALCHEMIST_RETARGET_GLB
  ?pathToFileURL(resolve(globalThis.process.env.PREP_ALCHEMIST_RETARGET_GLB))
  :new URL('../../public'+expectedUrl,import.meta.url);
const reviews=JSON.parse(readFileSync(new URL('../config/characterMotionReviews.json',import.meta.url),'utf8'));
const rigs=JSON.parse(readFileSync(new URL('../config/riggedAssets.json',import.meta.url),'utf8'));
const up=new Vector3(0,1,0);
let modelPromise;

const model=()=>modelPromise??=loadTexturelessGLB(candidateUrl);
const normalized=value=>String(value??'').replace(/[^a-z0-9]/gi,'').toLowerCase();

function clip(gltf,name){
  const animation=gltf.animations.find(item=>item.name===name);
  assert.ok(animation,`${name} must exist in the delivered Alchemist GLB`);
  assert.ok(animation.duration>0&&Number.isFinite(animation.duration),`${name} must have a finite duration`);
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

function legLengths(group){
  group.updateMatrixWorld(true);
  const result=[];
  for(const [side,thigh,knee,ankle] of [['left','Lthigh','Lshin','Lfoot'],['right','Rthigh','Rshin','Rfoot']]){
    const hipPoint=joint(group,thigh),kneePoint=joint(group,knee),anklePoint=joint(group,ankle);
    result.push({name:`${side} thigh`,length:hipPoint.distanceTo(kneePoint)});
    result.push({name:`${side} shin`,length:kneePoint.distanceTo(anklePoint)});
  }
  return result;
}

function attributeComponent(attribute,index,component){
  return [attribute.getX,attribute.getY,attribute.getZ,attribute.getW][component].call(attribute,index);
}

// This 20-bone target deliberately ends each leg at L_foot/R_foot and has no
// ToeBase. Ground contact therefore comes from CPU-skinned vertices influenced
// by the terminal foot bone, rather than treating the ankle joint as the sole.
function skinnedFootMinima(group){
  group.updateMatrixWorld(true);
  const point=new Vector3(),result={left:Infinity,right:Infinity,leftVertices:0,rightVertices:0};
  group.traverse(object=>{
    if(!object.isSkinnedMesh)return;
    object.skeleton.update();
    const skinIndex=object.geometry.attributes.skinIndex,skinWeight=object.geometry.attributes.skinWeight;
    assert.ok(skinIndex&&skinWeight,`${object.name} must retain skin indices and weights`);
    const footIndices={};
    object.skeleton.bones.forEach((bone,index)=>{
      const name=normalized(bone.name);
      if(name.endsWith('lfoot'))footIndices.left=index;
      if(name.endsWith('rfoot'))footIndices.right=index;
    });
    for(const side of ['left','right'])assert.ok(Number.isInteger(footIndices[side]),`${side} terminal foot bone must exist`);
    for(let vertex=0;vertex<skinIndex.count;vertex++){
      for(const side of ['left','right']){
        let influence=0;
        for(let component=0;component<skinIndex.itemSize;component++){
          if(attributeComponent(skinIndex,vertex,component)===footIndices[side])influence+=attributeComponent(skinWeight,vertex,component);
        }
        if(influence<=.01)continue;
        object.getVertexPosition(vertex,point).applyMatrix4(object.matrixWorld);
        result[side]=Math.min(result[side],point.y);result[`${side}Vertices`]++;
      }
    }
  });
  for(const side of ['left','right']){
    assert.ok(result[`${side}Vertices`]>0,`${side} foot must influence real vertices`);
    assert.ok(Number.isFinite(result[side]),`${side} foot vertex minimum must be finite`);
  }
  return result;
}

function poseSample(group,label){
  const bounds=synchronizeSkinnedBounds(group),size=bounds.getSize(new Vector3());
  assert.ok([...bounds.min.toArray(),...bounds.max.toArray()].every(Number.isFinite),`${label}: animated bounds must be finite`);
  assert.ok(Math.abs(bounds.min.y)<=.02,`${label}: CPU-skinned geometry is ${bounds.min.y.toFixed(6)}m from the floor`);
  assert.ok(finiteDeformedVertices(group)>0,`${label}: real deformed vertices must remain finite`);
  const feet=skinnedFootMinima(group),supportingMinimum=Math.min(feet.left,feet.right);
  assert.ok(Math.abs(supportingMinimum)<=.02,`${label}: the supporting terminal-foot vertices are ${supportingMinimum.toFixed(6)}m from the floor`);
  return {
    height:size.y,
    leftFoot:joint(group,'Lfoot'),
    rightFoot:joint(group,'Rfoot'),
    feet,
  };
}

function hipsRigidRegion(group){
  let mesh;
  group.traverse(object=>{if(object.isSkinnedMesh){assert.equal(mesh,undefined,'the Alchemist must remain one skinned mesh');mesh=object;}});
  assert.ok(mesh,'the Alchemist skinned mesh must exist');
  const skinIndex=mesh.geometry.attributes.skinIndex,skinWeight=mesh.geometry.attributes.skinWeight;
  const position=mesh.geometry.attributes.position,uv=mesh.geometry.attributes.uv;
  assert.ok(skinIndex&&skinWeight&&position&&uv,'the rigid accessory region must retain positions, UVs and skin weights');
  assert.equal(uv.count,position.count,'the exported UV vertex domain must match the geometry');
  const hipsIndex=mesh.skeleton.bones.findIndex(bone=>normalized(bone.name).endsWith('hips'));
  assert.ok(hipsIndex>=0,'the 20-bone target must contain hips');
  const vertices=[];
  for(let vertex=0;vertex<skinIndex.count;vertex++){
    const influences=[];
    for(let component=0;component<skinIndex.itemSize;component++){
      const weight=attributeComponent(skinWeight,vertex,component);
      if(weight>1e-6)influences.push({joint:attributeComponent(skinIndex,vertex,component),weight});
    }
    if(influences.length!==1||influences[0].joint!==hipsIndex||Math.abs(influences[0].weight-1)>1e-5)continue;
    assert.ok(Number.isFinite(uv.getX(vertex))&&Number.isFinite(uv.getY(vertex)),`hips-only vertex ${vertex} must retain finite UV coordinates`);
    vertices.push(vertex);
  }
  return {mesh,vertices};
}

function deformedPoints(mesh,vertices){
  mesh.updateMatrixWorld(true);
  return vertices.map(vertex=>mesh.getVertexPosition(vertex,new Vector3()).applyMatrix4(mesh.matrixWorld));
}

function extremeVertices(mesh,vertices){
  const points=deformedPoints(mesh,vertices),chosen=new Set();
  for(const axis of ['x','y','z']){
    let minimum=0,maximum=0;
    for(let index=1;index<points.length;index++){
      if(points[index][axis]<points[minimum][axis])minimum=index;
      if(points[index][axis]>points[maximum][axis])maximum=index;
    }
    chosen.add(vertices[minimum]);chosen.add(vertices[maximum]);
  }
  return [...chosen];
}

function pairDistances(points){
  const distances=[];
  for(let left=0;left<points.length;left++)for(let right=left+1;right<points.length;right++)distances.push(points[left].distanceTo(points[right]));
  return distances;
}

test('Alchemist retarget is the reviewed Anime-derived 20-bone single-skin GLB',async()=>{
  const review=reviews.find(item=>item.id===characterId),record=rigs.find(item=>item.id===characterId);
  assert.ok(review,'the Alchemist needs a hash-bound motion review');
  assert.ok(record,'the Alchemist needs a runtime rig record');
  assert.equal(record.url,expectedUrl);
  assert.equal(record.retargetSourceId,'SUP_lowpoly_anime_character_cyberstyle');
  assert.equal(record.scaleReferenceId,'CHR_Remy_Mixamo_20261005');
  assert.equal(review.controlMode,'retargeted');assert.equal(review.poseReviewed,true);assert.equal(review.locomotionValidated,true);
  assert.equal(review.idleClip,'Idle');assert.equal(review.walkClip,'Walk');
  const bytes=readFileSync(candidateUrl),hash=createHash('sha256').update(bytes).digest('hex');
  assert.equal(hash,review.sha256,'the delivered GLB must match the independently approved review hash');
  assert.equal(hash,record.sha256,'the runtime catalog and motion review must trust the same exact GLB');
  assert.equal(bytes.length,record.bytes);
  const jsonLength=bytes.readUInt32LE(12),doc=JSON.parse(bytes.toString('utf8',20,20+jsonLength));
  assert.equal(doc.skins?.length,1,'the Alchemist must have one skin');
  assert.equal(doc.skins[0].joints.length,20,'the Alchemist target rig has exactly 20 bones');
  const skinnedNodes=doc.nodes.filter(node=>node.skin!==undefined);
  assert.equal(skinnedNodes.length,1,'the original Alchemist must remain one skinned mesh without an additive garment shell');
  const mesh=doc.meshes[skinnedNodes[0].mesh];
  assert.ok(mesh.primitives.length>0);
  for(const primitive of mesh.primitives){
    assert.ok(primitive.attributes.POSITION!==undefined);
    assert.ok(primitive.attributes.JOINTS_0!==undefined&&primitive.attributes.WEIGHTS_0!==undefined,'all geometry must retain skin weights');
    assert.equal(doc.accessors[primitive.attributes.POSITION].count,doc.accessors[primitive.attributes.WEIGHTS_0].count);
  }
  assert.deepEqual(doc.animations.map(animation=>animation.name).sort(),['Idle','Walk']);
  const gltf=await model(),sourceBones=new Set(),skins=[];
  gltf.scene.traverse(object=>{if(object.isBone)sourceBones.add(object);if(object.isSkinnedMesh)skins.push(object);});
  assert.equal(sourceBones.size,20);assert.equal(skins.length,1);
  clip(gltf,'Idle');clip(gltf,'Walk');
  const {prepared,mixer}=privateIdle(gltf,1.7),clonedSkins=[];
  try{
    prepared.group.traverse(object=>{if(object.isSkinnedMesh)clonedSkins.push(object);});
    assert.equal(clonedSkins.length,1);
    assert.ok(clonedSkins[0].skeleton.bones.every(bone=>!sourceBones.has(bone)),'runtime instances must use a private cloned skeleton');
  }finally{
    mixer.stopAllAction();mixer.uncacheRoot(prepared.group);
  }
});

test('Alchemist Idle is authored at Remy height, grounded and anatomically upright',async()=>{
  const gltf=await model(),source=localTransformSnapshot(gltf.scene);
  for(const height of [0,1.7]){
    const {prepared,mixer}=privateIdle(gltf,height);
    try{
      const sample=poseSample(prepared.group,height===0?'authored Idle':'runtime-normalized Idle');
      assert.ok(Math.abs(sample.height-1.7)<=.02,`Idle height ${sample.height.toFixed(6)}m must match Remy within 2cm`);
      const torso=joint(prepared.group,'head').sub(joint(prepared.group,'hips')).normalize();
      assert.ok(torso.angleTo(up)<=15*Math.PI/180,'Idle torso must remain within 15 degrees of vertical');
      for(const [hand,shoulder] of [['Lhand','Lupperarm'],['Rhand','Rupperarm']]){
        assert.ok(joint(prepared.group,hand).y<joint(prepared.group,shoulder).y-.05,'Idle hands must remain below the shoulders');
      }
    }finally{
      mixer.stopAllAction();mixer.uncacheRoot(prepared.group);
    }
  }
  assert.deepEqual(localTransformSnapshot(gltf.scene),source,'Idle QA must not mutate the cached Alchemist source');
});

test('Alchemist Idle keeps both terminal-foot vertex regions within 2cm of the floor in eight phases',async()=>{
  const gltf=await model(),source=localTransformSnapshot(gltf.scene),{prepared,mixer}=privateIdle(gltf,1.7);
  mixer.stopAllAction();
  const idle=clip(gltf,'Idle'),action=mixer.clipAction(idle).play();action.paused=true;
  try{
    for(let index=0;index<8;index++){
      const phase=index/8;action.time=idle.duration*phase;mixer.update(0);
      const {feet}=poseSample(prepared.group,`Idle ${phase}`);
      for(const side of ['left','right']){
        assert.ok(Math.abs(feet[side])<=.02,
          `Idle ${phase}: ${side} terminal-foot vertices are ${feet[side].toFixed(6)}m from the floor; both feet must remain within 2cm`);
      }
    }
    assert.deepEqual(localTransformSnapshot(gltf.scene),source,'eight-phase Idle QA must not mutate the cached Alchemist source');
  }finally{
    mixer.stopAllAction();mixer.uncacheRoot(prepared.group);
  }
});

test('Alchemist Anime-derived Walk takes real grounded steps without stretching either leg',async()=>{
  const gltf=await model(),source=localTransformSnapshot(gltf.scene),{prepared,mixer}=privateIdle(gltf,1.7);
  const standingLegLengths=legLengths(prepared.group);
  mixer.stopAllAction();
  const walk=clip(gltf,'Walk'),action=mixer.clipAction(walk).play();action.paused=true;
  const deltas=walk.tracks.flatMap(track=>Array.from(track.times).slice(1)
    .map((time,index)=>time-track.times[index]).filter(delta=>delta>1e-6));
  assert.ok(deltas.length>0,'Walk must contain multiple keyed samples');
  const frameStep=Math.min(...deltas),samples=[];
  try{
    for(const phase of [0,.125,.25,.375,.5,.625,.75,.875])for(const offset of [0,frameStep/2]){
      const time=Math.min(walk.duration,walk.duration*phase+offset),label=`Walk ${phase}+${offset.toFixed(6)}s`;
      action.time=time;mixer.update(0);
      const sample=poseSample(prepared.group,label);
      for(const [index,segment] of legLengths(prepared.group).entries()){
        assert.ok(Math.abs(segment.length-standingLegLengths[index].length)<=.001,`${label}: ${segment.name} changed length by more than 1mm`);
      }
      samples.push(sample);
    }
    assert.equal(samples.length,16,'eight keyed phases and eight half-frame interpolated phases are checked');
    for(const side of ['leftFoot','rightFoot']){
      const movement=Math.max(...samples.map(sample=>sample[side].distanceTo(samples[0][side])));
      assert.ok(movement>.05,`${side} terminal bone must move at least 5cm during a real step`);
    }
    assert.deepEqual(localTransformSnapshot(gltf.scene),source,'Walk QA must not mutate the cached Alchemist source');
  }finally{
    mixer.stopAllAction();mixer.uncacheRoot(prepared.group);
  }
});

test('Alchemist bottle region stays UV-preserved and rigidly attached to hips throughout Walk',async()=>{
  const gltf=await model(),source=localTransformSnapshot(gltf.scene),{prepared,mixer}=privateIdle(gltf,1.7);
  const {mesh,vertices}=hipsRigidRegion(prepared.group);
  assert.ok(vertices.length>=2057,`expected at least 2057 vertices exclusively weighted to hips, found ${vertices.length}`);
  const extremes=extremeVertices(mesh,vertices);
  assert.ok(extremes.length>=4,'the hips-only accessory region must have at least four distinct geometric extremes');
  const referenceDistances=pairDistances(deformedPoints(mesh,extremes));
  assert.ok(referenceDistances.some(distance=>distance>.05),'the sampled rigid region must span visible bottle geometry');
  mixer.stopAllAction();
  const walk=clip(gltf,'Walk'),action=mixer.clipAction(walk).play();action.paused=true;
  try{
    for(const phase of [0,.25,.5,.75]){
      action.time=walk.duration*phase;mixer.update(0);prepared.group.updateMatrixWorld(true);
      const distances=pairDistances(deformedPoints(mesh,extremes));
      assert.equal(distances.length,referenceDistances.length);
      for(let index=0;index<distances.length;index++){
        assert.ok(Math.abs(distances[index]-referenceDistances[index])<=1e-5,
          `Walk ${phase}: rigid hips accessory distance ${index} changed by ${Math.abs(distances[index]-referenceDistances[index]).toFixed(8)}m`);
      }
    }
    assert.deepEqual(localTransformSnapshot(gltf.scene),source,'bottle-region QA must not mutate the cached Alchemist source');
  }finally{
    mixer.stopAllAction();mixer.uncacheRoot(prepared.group);
  }
});
