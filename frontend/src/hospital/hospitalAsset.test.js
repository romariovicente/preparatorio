import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { createDoorController, disposeHospitalModel, inspectHospitalModel } from './hospitalModel.js';

const assetPath = new URL('../../public/assets/environments/ENV_Hospital_Reception_Module_20261015.glb', import.meta.url);

test('delivered hospital GLB keeps metre scale, named inspection targets and reversible exported doors', { skip: !existsSync(assetPath) }, async () => {
  const data = readFileSync(assetPath);
  const gltf = await new GLTFLoader().parseAsync(data.buffer.slice(data.byteOffset, data.byteOffset + data.byteLength), '');
  const info = inspectHospitalModel(gltf.scene, gltf.animations);
  const publicDoor = createDoorController(gltf.scene, info.doorClips);
  const rooms = createDoorController(gltf.scene, info.roomClips);
  try {
    assert.ok(info.size.x > 35 && info.size.x < 38, '36 metre wide module must retain its original scale');
    assert.ok(info.size.y > 4 && info.size.y < 6);
    assert.ok(info.size.z > 23 && info.size.z < 31);
    assert.ok(info.roofNodes.length > 0);
    assert.deepEqual(info.triageWaypoints.map(point => point.id).sort(), ['01', '02']);
    assert.ok(publicDoor, 'public door must have an exported Door_Open clip');
    const left = gltf.scene.getObjectByName('HSP15_DOOR_PUBLIC_Left');
    const right = gltf.scene.getObjectByName('HSP15_DOOR_PUBLIC_Right');
    assert.ok(left && right);
    publicDoor.update(false, 2);
    const closed = [left.position.toArray(), right.position.toArray()];
    publicDoor.update(true, 2);
    assert.ok(left.position.x < closed[0][0] - 1);
    assert.ok(right.position.x > closed[1][0] + 1);
    for (const [index, leaf] of [left, right].entries()) {
      assert.equal(leaf.position.y, closed[index][1], 'sliding leaves must stay at the same height');
      assert.equal(leaf.position.z, closed[index][2], 'sliding leaves must stay in the facade plane');
    }
    publicDoor.update(false, 2);
    assert.deepEqual([left.position.toArray(), right.position.toArray()], closed);
    publicDoor.update(true, 0.5);
    publicDoor.update(false, 0.5);
    assert.deepEqual([left.position.toArray(), right.position.toArray()], closed);
    assert.equal(info.roomClips.length, 4);
    const hinges = Array.from({ length: 4 }, (_, index) => gltf.scene.getObjectByName(`HSP15_DOOR_ROOM_0${index + 1}_HINGE`));
    assert.ok(hinges.every(Boolean));
    const roomClosed = hinges.map(hinge => hinge.quaternion.clone());
    rooms.update(true, 2);
    hinges.forEach((hinge, index) => assert.ok(hinge.quaternion.angleTo(roomClosed[index]) > 1.5));
    rooms.update(false, 2);
    hinges.forEach((hinge, index) => assert.ok(hinge.quaternion.angleTo(roomClosed[index]) < 0.00001));
  } finally {
    publicDoor?.dispose();
    rooms?.dispose();
    disposeHospitalModel(gltf.scene);
  }
});
