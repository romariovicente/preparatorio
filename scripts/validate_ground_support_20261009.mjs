import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync, writeFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {Box3, Matrix3, Raycaster, Vector3} from '../frontend/node_modules/three/build/three.module.js';
import {loadTexturelessGLB} from './actual_asset_inspection.mjs';
import {collectGroundSurfaces, sampleGroundHeight} from '../frontend/src/cyber/groundSupport.js';

const source = new URL('../frontend/public/assets/cyber/ENV_Arapiraca_RealMaterials_v3_20261005.glb', import.meta.url);
const hash = () => createHash('sha256').update(readFileSync(source)).digest('hex');
const sourceHash = hash();
const {scene} = await loadTexturelessGLB(source);
const surfaces = collectGroundSurfaces(scene), ray = new Raycaster();
const points = [
  {label:'Reported curb overlap', position:{x:-.68,y:0,z:23.93}, expectedCenter:.01, expectedFootprint:.23},
  {label:'Flat plaza away from curb', position:{x:-.68,y:0,z:23}, expectedCenter:.01, expectedFootprint:.01},
  {label:'Sidewalk centre', position:{x:-.68,y:0,z:24.3}, expectedCenter:.23, expectedFootprint:.23},
];
const samples = points.map(point => {
  const center = sampleGroundHeight(ray, surfaces, point.position, {radius:0});
  const footprint = sampleGroundHeight(ray, surfaces, point.position);
  assert.ok(Math.abs(center - point.expectedCenter) < 1e-6, `${point.label}: centre height`);
  assert.ok(Math.abs(footprint - point.expectedFootprint) < 1e-6, `${point.label}: footprint height`);
  return {...point, center, footprint};
});
const underground = surfaces.find(mesh => mesh.name.startsWith('BLD_UndergroundInterior_Floor'));
assert.ok(underground, 'the actual city contains an underground floor');
const bounds = new Box3().setFromObject(underground), center = bounds.getCenter(new Vector3());
const undergroundPosition = {x:center.x,y:bounds.max.y,z:center.z};
const undergroundHeight = sampleGroundHeight(ray, surfaces, undergroundPosition);
assert.ok(Math.abs(undergroundHeight - bounds.max.y) < 1e-6, 'ground depth does not sink onto the inverted floor underside');
ray.set(new Vector3(center.x, bounds.max.y + .41, center.z), new Vector3(0,-1,0));
const undergroundHit = ray.intersectObject(underground, false)[0];
const undergroundNormal = undergroundHit.face.normal.clone()
  .applyMatrix3(new Matrix3().getNormalMatrix(underground.matrixWorld)).normalize();
assert.ok(undergroundNormal.y < 0, 'record the inverted winding in the unchanged legacy source floor');
assert.equal(hash(), sourceHash, 'the source environment remains unchanged');
const report = {
  date:'2026-10-09',
  source:fileURLToPath(source),
  sourceSha256:sourceHash,
  sourceUnchanged:true,
  method:'Actual unchanged city GLB, CPU mesh/ray intersections, runtime groundSupport helper; no browser or Blender mutation.',
  eligibleSurfaces:surfaces.length,
  samples,
  underground:{name:underground.name,position:undergroundPosition,height:undergroundHeight,
    topWorldNormal:undergroundNormal.toArray(),fallbackToBaseline:true,
    note:'The unchanged legacy GLB has inverted top winding. The helper rejects it and its occluded underside, preserving the baseline. Source floor normal repair remains separate work.'},
  actualRemyClipInspection:'reports/remy_ground_diagnostic_20261009.json',
  passed:true,
};
const target = new URL('../reports/ground_support_validation_20261009.json', import.meta.url);
writeFileSync(target, JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify(report, null, 2));
