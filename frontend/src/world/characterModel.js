import {Box3, Group, Vector3} from 'three';
import {clone} from 'three/addons/utils/SkeletonUtils.js';

// Normalization belongs to wrappers: an authored root position can be animated.
// Bone and mesh bounds are refreshed only on the independent skeleton copy.
export function isCharacterHelper(object) {
  if(!object.isMesh||object.isSkinnedMesh)return false;
  const name=(object.userData.asset_node_name??object.name).normalize('NFKD').replace(/[\u0300-\u036f]/g,'').replace(/[^a-z0-9]/gi,'').toLowerCase();
  return /^(icosphere|esferaicosaedrica)(?:\d+)?(?:mesh)?$/.test(name);
}

export function createCharacterClone(source, height) {
  const scene = clone(source), offset = new Group(), group = new Group();
  offset.add(scene); group.add(offset);
  scene.updateMatrixWorld(true);
  scene.traverse(object => {
    if (!object.isMesh) return;
    if(isCharacterHelper(object)){
      object.visible=false;
      object.userData.characterHelper=true;
      return;
    }
    object.castShadow = true; object.receiveShadow = true;
    if (object.isSkinnedMesh) {
      object.frustumCulled = false;
      object.skeleton.update();
      object.computeBoundingBox(); object.computeBoundingSphere();
    }
  });
  // Three's setFromObject includes invisible helpers. Only the character's
  // meshes define human scale; the auxiliary sphere remains preserved in cache.
  const box = new Box3();
  scene.traverse(object=>{if(object.isMesh&&!isCharacterHelper(object))box.expandByObject(object,true);});
  const size = box.getSize(new Vector3()), center = box.getCenter(new Vector3());
  if (height > 0 && !box.isEmpty() && Number.isFinite(size.y) && size.y > .001) {
    offset.position.set(-center.x, -box.min.y, -center.z);
    group.scale.setScalar(height / size.y);
  }
  group.updateMatrixWorld(true);
  return {group, scene, offset, authoredBounds: box};
}

export function findCharacterAction(actions, requested = 'Idle') {
  const find = name => actions[name] || Object.entries(actions)
    .find(([key]) => key.toLowerCase() === name.toLowerCase()
      || key.toLowerCase().endsWith(`|${name.toLowerCase()}`))?.[1];
  return find(requested) || find('Idle') || Object.values(actions)[0];
}

// A non-playing NPC still needs an authored pose. Stopping every action exposes
// the export bind/T pose; a paused Idle action keeps the hands at the sides.
export function startCharacterAction(action, mixer, playing) {
  if (!action) return;
  action.reset().setEffectiveWeight(1).play();
  action.paused = !playing;
  mixer.update(0);
}
