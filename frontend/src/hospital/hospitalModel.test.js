import test from 'node:test';
import assert from 'node:assert/strict';
import { AnimationClip, BoxGeometry, Group, Mesh, MeshStandardMaterial, VectorKeyframeTrack } from 'three';
import { createDoorController, hasNamedAncestor, inspectHospitalModel } from './hospitalModel.js';

function fixture() {
  const scene = new Group();
  const leaf = new Mesh(new BoxGeometry(1, 2, 0.1), new MeshStandardMaterial());
  leaf.name = 'HSP15_DOOR_PUBLIC_Left';
  const roof = new Mesh(new BoxGeometry(36, 0.2, 24), new MeshStandardMaterial());
  roof.name = 'HSP15_ROOF_Main';
  roof.position.y = 4.2;
  scene.add(leaf, roof);
  const clip = new AnimationClip('Door_Open', 1, [new VectorKeyframeTrack(`${leaf.name}.position`, [0, 1], [0, 0, 0, -1.2, 0, 0])]);
  return { scene, leaf, roof, clip };
}

test('detects the public door from nested clicked meshes and preserves metre scale', () => {
  const { scene, leaf, roof, clip } = fixture();
  const glass = new Mesh();
  leaf.add(glass);
  assert.equal(hasNamedAncestor(glass, 'HSP15_DOOR_PUBLIC'), true);
  assert.equal(hasNamedAncestor(roof, 'HSP15_DOOR_PUBLIC'), false);
  const info = inspectHospitalModel(scene, [clip]);
  assert.deepEqual(info.doorClips, [clip]);
  assert.deepEqual(info.roofNodes, [roof]);
  assert.equal(info.size.x, 36);
  assert.equal(info.size.z, 24);
  assert.deepEqual(scene.scale.toArray(), [1, 1, 1]);
});

test('door opens, reverses midway, closes fully and opens again', () => {
  const { scene, leaf, clip } = fixture();
  const controller = createDoorController(scene, [clip]);
  controller.update(true, 0.5);
  assert.ok(Math.abs(leaf.position.x + 0.6) < 0.00001);
  controller.update(false, 0.25);
  assert.ok(Math.abs(leaf.position.x + 0.3) < 0.00001);
  controller.update(false, 2);
  assert.equal(leaf.position.x, 0);
  controller.update(true, 2);
  assert.ok(Math.abs(leaf.position.x + 1.2) < 0.00001);
  controller.update(false, 2);
  assert.equal(leaf.position.x, 0);
  controller.update(true, 2);
  assert.ok(Math.abs(leaf.position.x + 1.2) < 0.00001);
  controller.dispose();
});

test('unavailable animation leaves the door control unavailable', () => {
  const { scene } = fixture();
  assert.deepEqual(inspectHospitalModel(scene, []).doorClips, []);
  assert.equal(createDoorController(scene, null), null);
  assert.throws(() => inspectHospitalModel(new Group(), []), /módulo visível/);
});

test('separate Door_Open clips animate both leaves at the same time', () => {
  const { scene, leaf, clip } = fixture();
  clip.name = 'Door_Open_Left';
  const right = leaf.clone();
  right.name = 'HSP15_DOOR_PUBLIC_Right';
  scene.add(right);
  const rightClip = new AnimationClip('Door_Open_Right', 1, [new VectorKeyframeTrack(`${right.name}.position`, [0, 1], [0, 0, 0, 1.2, 0, 0])]);
  const info = inspectHospitalModel(scene, [clip, rightClip]);
  assert.equal(info.doorClips.length, 2);
  const controller = createDoorController(scene, info.doorClips);
  controller.update(true, 1);
  assert.ok(Math.abs(leaf.position.x + 1.2) < 0.00001);
  assert.ok(Math.abs(right.position.x - 1.2) < 0.00001);
  controller.update(false, 1);
  assert.equal(leaf.position.x, 0);
  assert.equal(right.position.x, 0);
  controller.dispose();
});
