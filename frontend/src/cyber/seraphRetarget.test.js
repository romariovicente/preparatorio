import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import {AnimationMixer,Vector3} from 'three';
import {createFrozenCharacterClone} from '../world/frozenCharacter.js';
import {finiteDeformedVertices,joint,loadTexturelessGLB,localTransformSnapshot,synchronizeSkinnedBounds} from '../../../scripts/actual_asset_inspection.mjs';

const characterId='SUP_bone_seraph_skeletal_angel';
const expectedUrl='/assets/characters/CHR_Seraph_Anime_Retarget_20261023.glb';
const candidateUrl=globalThis.process.env.PREP_SERAPH_RETARGET_GLB
  ?pathToFileURL(resolve(globalThis.process.env.PREP_SERAPH_RETARGET_GLB))
  :new URL('../../public'+expectedUrl,import.meta.url);
const reviews=JSON.parse(readFileSync(new URL('../config/characterMotionReviews.json',import.meta.url),'utf8'));
const rigs=JSON.parse(readFileSync(new URL('../config/riggedAssets.json',import.meta.url),'utf8'));
const up=new Vector3(0,1,0);
let modelPromise;

const model=()=>modelPromise??=loadTexturelessGLB(candidateUrl);
const normalized=value=>String(value??'').replace(/[^a-z0-9]/gi,'').toLowerCase();

function clip(gltf,name){
  const animation=gltf.animations.find(item=>item.name===name);
  assert.ok(animation,`${name} must exist in the delivered Seraph GLB`);
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

// This 22-bone target deliberately ends each leg at L_foot/R_foot and has no
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

function boneByName(group,name){
  let found;
  group.traverse(object=>{if(object.isBone&&normalized(object.name)===normalized(name))found=object;});
  assert.ok(found,`${name} must exist in the actual Seraph skeleton`);
  return found;
}

function attachmentSnapshot(group){
  group.updateMatrixWorld(true);
  const attachments=[];
  group.traverse(object=>{
    if(!object.isBone||!object.parent?.isBone)return;
    attachments.push({name:object.name,length:object.getWorldPosition(new Vector3())
      .distanceTo(object.parent.getWorldPosition(new Vector3()))});
  });
  assert.equal(attachments.length,21,'all 22 FK bones must retain one connected skeleton');
  // Hips translation relative to the non-anatomical root carries body sway and
  // floor correction. Its radius is not a limb length; the other twenty
  // parent-child radii, including both wings, must remain invariant.
  const anatomical=attachments.filter(item=>normalized(item.name)!=='hips');
  assert.equal(anatomical.length,20,'all twenty anatomical/wing attachments must be checked');
  return anatomical;
}

function wingAttachments(group){
  group.updateMatrixWorld(true);
  const chest=boneByName(group,'chest');
  return ['L_wing','R_wing'].map(name=>{
    const wing=boneByName(group,name);
    assert.equal(wing.parent,chest,`${name} must remain attached to chest`);
    return {name,point:chest.worldToLocal(wing.getWorldPosition(new Vector3()))};
  });
}

function rigidBoneRegion(group,boneName,minimumVertices){
  let mesh;
  group.traverse(object=>{
    if(!object.isSkinnedMesh)return;
    assert.equal(mesh,undefined,'Seraph must remain one skinned mesh');mesh=object;
  });
  assert.ok(mesh,'the original Seraph body and wings mesh must exist');
  const index=mesh.geometry.attributes.skinIndex,weight=mesh.geometry.attributes.skinWeight;
  const position=mesh.geometry.attributes.position,uv=mesh.geometry.attributes.uv;
  assert.ok(index&&weight&&position&&uv,'rigid regions must retain geometry, skin and UVs');
  assert.equal(uv.count,position.count,'UVs must share the exported vertex domain');
  const boneIndex=mesh.skeleton.bones.findIndex(bone=>normalized(bone.name)===normalized(boneName));
  assert.ok(boneIndex>=0,`${boneName} must exist in the actual skeleton`);
  const vertices=[];
  for(let vertex=0;vertex<weight.count;vertex++){
    let targetWeight=0,otherWeight=0;
    for(let component=0;component<weight.itemSize;component++){
      const value=attributeComponent(weight,vertex,component);
      if(attributeComponent(index,vertex,component)===boneIndex)targetWeight+=value;
      else otherWeight+=value;
    }
    if(Math.abs(targetWeight-1)>1e-6||otherWeight>1e-6)continue;
    assert.ok(Number.isFinite(uv.getX(vertex))&&Number.isFinite(uv.getY(vertex)),
      `${boneName} vertex ${vertex} must retain finite UVs`);
    vertices.push(vertex);
  }
  assert.ok(vertices.length>=minimumVertices,
    `${boneName} needs at least ${minimumVertices} vertices rigidly weighted 100%; found ${vertices.length}`);
  return {mesh,vertices};
}

function regionPoints(mesh,vertices){
  mesh.updateMatrixWorld(true);mesh.skeleton.update();
  return vertices.map(vertex=>mesh.getVertexPosition(vertex,new Vector3()).applyMatrix4(mesh.matrixWorld));
}

function regionExtremes(mesh,vertices){
  const points=regionPoints(mesh,vertices),chosen=new Set();
  for(const axis of ['x','y','z']){
    let low=0,high=0;
    for(let index=1;index<points.length;index++){
      if(points[index][axis]<points[low][axis])low=index;
      if(points[index][axis]>points[high][axis])high=index;
    }
    chosen.add(vertices[low]);chosen.add(vertices[high]);
  }
  assert.ok(chosen.size>=4,'a rigid wing/halo region must have four distinct geometric extremes');
  return [...chosen];
}

function pairDistances(points){
  const distances=[];
  for(let left=0;left<points.length;left++)for(let right=left+1;right<points.length;right++){
    distances.push(points[left].distanceTo(points[right]));
  }
  return distances;
}

test('Seraph retarget is the reviewed Anime-derived 22-bone single-skin GLB',async()=>{
  const review=reviews.find(item=>item.id===characterId),record=rigs.find(item=>item.id===characterId);
  assert.ok(review,'the Seraph needs a hash-bound motion review');
  assert.ok(record,'the Seraph needs a runtime rig record');
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
  assert.equal(doc.skins?.length,1,'the Seraph must have one skin');
  assert.equal(doc.skins[0].joints.length,22,'the Seraph target rig has exactly 20 bones');
  const skinnedNodes=doc.nodes.filter(node=>node.skin!==undefined);
  assert.equal(skinnedNodes.length,1,'the original Seraph must remain one skinned mesh without an additive garment shell');
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
  assert.equal(sourceBones.size,22);assert.equal(skins.length,1);
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

test('Seraph keeps all original body and wing vertices normalized to at most four influences',async()=>{
  const gltf=await model();
  let vertices=0;
  gltf.scene.traverse(object=>{
    if(!object.isSkinnedMesh)return;
    const index=object.geometry.attributes.skinIndex,weight=object.geometry.attributes.skinWeight;
    assert.ok(index&&weight,'the complete Seraph body and wings must remain skinned');
    assert.equal(index.count,weight.count);assert.ok(weight.itemSize<=4);
    for(let vertex=0;vertex<weight.count;vertex++){
      let sum=0,influences=0;
      for(let component=0;component<weight.itemSize;component++){
        const value=attributeComponent(weight,vertex,component);
        assert.ok(Number.isFinite(value)&&value>=0,`vertex ${vertex} must have finite nonnegative weights`);
        if(value<=1e-8)continue;
        const bone=attributeComponent(index,vertex,component);
        assert.ok(Number.isInteger(bone)&&bone>=0&&bone<object.skeleton.bones.length,`vertex ${vertex} must target an actual bone`);
        sum+=value;influences++;
      }
      assert.ok(influences>0&&influences<=4,`vertex ${vertex} needs 1-4 bone influences`);
      assert.ok(Math.abs(sum-1)<.003,`vertex ${vertex} weights sum to ${sum}`);
      vertices++;
    }
  });
  assert.ok(vertices>0,'real Seraph geometry must be checked');
});

test('Seraph Idle is authored at Remy height, grounded and anatomically upright',async()=>{
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
  assert.deepEqual(localTransformSnapshot(gltf.scene),source,'Idle QA must not mutate the cached Seraph source');
});

test('Seraph Idle keeps both terminal-foot vertex regions within 2cm of the floor in eight phases',async()=>{
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
    assert.deepEqual(localTransformSnapshot(gltf.scene),source,'eight-phase Idle QA must not mutate the cached Seraph source');
  }finally{
    mixer.stopAllAction();mixer.uncacheRoot(prepared.group);
  }
});

test('Seraph Anime-derived Walk takes real grounded steps without stretching either leg',async()=>{
  const gltf=await model(),source=localTransformSnapshot(gltf.scene),{prepared,mixer}=privateIdle(gltf,1.7);
  const standingLegLengths=legLengths(prepared.group);
  const standingAttachments=attachmentSnapshot(prepared.group),standingWings=wingAttachments(prepared.group);
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
      for(const [index,attachment] of attachmentSnapshot(prepared.group).entries()){
        assert.equal(attachment.name,standingAttachments[index].name);
        assert.ok(Math.abs(attachment.length-standingAttachments[index].length)<=.001,
          `${label}: ${attachment.name} moved more than 1mm from its parent attachment radius`);
      }
      for(const [index,wing] of wingAttachments(prepared.group).entries()){
        assert.ok(wing.point.distanceTo(standingWings[index].point)<=.001,
          `${label}: ${wing.name} attachment moved more than 1mm relative to the chest`);
      }
      samples.push(sample);
    }
    assert.equal(samples.length,16,'eight keyed phases and eight half-frame interpolated phases are checked');
    for(const side of ['leftFoot','rightFoot']){
      const movement=Math.max(...samples.map(sample=>sample[side].distanceTo(samples[0][side])));
      assert.ok(movement>.05,`${side} terminal bone must move at least 5cm during a real step`);
    }
    assert.deepEqual(localTransformSnapshot(gltf.scene),source,'Walk QA must not mutate the cached Seraph source');
  }finally{
    mixer.stopAllAction();mixer.uncacheRoot(prepared.group);
  }
});

test('Seraph keeps both wings and halo UV-preserved and rigid during four Walk phases',async()=>{
  const gltf=await model(),source=localTransformSnapshot(gltf.scene),{prepared,mixer}=privateIdle(gltf,1.7);
  const regions=[['L_wing',14035],['R_wing',13871],['head',299]].map(([name,count])=>{
    const {mesh,vertices}=rigidBoneRegion(prepared.group,name,count);
    const extremes=regionExtremes(mesh,vertices);
    const distances=pairDistances(regionPoints(mesh,extremes));
    assert.ok(distances.some(distance=>distance>.05),`${name} extremes must span visible geometry`);
    return {name,mesh,extremes,distances};
  });
  mixer.stopAllAction();
  const walk=clip(gltf,'Walk'),action=mixer.clipAction(walk).play();action.paused=true;
  try{
    for(const phase of [0,.25,.5,.75]){
      action.time=walk.duration*phase;mixer.update(0);prepared.group.updateMatrixWorld(true);
      for(const region of regions){
        const distances=pairDistances(regionPoints(region.mesh,region.extremes));
        assert.equal(distances.length,region.distances.length);
        for(let index=0;index<distances.length;index++){
          const error=Math.abs(distances[index]-region.distances[index]);
          assert.ok(error<=1e-5,`Walk ${phase}: ${region.name} extreme pair ${index} changed by ${error.toFixed(8)}m`);
        }
      }
    }
    assert.deepEqual(localTransformSnapshot(gltf.scene),source,'wing/halo QA must not mutate the cached Seraph source');
  }finally{
    mixer.stopAllAction();mixer.uncacheRoot(prepared.group);
  }
});

