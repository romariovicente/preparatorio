import {assetUrl} from '../config/deploymentConfig.js';
import { AnimationMixer, Box3, LoopOnce, MathUtils, Vector3 } from 'three';

export const HOSPITAL_ASSET_URL = assetUrl('/assets/environments/ENV_Hospital_Reception_Module_20261015.glb');
export const PUBLIC_DOOR_PREFIX = 'HSP15_DOOR_PUBLIC';
export const ROOF_PREFIX = 'HSP15_ROOF_';

export function hasNamedAncestor(object, prefix) {
  for (let current = object; current; current = current.parent) {
    if (current.name?.startsWith(prefix)) return true;
  }
  return false;
}

export function inspectHospitalModel(scene, animations) {
  const roofNodes = [];
  const triageWaypoints = [];
  let meshCount = 0;
  let hasPublicDoor = false;
  scene.updateMatrixWorld(true);
  scene.traverse(object => {
    if (object.name.startsWith(ROOF_PREFIX)) roofNodes.push(object);
    if (object.name.startsWith(PUBLIC_DOOR_PREFIX)) hasPublicDoor = true;
    const triage = object.name.match(/^HSP15_WAYPOINT_TRIAGE_(01|02)$/);
    if (triage) triageWaypoints.push({ id: triage[1], label: `Triagem ${triage[1]}`, position: object.getWorldPosition(new Vector3()).toArray() });
    if (object.isMesh) {
      meshCount += 1;
      object.castShadow = true;
      object.receiveShadow = true;
    }
  });
  const bounds = new Box3().setFromObject(scene);
  if (meshCount === 0 || bounds.isEmpty()) throw new Error('O arquivo não contém um módulo visível.');
  return {
    bounds,
    roofNodes,
    triageWaypoints,
    doorClips: hasPublicDoor ? animations.filter(clip => clip.name.startsWith('Door_Open') && clip.duration > 0) : [],
    roomClips: animations.filter(clip => clip.name.startsWith('Room_Open_') && clip.duration > 0),
    size: bounds.getSize(new Vector3()),
  };
}

// Evaluate the exported clip at an explicit time so a partially opened door can
// reverse smoothly without restarting, including after reaching either end.
export function createDoorController(scene, clips) {
  if (!clips?.length) return null;
  const mixer = new AnimationMixer(scene);
  const duration = Math.max(...clips.map(clip => clip.duration));
  const actions = clips.map(clip => {
    const action = mixer.clipAction(clip);
    action.setLoop(LoopOnce, 1);
    action.clampWhenFinished = true;
    action.play();
    action.paused = true;
    return action;
  });
  let time = 0;
  function update(open, delta) {
    const target = open ? duration : 0;
    time = MathUtils.clamp(time + Math.sign(target - time) * Math.min(delta, Math.abs(target - time)), 0, duration);
    actions.forEach(action => { action.time = Math.min(time, action.getClip().duration); });
    mixer.update(0);
    return time;
  }
  update(false, 0);
  return {
    update,
    dispose() {
      mixer.stopAllAction();
      mixer.uncacheRoot(scene);
    },
  };
}

export function disposeHospitalModel(scene) {
  const geometries = new Set();
  const materials = new Set();
  const textures = new Set();
  scene.traverse(object => {
    if (object.geometry) geometries.add(object.geometry);
    for (const material of (Array.isArray(object.material) ? object.material : [object.material])) {
      if (!material) continue;
      materials.add(material);
      for (const value of Object.values(material)) if (value?.isTexture) textures.add(value);
    }
  });
  textures.forEach(texture => texture.dispose());
  materials.forEach(material => material.dispose());
  geometries.forEach(geometry => geometry.dispose());
}
