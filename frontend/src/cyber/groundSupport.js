import {Matrix3, Vector3} from 'three';

const down = new Vector3(0, -1, 0);
const footprint = [[0, 0], ...Array.from({length:8}, (_, index) => {
  const angle = index * Math.PI / 4;
  return [Math.cos(angle), Math.sin(angle)];
})];

// Authored ground and explicit walkable floors only. Furniture, roofs and
// vehicles do not become ground merely because the ray intersects them.
export function isWalkableSurface(object) {
  if (!object?.isMesh) return false;
  const name = object.name ?? '';
  return Boolean(object.userData?.walkable
    || name.startsWith('ENV_ARAP_Base')
    || name.startsWith('ENV_ARAP_UrbanPlate')
    || name.startsWith('UNDERGROUND_Floor')
    || name.startsWith('BLD_UndergroundInterior_Floor')
    || name.startsWith('ROAD_') && !/white|Centre|MARK/i.test(name));
}

export function collectGroundSurfaces(scene) {
  const surfaces = [];
  scene.updateWorldMatrix(true, true);
  scene.traverse(object => { if (isWalkableSurface(object)) surfaces.push(object); });
  return surfaces;
}

function ancestorsVisible(object) {
  for (let parent = object; parent; parent = parent.parent) {
    if (parent.visible === false) return false;
  }
  return true;
}

// A centre-only ray can miss a curb while animated shoes already overlap it.
// Support the small footprint without moving bones or editing source clips.
export function sampleGroundHeight(ray, surfaces, position, {radius=.32, maxStep=.4, maxDrop=.4}={}) {
  const baseline = Number.isFinite(position?.y) ? position.y : 0;
  if (!Number.isFinite(position?.x) || !Number.isFinite(position?.z)) return baseline;
  const reach = Math.max(0, radius), rise = Math.max(0, maxStep), drop = Math.max(0, maxDrop);
  const origin = new Vector3(), normal = new Vector3(), normalMatrix = new Matrix3();
  const savedNear = ray.near, savedFar = ray.far;
  let height = null;
  ray.near = 0;
  ray.far = rise + drop + .02;
  try {
    for (const [x, z] of reach ? footprint : footprint.slice(0, 1)) {
      origin.set(position.x + x * reach, baseline + rise + .01, position.z + z * reach);
      ray.set(origin, down);
      const encountered = new Set();
      for (const hit of ray.intersectObjects(surfaces, false)) {
        if (!hit.face || !ancestorsVisible(hit.object)) continue;
        // Never stand on a deeper face behind a rejected top face. Some legacy
        // double-sided floors have inverted winding; their bottom is not ground.
        if (encountered.has(hit.object)) continue;
        encountered.add(hit.object);
        const y = hit.point.y;
        if (y > baseline + rise + .000001 || y < baseline - drop - .000001) continue;
        normalMatrix.getNormalMatrix(hit.object.matrixWorld);
        normal.copy(hit.face.normal).applyMatrix3(normalMatrix).normalize();
        if (normal.y < .55) continue;
        if (height === null || y > height) height = y;
      }
    }
  } finally {
    ray.near = savedNear;
    ray.far = savedFar;
  }
  return height ?? baseline;
}
