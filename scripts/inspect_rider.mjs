import {createHash} from 'node:crypto';
import {readFileSync,writeFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {createSeatedClone} from '../frontend/src/cyber/seating.js';
import {finiteDeformedVertices,joint,loadTexturelessGLB,localTransformSnapshot,synchronizeSkinnedBounds} from './actual_asset_inspection.mjs';

const path=new URL('../frontend/public/assets/characters/CHR_Remy_Mixamo_20261005.glb',import.meta.url);
const catalog=JSON.parse(readFileSync(new URL('../frontend/src/config/mixamoAssets.json',import.meta.url)));
const expectedHash=catalog.find(asset=>asset.id==='CHR_Remy_Mixamo_20261005').sha256;
const sourceHash=createHash('sha256').update(readFileSync(path)).digest('hex');
const {scene}=await loadTexturelessGLB(path),original=localTransformSnapshot(scene);
const positions={seated:[0,.48,0],riding:[0,.94,-.4]};
const cases={};
for(const [mode,position] of Object.entries(positions)){
  const pose=createSeatedClone(scene,1.7,mode==='riding');
  pose.group.position.set(position[0],position[1]+pose.offset,position[2]);
  const bounds=synchronizeSkinnedBounds(pose.group);
  const joints={};
  for(const name of ['Hips','Spine','Spine2','LeftUpLeg','LeftLeg','LeftFoot','RightUpLeg','RightLeg','RightFoot','LeftArm','LeftForeArm','LeftHand','RightArm','RightForeArm','RightHand'])joints[name]=joint(pose.group,name).toArray();
  let clonedSkinCount=0,sourceSkinCount=0,sharedSkeletonBones=0;
  const sourceBones=new Set();scene.traverse(object=>{if(object.isBone)sourceBones.add(object);if(object.isSkinnedMesh)sourceSkinCount++;});
  pose.group.traverse(object=>{if(object.isSkinnedMesh){clonedSkinCount++;sharedSkeletonBones+=object.skeleton.bones.filter(bone=>sourceBones.has(bone)).length;}});
  cases[mode]={posed:pose.posed,mountPosition:position,offset:pose.offset,scale:pose.group.scale.toArray(),bounds:[bounds.min.toArray(),bounds.max.toArray()],joints,deformedVertexCount:finiteDeformedVertices(pose.group),skinClone:{sourceSkinCount,clonedSkinCount,sharedSkeletonBones},checks:{sourceTransformsUnchanged:JSON.stringify(original)===JSON.stringify(localTransformSnapshot(scene)),boundsFinite:[...bounds.min.toArray(),...bounds.max.toArray()].every(Number.isFinite),hipsAboveSeat:joints.Hips[1]>position[1],anklesAboveFloor:joints.LeftFoot[1]>0&&joints.RightFoot[1]>0,armsForward:joints.LeftHand[2]>joints.LeftArm[2]&&joints.RightHand[2]>joints.RightArm[2],kneesForward:joints.LeftLeg[2]>joints.LeftUpLeg[2]&&joints.RightLeg[2]>joints.RightUpLeg[2]}};
}
const report={date:'2026-10-08',asset:{path:fileURLToPath(path),sha256:sourceHash,validatedOriginalUnchanged:sourceHash===expectedHash},method:'Real GLB parsed with GLTFLoader in CPU-only mode; textures omitted in memory; original vertex/joint/skin data preserved; exact deformed vertex bounds',cases,sourceTransformsUnchanged:JSON.stringify(original)===JSON.stringify(localTransformSnapshot(scene)),limits:['FK pose validation verifies real skin and bone transforms, finite bounds and basic contact; it does not certify precise fingers gripping the handlebar.','Clothing and tank collision still require per-character visual fitting.','Bench shoes extend approximately 1.7cm below the floor with the provisional FK pose at a 0.48m bench; ankle joints are above the floor.','Seated runtime pose is derived from Remy original rig; source GLB and animation clips are not edited.']};
writeFileSync(new URL('../reports/rider_actual_validation_20261008.json',import.meta.url),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report,null,2));
