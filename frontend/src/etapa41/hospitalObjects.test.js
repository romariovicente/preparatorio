import test from 'node:test';
import assert from 'node:assert/strict';
import { HOSPITAL_START, hospitalPlacementAllowed, hospitalTemplates, readHospitalLayout, routeToHospitalObject, stepHospitalPlayer, writeHospitalLayout } from './hospitalObjects.js';

test('hospital walking and furniture placement respect beds, desk and room boundaries', () => {
  assert.equal(hospitalPlacementAllowed([-2.8, 0, -1.6]), false);
  assert.equal(hospitalPlacementAllowed([2.8, 0, 1.6]), false);
  assert.equal(hospitalPlacementAllowed([5, 0, 0]), false);
  assert.equal(hospitalPlacementAllowed([NaN, 0, 2]), false);
  assert.equal(hospitalPlacementAllowed([0, 0, 2.8], [0.9, 0.75]), true);
  const position = [-2.8, 0, 0.2];
  assert.deepEqual(stepHospitalPlayer(position, [0, -1]), position);
  const furniture = hospitalTemplates.filter(t => t.movable);
  const route = routeToHospitalObject(HOSPITAL_START, hospitalTemplates[0].position, furniture);
  assert.ok(route?.length > 0);
  assert.ok(route.every(p => hospitalPlacementAllowed(p, [0.5, 0.5], furniture)));
  assert.ok(Math.hypot(route.at(-1)[0] - 3.5, route.at(-1)[2] - 1.7) <= 1.45);
});

test('hospital layout restores only validated authored furniture ids and safe positions', () => {
  let stored = JSON.stringify({ version: 1, positions: { hospital_cart: [0, 99, 2.9], hospital_chair: [-2.8, 0, -1.6], unknown: [0, 0, 0] } });
  const storage = { getItem: () => stored, setItem: (_, value) => { stored = value; } };
  const layout = readHospitalLayout(storage);
  assert.deepEqual(layout.hospital_cart, [0, 0, 2.9]);
  assert.deepEqual(layout.hospital_chair, [-3.9, 0, 1.25]);
  assert.equal(layout.unknown, undefined);
  assert.equal(writeHospitalLayout(storage, layout), true);
  assert.deepEqual(readHospitalLayout(storage), layout);
  assert.equal(writeHospitalLayout({ setItem() { throw new Error('unavailable'); } }, layout), false);
});
