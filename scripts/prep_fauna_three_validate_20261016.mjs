/** CPU-only Three.js validation of six delivered fauna GLBs.
 * Five deliveries contain audited zero-specular PBR JSON metadata adaptations;
 * their BIN data, geometry, skins and animations must match preserved originals.
 * Megalodon remains strictly byte-identical to its supplied source.
 * Images/material references are removed only from a reconstructed in-memory GLB.
 * All BIN bytes, node transforms, skins, inverse binds, weights and clips remain
 * unchanged. No DOM, browser, image decoder, public-file edit or bind repair.
 */
import assert from 'node:assert/strict';
import {appendFileSync,constants,copyFileSync,existsSync,readFileSync,writeFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {AnimationMixer,Box3,LoopOnce,Matrix3,Mesh,PropertyBinding,Vector3,REVISION} from '../frontend/node_modules/three/build/three.module.js';
import {GLTFLoader} from '../frontend/node_modules/three/examples/jsm/loaders/GLTFLoader.js';
import {clone} from '../frontend/node_modules/three/examples/jsm/utils/SkeletonUtils.js';

const ROOT=fileURLToPath(new URL('../',import.meta.url));
const ENTRIES=path.join(ROOT,'reports/fauna_catalog_entries_20261016.json');
const REPORT=path.join(ROOT,'reports/fauna_three_20261016.json');
const LOG=path.join(ROOT,'reports/fauna_three_20261016.log');
const COMPAT=path.join(ROOT,'reports/FAUNA_MATERIAL_COMPAT_20261016.json');
const LEGACY_BACKUP=path.join(ROOT,'art/blender/checkpoints/FAUNA_LEGACY_SOURCE_20261016');
const PREVIOUS_REPORT=path.join(ROOT,'reports/fauna_three_before_material_compat_20261016.json');
const PREVIOUS_LOG=path.join(ROOT,'reports/fauna_three_before_material_compat_20261016.log');
const OWNER='prep_fauna_three_validate_20261016_v1';
const COMPAT_OWNER='prep_fauna_material_compat_20261016_v1';
const LEGACY='KHR_materials_pbrSpecularGlossiness';
const SPECULAR='KHR_materials_specular';
const EXPECTED=['FOX','LIONESS','RABBIT','WOLF','HORSE','MEGALODON'].map(name=>`FAUNA_${name}_20261016`);
const TIMES=[0,.3,.6];
const sha=data=>createHash('sha256').update(data).digest('hex');
const jsonSha=data=>sha(JSON.stringify(data));
const finite=values=>Array.from(values).every(Number.isFinite);
const log=message=>appendFileSync(LOG,`${new Date().toISOString()} ${message}\n`,'utf8');
const helper=object=>object.isMesh&&!object.isSkinnedMesh&&/^(icosphere|esferaicosaedrica)(?:\d+)?(?:mesh)?$/.test(
  String(object.userData.asset_node_name??object.name).normalize('NFKD').replace(/[\u0300-\u036f]/g,'').replace(/[^a-z0-9]/gi,'').toLowerCase());

function glbParts(raw){
  assert.equal(raw.toString('ascii',0,4),'glTF');
  assert.equal(raw.readUInt32LE(4),2);assert.equal(raw.readUInt32LE(8),raw.length);
  const chunks=[];let offset=12;
  while(offset<raw.length){
    assert.ok(offset+8<=raw.length);
    const length=raw.readUInt32LE(offset),type=raw.readUInt32LE(offset+4);offset+=8;
    assert.equal(length%4,0);assert.ok(offset+length<=raw.length);
    chunks.push({type,bytes:raw.subarray(offset,offset+length)});offset+=length;
  }
  assert.equal(offset,raw.length);assert.equal(chunks[0].type,0x4e4f534a);
  assert.equal(chunks.filter(chunk=>chunk.type===0x4e4f534a).length,1);
  assert.equal(chunks.filter(chunk=>chunk.type===0x004e4942).length,1);
  return {doc:JSON.parse(chunks[0].bytes.toString('utf8')),chunks};
}

function deliveryChecks(entry,raw,digest){
  if(entry.id==='FAUNA_MEGALODON_20261016'){
    assert.equal(digest,entry.sourceSha256,'Megalodon must remain a byte-identical verified source copy');
    return {byteIdenticalToSource:true,metadataOnlyAdaptation:false,binIdentical:true,
      evidence:{method:'Strict whole-file source SHA256 equality',sourceSha256:entry.sourceSha256}};
  }
  const compatibility=JSON.parse(readFileSync(COMPAT,'utf8'));
  assert.equal(compatibility.owner,COMPAT_OWNER);
  const evidence=compatibility.assets.filter(item=>item.id===entry.id);
  assert.equal(evidence.length,1,'exactly one owned compatibility record for each adapted asset');
  const expected=evidence[0];
  assert.equal(digest,expected.convertedSha256);assert.equal(raw.length,expected.convertedBytes);
  assert.equal(entry.sourceSha256,expected.originalSha256);
  const saved=path.resolve(expected.originalCheckpoint);
  assert.equal(path.dirname(saved),LEGACY_BACKUP,'original checkpoint must be in the owned backup directory');
  assert.equal(path.basename(saved),`${entry.id}.glb`);
  const original=readFileSync(saved);
  assert.equal(sha(original),entry.sourceSha256);assert.equal(original.length,expected.originalBytes);
  assert.notEqual(digest,entry.sourceSha256,'adapted delivery must report that its JSON bytes changed');
  const before=glbParts(original),after=glbParts(raw);
  assert.equal(before.chunks.length,after.chunks.length);
  for(let index=1;index<before.chunks.length;index++){
    assert.equal(before.chunks[index].type,after.chunks[index].type);
    assert.ok(before.chunks[index].bytes.equals(after.chunks[index].bytes),'all non-JSON chunks stay byte-identical');
  }
  const bin=after.chunks.find(chunk=>chunk.type===0x004e4942).bytes;
  assert.equal(sha(bin),expected.binaryChunkSha256Before);assert.equal(sha(bin),expected.binaryChunkSha256After);
  const allowed=new Set(['materials','extensionsUsed','extensionsRequired','asset']);
  const unchanged=Object.keys(before.doc).filter(key=>!allowed.has(key));
  for(const key of unchanged)assert.deepEqual(after.doc[key],before.doc[key],`unchanged JSON field ${key}`);
  assert.deepEqual(Object.keys(after.doc).filter(key=>!allowed.has(key)).sort(),[...unchanged].sort());
  for(const [key,value]of Object.entries(before.doc.asset)){
    if(key==='extras')for(const [credit,content]of Object.entries(value))assert.deepEqual(after.doc.asset.extras[credit],content,'original authorship/license/source retained');
    else assert.deepEqual(after.doc.asset[key],value);
  }
  assert.equal(after.doc.materials.length,before.doc.materials.length);
  for(let index=0;index<before.doc.materials.length;index++){
    const old=before.doc.materials[index],material=after.doc.materials[index],legacy=old.extensions[LEGACY];
    assert.deepEqual(legacy.specularFactor,[0,0,0]);assert.equal(legacy.specularGlossinessTexture,undefined);
    assert.equal(material.extensions[LEGACY],undefined);assert.equal(material.extensions[SPECULAR].specularFactor,0);
    assert.deepEqual(material.pbrMetallicRoughness.baseColorFactor,legacy.diffuseFactor??[1,1,1,1]);
    assert.deepEqual(material.pbrMetallicRoughness.baseColorTexture,legacy.diffuseTexture);
    assert.equal(material.pbrMetallicRoughness.metallicFactor,0);
    assert.equal(material.pbrMetallicRoughness.roughnessFactor,1-(legacy.glossinessFactor??1));
    for(const [key,value]of Object.entries(old))if(!['extensions','extras'].includes(key))assert.deepEqual(material[key],value,`original material field ${key}`);
    assert.deepEqual(material.extras.PREPARATORIO_material_compat_20261016.originalWorkflow,legacy);
  }
  assert.ok(!after.doc.extensionsRequired.includes(LEGACY)&&!after.doc.extensionsUsed.includes(LEGACY));
  assert.ok(after.doc.extensionsRequired.includes(SPECULAR)&&after.doc.extensionsUsed.includes(SPECULAR));
  assert.equal(sha(readFileSync(saved)),entry.sourceSha256,'original checkpoint was read only');
  return {byteIdenticalToSource:false,metadataOnlyAdaptation:true,binIdentical:true,
    evidence:{method:'Audited source checkpoint + exact non-JSON chunk comparison + all non-material JSON fields equal',
      compatibilityReport:COMPAT,sourceCheckpoint:saved,sourceSha256:entry.sourceSha256,
      convertedSha256:digest,binaryChunkSha256:sha(bin),unchangedJSONFields:unchanged,
      nodesSkinsAnimationsAccessorsBufferViewsUnchanged:true,sourceAttributionUnchanged:true,
      materialCount:after.doc.materials.length}};
}

function geometrySignature(doc){
  return jsonSha({nodes:doc.nodes,skins:doc.skins,animations:doc.animations,
    buffers:doc.buffers,bufferViews:doc.bufferViews,accessors:doc.accessors,
    meshes:doc.meshes.map(mesh=>({...mesh,primitives:mesh.primitives.map(primitive=>{
      const value={...primitive};delete value.material;
      if(value.extensions?.KHR_materials_variants){value.extensions={...value.extensions};delete value.extensions.KHR_materials_variants;}
      return value;
    })}))});
}

function texturelessCopy(raw){
  assert.equal(raw.toString('ascii',0,4),'glTF');
  assert.equal(raw.readUInt32LE(4),2);
  assert.equal(raw.readUInt32LE(8),raw.length);
  assert.equal(raw.readUInt32LE(16),0x4e4f534a);
  const jsonLength=raw.readUInt32LE(12);
  const doc=JSON.parse(raw.toString('utf8',20,20+jsonLength));
  assert.ok((doc.buffers??[]).every(buffer=>!buffer.uri),'external geometry buffers are not allowed');
  const signature=geometrySignature(doc);
  const removed={images:doc.images?.length??0,textures:doc.textures?.length??0,materials:doc.materials?.length??0};
  delete doc.images;delete doc.textures;delete doc.materials;delete doc.samplers;
  for(const mesh of doc.meshes)for(const primitive of mesh.primitives){
    delete primitive.material;
    if(primitive.extensions)delete primitive.extensions.KHR_materials_variants;
  }
  if(doc.extensions)delete doc.extensions.KHR_materials_variants;
  const materialExtension=name=>name.startsWith('KHR_materials_')||name==='KHR_texture_transform'||/^(EXT_texture_|KHR_texture_basisu|MSFT_texture_dds)/.test(name);
  for(const key of ['extensionsUsed','extensionsRequired'])if(doc[key])doc[key]=doc[key].filter(name=>!materialExtension(name));
  assert.equal(geometrySignature(doc),signature,'in-memory image removal must preserve all skin/animation/geometry data');
  const text=Buffer.from(JSON.stringify(doc),'utf8');
  const chunk=Buffer.concat([text,Buffer.alloc((4-text.length%4)%4,32)]);
  const tail=raw.subarray(20+jsonLength);
  const buffer=Buffer.alloc(20+chunk.length+tail.length);
  raw.copy(buffer,0,0,12);buffer.writeUInt32LE(buffer.length,8);
  buffer.writeUInt32LE(chunk.length,12);buffer.writeUInt32LE(0x4e4f534a,16);
  chunk.copy(buffer,20);tail.copy(buffer,20+chunk.length);
  assert.ok(buffer.subarray(20+chunk.length).equals(tail),'all original BIN chunks must remain byte-identical');
  return {buffer,doc,removed,skinAnimationGeometryDigest:signature,binChunksSha256:sha(tail)};
}

function objects(root){
  const meshes=[],skins=[],bones=[],all=new Set(),helpers=[];
  root.traverse(object=>{
    all.add(object);
    if(object.isBone)bones.push(object);
    if(helper(object))helpers.push(object);
    else if(object.isMesh)meshes.push(object);
    if(object.isSkinnedMesh)skins.push(object);
  });
  return {meshes,skins,bones,all,helpers};
}

function skeletonChecks(root,sourceObjects,expectedJointCounts){
  const found=objects(root);
  assert.ok(found.skins.length>0,'requires an actual SkinnedMesh');
  assert.ok(found.bones.length>0,'requires actual Bone nodes');
  const weights=[];
  for(const mesh of found.skins){
    const skeleton=mesh.skeleton;
    assert.ok(expectedJointCounts.includes(skeleton.bones.length),'skin joint count must match serialized GLB');
    assert.equal(skeleton.bones.length,skeleton.boneInverses.length);
    assert.ok(skeleton.bones.every(bone=>bone?.isBone&&found.all.has(bone)),'every joint belongs to the independently cloned scene');
    assert.ok(skeleton.bones.every(bone=>!sourceObjects.has(bone)),'skeleton clones cannot reuse the cached source bones');
    assert.ok(skeleton.boneInverses.every(matrix=>finite(matrix.elements)));
    assert.ok(finite(mesh.bindMatrix.elements)&&finite(mesh.bindMatrixInverse.elements));
    const {position,skinIndex,skinWeight}=mesh.geometry.attributes;
    assert.ok(position&&skinIndex&&skinWeight);
    assert.equal(position.count,skinIndex.count);assert.equal(position.count,skinWeight.count);
    assert.equal(skinIndex.itemSize,4);assert.equal(skinWeight.itemSize,4);
    let minimum=Infinity,maximum=-Infinity,nonzero=0;
    for(let index=0;index<position.count;index++){
      let sum=0;
      for(let component=0;component<4;component++){
        const weight=skinWeight.getComponent(index,component),joint=skinIndex.getComponent(index,component);
        assert.ok(Number.isFinite(weight)&&weight>=-1e-7,'finite nonnegative skin weights');
        assert.ok(Number.isInteger(joint)&&joint>=0,'finite integer joint indices');
        if(weight>0){assert.ok(joint<skeleton.bones.length,'active joint index within its actual skeleton');nonzero++;}
        sum+=weight;
      }
      assert.ok(sum>0&&Math.abs(sum-1)<.001,'every vertex has normalized nonzero skin weights');
      minimum=Math.min(minimum,sum);maximum=Math.max(maximum,sum);
    }
    weights.push({mesh:mesh.name,vertices:position.count,joints:skeleton.bones.length,
      weightSumMin:minimum,weightSumMax:maximum,nonzeroInfluences:nonzero});
  }
  return {found,weights};
}

function evaluate(root,found,baseline=null){
  root.updateMatrixWorld(true);
  for(const bone of found.bones)assert.ok(finite(bone.matrixWorld.elements),'finite posed bone matrices');
  for(const skeleton of new Set(found.skins.map(mesh=>mesh.skeleton)))skeleton.update();
  const box=new Box3(),localPoints=[],worldPoints=[],point=new Vector3(),world=new Vector3(),delta=new Vector3(),linear=new Matrix3();
  let vertices=0,skinnedVertices=0,maxLocal=0,maxWorld=0,maxSkinScene=0,sumLocalSquared=0,sumSkinSceneSquared=0,moved=0;
  for(const mesh of found.meshes){
    assert.ok(finite(mesh.matrixWorld.elements),'finite posed mesh matrices');
    linear.setFromMatrix4(mesh.matrixWorld);
    const count=mesh.geometry.attributes.position.count;
    for(let index=0;index<count;index++){
      // Mesh.getVertexPosition includes authored morphs; the real skin is then
      // evaluated explicitly through Three's applyBoneTransform, without any
      // bindMatrix edits, skeleton.pose(), inverse-bind recalculation or baking.
      Mesh.prototype.getVertexPosition.call(mesh,index,point);
      if(mesh.isSkinnedMesh)mesh.applyBoneTransform(index,point);
      assert.ok(finite(point.toArray()),'finite deformed local vertices');
      world.copy(point).applyMatrix4(mesh.matrixWorld);
      assert.ok(finite(world.toArray()),'finite deformed world vertices');
      box.expandByPoint(world);vertices++;
      if(mesh.isSkinnedMesh){
        const offset=skinnedVertices*3;
        localPoints.push(point.x,point.y,point.z);worldPoints.push(world.x,world.y,world.z);
        if(baseline){
          delta.set(point.x-baseline.localPoints[offset],point.y-baseline.localPoints[offset+1],point.z-baseline.localPoints[offset+2]);
          const local=delta.length(),skinScene=delta.applyMatrix3(linear).length();
          const global=Math.hypot(world.x-baseline.worldPoints[offset],world.y-baseline.worldPoints[offset+1],world.z-baseline.worldPoints[offset+2]);
          maxLocal=Math.max(maxLocal,local);maxWorld=Math.max(maxWorld,global);
          maxSkinScene=Math.max(maxSkinScene,skinScene);
          sumLocalSquared+=local*local;sumSkinSceneSquared+=skinScene*skinScene;
          if(skinScene>baseline.motionThreshold)moved++;
        }
        skinnedVertices++;
      }
    }
  }
  assert.ok(!box.isEmpty()&&finite([...box.min.toArray(),...box.max.toArray()]));
  const dimensions=box.getSize(new Vector3()).toArray();
  return {vertices,skinnedVertices,bounds:{min:box.min.toArray(),max:box.max.toArray(),dimensions},
    localPoints,worldPoints,maxLocalSkinDisplacement:maxLocal,maxWorldDisplacement:maxWorld,
    maxSkinDisplacementInSceneUnits:maxSkinScene,
    rmsLocalSkinDisplacement:skinnedVertices?Math.sqrt(sumLocalSquared/skinnedVertices):0,
    rmsSkinDisplacementInSceneUnits:skinnedVertices?Math.sqrt(sumSkinSceneSquared/skinnedVertices):0,
    movedSkinnedVertices:moved,motionThreshold:baseline?.motionThreshold??Math.max(...dimensions)*1e-8};
}

function conciseFrame(time,sample){
  const {localPoints:unusedLocal,worldPoints:unusedWorld,...summary}=sample;
  void unusedLocal;void unusedWorld;
  return {timeSeconds:time,...summary};
}

function disposeSource(scene){
  const geometries=new Set(),materials=new Set(),skeletons=new Set();
  scene.traverse(object=>{
    if(object.geometry)geometries.add(object.geometry);
    if(object.skeleton)skeletons.add(object.skeleton);
    for(const material of Array.isArray(object.material)?object.material:[object.material])if(material)materials.add(material);
  });
  skeletons.forEach(skeleton=>skeleton.dispose());geometries.forEach(geometry=>geometry.dispose());materials.forEach(material=>material.dispose());
}

async function validate(entry){
  const started=performance.now(),warnings=[],errors=[];
  const originalWarn=console.warn,originalError=console.error;
  console.warn=(...args)=>warnings.push(args.map(value=>String(value)).join(' '));
  console.error=(...args)=>errors.push(args.map(value=>String(value)).join(' '));
  let gltf;
  try{
    assert.equal(entry.status,'validated');
    const publicRoot=path.resolve(ROOT,'frontend/public');
    const file=path.resolve(publicRoot,entry.url.replace(/^\/+/,''));
    assert.ok(file.startsWith(publicRoot+path.sep),'public URL stays in the public asset folder');
    const raw=readFileSync(file),digest=sha(raw);
    assert.equal(raw.length,entry.bytes);assert.equal(digest,entry.sha256);
    const delivery=deliveryChecks(entry,raw,digest);
    const memory=texturelessCopy(raw);
    gltf=await new GLTFLoader().parseAsync(memory.buffer.buffer.slice(memory.buffer.byteOffset,memory.buffer.byteOffset+memory.buffer.byteLength),'');
    const source=objects(gltf.scene),expectedJointCounts=memory.doc.skins.map(skin=>skin.joints.length);
    assert.ok(source.skins.length&&source.bones.length);
    assert.deepEqual(gltf.animations.map(clip=>clip.name).sort(),[...entry.animations].sort());
    assert.ok(gltf.animations.length>0);
    const originalInverseDigest=jsonSha(source.skins.map(mesh=>mesh.skeleton.boneInverses.map(matrix=>matrix.toArray())));
    const clips=[];let skinWeights;
    for(const clip of gltf.animations){
      assert.ok(clip.duration>0&&Number.isFinite(clip.duration));
      const scene=clone(gltf.scene),checked=skeletonChecks(scene,source.all,expectedJointCounts);
      skinWeights??=checked.weights;
      for(const track of clip.tracks){
        assert.ok(finite(track.times)&&finite(track.values),'finite clip samples');
        const binding=PropertyBinding.create(scene,track.name);binding.bind();
        assert.ok(binding.node&&binding.targetObject,'every clip track binds to a real target: '+track.name);
        binding.unbind();
      }
      const mixer=new AnimationMixer(scene),action=mixer.clipAction(clip);
      action.setLoop(LoopOnce,1);action.clampWhenFinished=true;action.play();
      const samples=[];let baseline;
      for(const time of TIMES){
        action.reset().play();
        mixer.setTime(time);
        const sample=evaluate(scene,checked.found,baseline);
        baseline??=sample;samples.push({...conciseFrame(time,sample),evaluatedClipTimeSeconds:action.time});
      }
      clips.push({name:clip.name,durationSeconds:clip.duration,tracks:clip.tracks.length,
        boundTracks:clip.tracks.length,samples,
        maxLocalSkinDisplacement:Math.max(...samples.map(sample=>sample.maxLocalSkinDisplacement)),
        maxSkinDisplacementInSceneUnits:Math.max(...samples.map(sample=>sample.maxSkinDisplacementInSceneUnits)),
        maxWorldDisplacement:Math.max(...samples.map(sample=>sample.maxWorldDisplacement))});
      mixer.stopAllAction();mixer.uncacheRoot(scene);
      for(const skeleton of new Set(checked.found.skins.map(mesh=>mesh.skeleton)))skeleton.dispose();
    }
    assert.equal(jsonSha(source.skins.map(mesh=>mesh.skeleton.boneInverses.map(matrix=>matrix.toArray()))),originalInverseDigest,'source inverse binds remain unchanged');
    const maxMotion=Math.max(...clips.map(clip=>clip.maxSkinDisplacementInSceneUnits));
    const threshold=Math.min(...clips.map(clip=>clip.samples[0].motionThreshold));
    assert.ok(maxMotion>threshold,'at least one authored clip must deform actual skinned vertices, beyond root movement');
    assert.equal(warnings.length,0,'no loader/skeleton/track-binding warnings');
    assert.equal(errors.length,0,'no loader/skeleton/track-binding errors');
    assert.equal(sha(readFileSync(file)),digest,'public GLB bytes remain unchanged after numerical QA');
    const reference=clips.find(clip=>clip.name===entry.referenceClip)??clips[0];
    const scale=entry.normalization?.uniformRootScale;
    const displayFrames=reference.samples.map(sample=>({timeSeconds:sample.timeSeconds,
      nativeYUpHeight:sample.bounds.dimensions[1],
      approximateDisplayHeight:Number.isFinite(scale)?sample.bounds.dimensions[1]*scale:null}));
    const target=entry.normalization?.displayHeightMeters??entry.height??null;
    return {id:entry.id,name:entry.name,status:'passed',url:entry.url,bytes:raw.length,sha256:digest,
      byteIdenticalToSource:delivery.byteIdenticalToSource,
      metadataOnlyAdaptation:delivery.metadataOnlyAdaptation,binIdentical:delivery.binIdentical,
      deliveryEvidence:delivery.evidence,inMemoryOnlyImageRemoval:memory.removed,
      skinAnimationGeometryDigest:memory.skinAnimationGeometryDigest,binChunksSha256:memory.binChunksSha256,
      sourceInverseBindsUnchanged:true,sourceFilesUnchanged:true,
      boneNodes:source.bones.length,skinnedMeshes:source.skins.length,serializedSkinJointCounts:expectedJointCounts,
      independentClonedBones:true,skinWeights,excludedNonSkinnedHelpers:source.helpers.map(object=>object.name),
      referenceClip:reference.name,approximatePresentationComparison:{blenderTargetHeight:target,
        blenderOuterRootScale:scale??null,threeFrames:displayFrames,
        firstFrameRelativeDifference:Number.isFinite(target)&&target>0&&displayFrames[0].approximateDisplayHeight!==null?
          (displayFrames[0].approximateDisplayHeight-target)/target:null,
        note:'Informational pose-dependent comparison only. Three samples seconds 0/0.3/0.6; Blender used a specific evaluated frame and its outer presentation root. No equality of normalized heights, frames or specimen dimensions is asserted.'},
      clips,maxLocalSkinDisplacement:Math.max(...clips.map(clip=>clip.maxLocalSkinDisplacement)),
      maxSkinDisplacementInSceneUnits:maxMotion,motionThreshold:threshold,warnings,errors,
      displacementUnits:{local:'Per-mesh authored coordinate units; scales can differ, so this is not a metric distance.',
        scene:'Native GLB world/scene units before the optional exterior Blender display scale; no physical specimen-size claim.',
        skinScene:'Local bone-deformation delta transformed by the current mesh linear world matrix, excluding root translation; used for the actual-deformation assertion.'},
      durationMs:Math.round(performance.now()-started)};
  }catch(error){
    return {id:entry.id,name:entry.name,status:'failed',error:error.stack??String(error),warnings,errors,durationMs:Math.round(performance.now()-started)};
  }finally{
    console.warn=originalWarn;console.error=originalError;
    if(gltf)disposeSource(gltf.scene);
  }
}

async function main(){
  // Retain the pre-adaptation numerical evidence once; later runs append to the
  // current log and never replace this historical checkpoint.
  if(existsSync(REPORT)&&!existsSync(PREVIOUS_REPORT))copyFileSync(REPORT,PREVIOUS_REPORT,constants.COPYFILE_EXCL);
  if(existsSync(LOG)&&!existsSync(PREVIOUS_LOG))copyFileSync(LOG,PREVIOUS_LOG,constants.COPYFILE_EXCL);
  log('RUN START — CPU-only GLTFLoader/SkeletonUtils; no public GLB mutation or browser APIs');
  const initial=readFileSync(ENTRIES),input=JSON.parse(initial.toString('utf8'));
  const entries=Array.isArray(input)?input:input.entries;
  assert.ok(Array.isArray(entries));
  const actual=entries.map(entry=>entry.id);
  assert.deepEqual([...actual].sort(),[...EXPECTED].sort(),'all six expected delivered fauna entries are required before complete QA');
  const results=[];
  for(const id of EXPECTED){
    log(`VALIDATING ${id}`);
    const result=await validate(entries.find(entry=>entry.id===id));results.push(result);
    log(`${result.status.toUpperCase()} ${id}: ${result.status==='passed'?`${result.skinnedMeshes} skinned meshes, ${result.boneNodes} bones, ${result.clips.length} clips, max skin deformation in native scene units ${result.maxSkinDisplacementInSceneUnits}`:result.error}`);
    console.log(JSON.stringify({id,status:result.status,skinnedMeshes:result.skinnedMeshes,bones:result.boneNodes,clips:result.clips?.length,maxSkinDisplacementInSceneUnits:result.maxSkinDisplacementInSceneUnits,error:result.status==='failed'?result.error:undefined}));
  }
  const entriesUnchanged=sha(readFileSync(ENTRIES))===sha(initial);
  const passed=results.filter(result=>result.status==='passed').length;
  const report={owner:OWNER,generatedAt:new Date().toISOString(),status:passed===6&&entriesUnchanged?'passed':'failed',
    expectedAssets:6,validatedAssets:results.length,passedAssets:passed,failedAssets:results.length-passed,
    entriesUnchangedDuringValidation:entriesUnchanged,entriesSha256:sha(initial),
    environment:{node:process.version,threeRevision:REVISION,platform:process.platform},
    method:{loader:'Three.js GLTFLoader',independentSkeletonClone:'SkeletonUtils.clone',
      animation:'AnimationMixer at seconds 0, 0.3 and 0.6 for every delivered clip',
      skinning:'Actual applyBoneTransform evaluation of every skinned vertex at each sample',
      images:'Images/textures/material references removed only from a reconstructed memory buffer; original BIN chunks and all skin/animation geometry metadata retained',
      fileEdits:'Only this QA script, its JSON report and append-only log; no public GLB, source asset, manifest, runtime or city modification',
      bounds:'Full finite deformed vertex bounds, excluding named non-skinned importer helper spheres',
      presentation:'Blender outer-root height comparison is approximate and pose-dependent, never an assertion of equivalent normalized frames'},
    preservedPreviousResults:{report:PREVIOUS_REPORT,log:PREVIOUS_LOG},
    results};
  writeFileSync(REPORT,JSON.stringify(report,null,2)+'\n','utf8');
  log(`RUN END ${report.status.toUpperCase()} ${passed}/6; entries stable=${entriesUnchanged}`);
  console.log(JSON.stringify({status:report.status,passedAssets:passed,expectedAssets:6,report:REPORT,log:LOG}));
  if(report.status!=='passed')process.exitCode=1;
}

main().catch(error=>{
  const report={owner:OWNER,generatedAt:new Date().toISOString(),status:'not_complete',expectedAssets:6,error:error.stack??String(error)};
  writeFileSync(REPORT,JSON.stringify(report,null,2)+'\n','utf8');log(report.error);console.error(report.error);process.exitCode=1;
});
