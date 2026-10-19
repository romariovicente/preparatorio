import { Quaternion, Vector3 } from 'three';
import {createCharacterClone} from '../world/characterModel.js';

function pointBoneAt(bone, child, direction, scene) {
  scene.updateMatrixWorld(true);
  const from = bone.getWorldPosition(new Vector3()), to = child.getWorldPosition(new Vector3());
  const current = to.sub(from).normalize();
  if (!current.lengthSq()) return;
  const delta = new Quaternion().setFromUnitVectors(current,direction);
  const target = delta.multiply(bone.getWorldQuaternion(new Quaternion()));
  const parent = bone.parent?.getWorldQuaternion(new Quaternion()) ?? new Quaternion();
  bone.quaternion.copy(parent.invert().multiply(target));
  scene.updateMatrixWorld(true);
}

// The pose is applied only to a SkeletonUtils copy, preserving cached GLB data.
// It is a provisional FK seating pose; per-character clothing still needs fitting.
export function createSeatedClone(source, height = 1.7, riding = false) {
  const {scene,group} = createCharacterClone(source,height);
  const bones = [];
  scene.traverse(object => { if (object.isBone) bones.push(object); });
  const findLegBone = (side, part) => {
    const mixamoSide = side === 'L' ? 'left' : 'right';
    const mixamoPart = { thigh:'upleg', shin:'leg', foot:'foot' }[part];
    return bones.find(bone => bone.name === `${side}_${part}`)
      ?? bones.find(bone => bone.name.replace(/[^a-z]/gi,'').toLowerCase().endsWith(`${mixamoSide}${mixamoPart}`));
  };
  let posed = false;
  for (const side of ['L','R']) {
    const thigh = findLegBone(side,'thigh');
    const shin = findLegBone(side,'shin');
    const foot = findLegBone(side,'foot');
    if (!thigh || !shin || !foot) continue;
    pointBoneAt(thigh,shin,new Vector3(riding?(side==='L'?.24:-.24):0,riding?-.12:0,1).normalize(),group);
    pointBoneAt(shin,foot,new Vector3(0,-1,0),group);
    posed = true;
  }
  if(riding){
    const spine=bones.find(b=>b.name.replace(/[^a-z]/gi,'').toLowerCase().endsWith('spine'));
    const chest=bones.find(b=>b.name.replace(/[^a-z0-9]/gi,'').toLowerCase().endsWith('spine1'));
    if(spine&&chest)pointBoneAt(spine,chest,new Vector3(0,.85,.53).normalize(),group);
  }
  for(const side of ['Left','Right']){
    const find=part=>bones.find(b=>b.name.replace(/[^a-z]/gi,'').toLowerCase().endsWith(`${side}${part}`.toLowerCase()));
    const upper=find('Arm'),lower=find('ForeArm'),hand=find('Hand');
    if(upper&&lower&&hand){
      pointBoneAt(upper,lower,new Vector3(side==='Left'?.12:-.12,riding?-.35:-.7,riding?.94:.7).normalize(),group);
      pointBoneAt(lower,hand,new Vector3(0,-.14,1).normalize(),group);
    }
  }
  group.updateMatrixWorld(true);
  group.traverse(object=>{if(object.isSkinnedMesh){object.skeleton.update();object.computeBoundingBox();object.computeBoundingSphere();}});
  const hips=bones.find(b=>b.name.replace(/[^a-z]/gi,'').toLowerCase().endsWith('hips'));
  const offset=posed&&hips?.getWorldPosition(new Vector3()).y>.2 ? .06-hips.getWorldPosition(new Vector3()).y : posed?-.82:-.45;
  return { group, posed, offset };
}
