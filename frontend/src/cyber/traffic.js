import trafficCycle from '../config/trafficCycle.json' with { type: 'json' };

// This shared stage table is a game demonstration, not actual HEA signal timing.
export const TRAFFIC_PHASES = Object.freeze(trafficCycle.stages.map(stage => Object.freeze({ ...stage })));
export const TRAFFIC_CYCLE_SECONDS = TRAFFIC_PHASES.reduce((seconds, stage) => seconds + stage.duration, 0);
export const PEDESTRIAN_FLASH_HALF_PERIOD = trafficCycle.flashingRedOnSeconds;

/** NS/EW are vehicle axes. Both pedestrian groups use a separate protected stage. */
export function sampleTraffic(elapsedSeconds) {
  const elapsed = Number.isFinite(elapsedSeconds) ? elapsedSeconds : 0;
  const cycleElapsed = ((elapsed % TRAFFIC_CYCLE_SECONDS) + TRAFFIC_CYCLE_SECONDS) % TRAFFIC_CYCLE_SECONDS;
  let start = 0;
  for (let index = 0; index < TRAFFIC_PHASES.length; index += 1) {
    const stage = TRAFFIC_PHASES[index];
    if (cycleElapsed < start + stage.duration) {
      const phaseElapsed = cycleElapsed - start;
      return {
        ns: stage.ns,
        ew: stage.ew,
        pedNs: stage.pedNs,
        pedEw: stage.pedEw,
        phase: stage.id,
        phaseIndex: index,
        phaseElapsed,
        phaseRemaining: stage.duration - phaseElapsed,
        cycleElapsed,
        cycleSeconds: TRAFFIC_CYCLE_SECONDS,
        pedestrianRedLit: Math.floor(phaseElapsed / PEDESTRIAN_FLASH_HALF_PERIOD) % 2 === 0,
      };
    }
    start += stage.duration;
  }
  // Durations are positive and the modulo is bounded; this guards corrupted tables.
  return { ns: 'red', ew: 'red', pedNs: 'red', pedEw: 'red', phase: 'SAFE_RED', phaseIndex: -1, phaseElapsed: 0, phaseRemaining: 0, cycleElapsed: 0, cycleSeconds: TRAFFIC_CYCLE_SECONDS, pedestrianRedLit: true };
}

const LAMP_COLOURS = Object.freeze({ R: 0xe53935, Y: 0xffd130, G: 0x21b24b });
const DARK_COLOUR = 0x071016;
const LAMP_PATTERN = /^TRAFFIC_J(\d+)_(?:(PED)_)?(NS|EW)_(R|Y|G)(?:[._]\d+)?$/;

/** Blender duplicate names may have .001, renamed to _001 by the GLB loader. */
export function trafficLampDescriptor(name) {
  const match = typeof name === 'string' && name.match(LAMP_PATTERN);
  if (!match || (match[2] && match[4] === 'Y')) return null;
  return { junction: Number(match[1]), pedestrian: Boolean(match[2]), axis: match[3], signal: match[4] };
}

function descriptorForNode(node, scene) {
  let current = node;
  while (current) {
    const descriptor = trafficLampDescriptor(current.name);
    if (descriptor) return descriptor;
    if (current === scene) break;
    current = current.parent;
  }
  return null;
}

function isLampLit(descriptor, state) {
  if (!descriptor.pedestrian) {
    const signal = state[descriptor.axis.toLowerCase()];
    return descriptor.signal === ({ red: 'R', yellow: 'Y', green: 'G' })[signal];
  }
  const signal = state[descriptor.axis === 'NS' ? 'pedNs' : 'pedEw'];
  if (descriptor.signal === 'G') return signal === 'green';
  return signal === 'red' || (signal === 'flashing-red' && state.pedestrianRedLit);
}

/**
 * Isolate each bulb material from GLTF cache and other scene instances.
 * No geometry, object transform, global material or animation is changed.
 */
export function createTrafficLightController(scene) {
  const lamps = [];
  const ownedMaterials = new Set();
  let disposed = false;
  if (scene && typeof scene.traverse === 'function') {
    scene.traverse(node => {
      if (!node.isMesh || !node.material) return;
      const descriptor = descriptorForNode(node, scene);
      if (!descriptor) return;
      const originals = Array.isArray(node.material) ? node.material : [node.material];
      if (originals.some(material => !material || typeof material.clone !== 'function')) return;
      const materials = originals.map(material => material.clone());
      materials.forEach(material => ownedMaterials.add(material));
      const assigned = Array.isArray(node.material) ? materials : materials[0];
      lamps.push({ node, descriptor, original: node.material, assigned, materials, lit: null });
      node.material = assigned;
    });
  }

  function update(elapsedSeconds) {
    const state = sampleTraffic(elapsedSeconds);
    if (disposed) return state;
    for (const lamp of lamps) {
      const lit = isLampLit(lamp.descriptor, state);
      if (lit === lamp.lit) continue;
      for (const material of lamp.materials) {
        material.color?.setHex(lit ? LAMP_COLOURS[lamp.descriptor.signal] : DARK_COLOUR);
        material.emissive?.setHex(lit ? LAMP_COLOURS[lamp.descriptor.signal] : 0x000000);
        if ('emissiveIntensity' in material) material.emissiveIntensity = lit ? 3 : 0;
      }
      lamp.lit = lit;
    }
    return state;
  }

  function dispose() {
    if (disposed) return;
    disposed = true;
    for (const lamp of lamps) {
      if (lamp.node.material === lamp.assigned) lamp.node.material = lamp.original;
    }
    ownedMaterials.forEach(material => material.dispose?.());
    ownedMaterials.clear();
  }

  update(0);
  return { update, dispose, bulbCount: lamps.length };
}
