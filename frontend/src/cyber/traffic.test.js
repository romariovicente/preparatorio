import test from 'node:test';
import assert from 'node:assert/strict';
import { Group, Mesh, MeshStandardMaterial, SphereGeometry } from 'three';
import { createTrafficLightController, sampleTraffic, trafficLampDescriptor, TRAFFIC_CYCLE_SECONDS, TRAFFIC_PHASES } from './traffic.js';

test('all 60fps samples of two cycles avoid vehicle and pedestrian conflicts', () => {
  for (let frame = 0; frame <= TRAFFIC_CYCLE_SECONDS * 60 * 2; frame += 1) {
    const state = sampleTraffic(frame / 60);
    assert.ok(!(state.ns === 'green' && state.ew === 'green'), `two greens at ${frame}`);
    assert.ok(!(state.ns !== 'red' && state.ew !== 'red'), `two vehicle rights at ${frame}`);
    if (state.pedNs !== 'red' || state.pedEw !== 'red') {
      assert.equal(state.ns, 'red', `NS conflicts with pedestrian at ${frame}`);
      assert.equal(state.ew, 'red', `EW conflicts with pedestrian at ${frame}`);
    }
  }
});

test('stage boundaries preserve green-yellow-red, intergreen and pedestrian clearance', () => {
  let boundary = 0;
  const phases = [];
  for (const stage of TRAFFIC_PHASES) {
    assert.ok(stage.duration > 0);
    const atStart = sampleTraffic(boundary);
    const beforeEnd = sampleTraffic(boundary + stage.duration - 1e-6);
    assert.equal(atStart.phase, stage.id);
    assert.equal(beforeEnd.phase, stage.id);
    assert.equal(atStart.phaseElapsed, 0);
    assert.ok(beforeEnd.phaseRemaining > 0);
    phases.push(atStart.phase);
    boundary += stage.duration;
  }
  assert.deepEqual(phases, ['NS_GREEN', 'NS_YELLOW', 'CLEAR_NS', 'EW_GREEN', 'EW_YELLOW', 'CLEAR_EW', 'PEDESTRIAN_GREEN', 'PEDESTRIAN_CLEAR', 'CLEAR_PEDESTRIAN']);
  assert.equal(sampleTraffic(boundary).phase, 'NS_GREEN');
  const beforePedestrian = sampleTraffic(45.999);
  assert.equal(beforePedestrian.phase, 'CLEAR_EW');
  assert.deepEqual([beforePedestrian.ns, beforePedestrian.ew, beforePedestrian.pedNs], ['red', 'red', 'red']);
  assert.equal(sampleTraffic(46).pedNs, 'green');
  assert.equal(sampleTraffic(56).pedNs, 'flashing-red');
  assert.equal(sampleTraffic(62).pedNs, 'red');
  assert.equal(sampleTraffic(63.999).ns, 'red');
  assert.equal(sampleTraffic(64).ns, 'green');
});

test('shared cycle remains periodic for long, negative and invalid elapsed values', () => {
  for (const elapsed of [0, 10.25, 18, 23, 46, 56.5, 63.5]) {
    assert.deepEqual(sampleTraffic(elapsed), sampleTraffic(elapsed + TRAFFIC_CYCLE_SECONDS * 100));
  }
  assert.deepEqual(sampleTraffic(-0.5), sampleTraffic(TRAFFIC_CYCLE_SECONDS - 0.5));
  for (const invalid of [NaN, Infinity, -Infinity, undefined, '18']) {
    assert.deepEqual(sampleTraffic(invalid), sampleTraffic(0));
  }
});

test('bulb names accept Blender duplicates and distinguish pedestrian heads', () => {
  assert.deepEqual(trafficLampDescriptor('TRAFFIC_J2_NS_G.001'), { junction: 2, pedestrian: false, axis: 'NS', signal: 'G' });
  assert.deepEqual(trafficLampDescriptor('TRAFFIC_J2_PED_EW_R_001'), { junction: 2, pedestrian: true, axis: 'EW', signal: 'R' });
  assert.equal(trafficLampDescriptor('TRAFFIC_Housing'), null);
  assert.equal(trafficLampDescriptor('TRAFFIC_J2_PED_NS_Y'), null);
  assert.equal(trafficLampDescriptor('AD_TRAFFIC_J2_NS_G'), null);
});

test('real Three materials isolate cached scenes, light every stage and restore on dispose', () => {
  const scene = new Group(), geometry = new SphereGeometry(.2, 4, 4);
  const source = new MeshStandardMaterial({ color: 0xdddddd, emissive: 0x332211, emissiveIntensity: .3 });
  const bulbs = new Map();
  for (const name of ['TRAFFIC_J1_NS_R', 'TRAFFIC_J1_NS_Y', 'TRAFFIC_J1_NS_G', 'TRAFFIC_J1_EW_R', 'TRAFFIC_J1_EW_G', 'TRAFFIC_J1_PED_NS_R', 'TRAFFIC_J1_PED_NS_G']) {
    const bulb = new Mesh(geometry, source); bulb.name = name; scene.add(bulb); bulbs.set(name, bulb);
  }
  const advertisement = new Mesh(geometry, source); advertisement.name = 'PROP_Neon'; scene.add(advertisement);
  const controller = createTrafficLightController(scene);
  assert.equal(controller.bulbCount, 7);
  assert.equal(advertisement.material, source);
  const isolated = bulbs.get('TRAFFIC_J1_NS_G').material;
  assert.notEqual(isolated, source);
  assert.notEqual(isolated, bulbs.get('TRAFFIC_J1_EW_G').material);
  assert.equal(isolated.emissiveIntensity, 3);
  assert.equal(bulbs.get('TRAFFIC_J1_NS_R').material.emissiveIntensity, 0);
  assert.equal(bulbs.get('TRAFFIC_J1_EW_R').material.emissiveIntensity, 3);
  assert.equal(bulbs.get('TRAFFIC_J1_PED_NS_G').material.emissiveIntensity, 0);
  controller.update(18);
  assert.equal(bulbs.get('TRAFFIC_J1_NS_Y').material.emissiveIntensity, 3);
  assert.equal(isolated.emissiveIntensity, 0);
  controller.update(46);
  assert.equal(bulbs.get('TRAFFIC_J1_NS_R').material.emissiveIntensity, 3);
  assert.equal(bulbs.get('TRAFFIC_J1_PED_NS_G').material.emissiveIntensity, 3);
  assert.equal(bulbs.get('TRAFFIC_J1_PED_NS_R').material.emissiveIntensity, 0);
  controller.update(56);
  assert.equal(bulbs.get('TRAFFIC_J1_PED_NS_R').material.emissiveIntensity, 3);
  assert.equal(bulbs.get('TRAFFIC_J1_PED_NS_G').material.emissiveIntensity, 0);
  controller.update(56.5);
  assert.equal(bulbs.get('TRAFFIC_J1_PED_NS_R').material.emissiveIntensity, 0);
  controller.update(57);
  assert.equal(bulbs.get('TRAFFIC_J1_PED_NS_R').material.emissiveIntensity, 3);
  assert.equal(source.emissiveIntensity, .3);
  assert.equal(source.color.getHex(), 0xdddddd);
  let disposed = 0; isolated.addEventListener('dispose', () => { disposed += 1; });
  controller.dispose(); controller.dispose(); controller.update(46);
  assert.equal(disposed, 1);
  for (const bulb of bulbs.values()) assert.equal(bulb.material, source);
  source.dispose(); geometry.dispose();
});

test('controller supports named parent groups and material arrays without changing replacements', () => {
  const scene = new Group(), named = new Group(); named.name = 'TRAFFIC_J3_PED_EW_G';
  const originals = [new MeshStandardMaterial(), new MeshStandardMaterial()];
  const geometry = new SphereGeometry(.1, 4, 4), bulb = new Mesh(geometry, originals);
  named.add(bulb); scene.add(named);
  const controller = createTrafficLightController(scene);
  assert.equal(controller.bulbCount, 1);
  assert.notEqual(bulb.material, originals);
  controller.update(46);
  assert.ok(bulb.material.every(material => material.emissiveIntensity === 3));
  assert.ok(originals.every(material => material.emissiveIntensity === 1));
  const replacement = new MeshStandardMaterial(); bulb.material = replacement;
  controller.dispose(); assert.equal(bulb.material, replacement);
  assert.equal(createTrafficLightController(null).bulbCount, 0);
  originals.forEach(material => material.dispose()); replacement.dispose(); geometry.dispose();
});
