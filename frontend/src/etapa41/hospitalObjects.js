export const HOSPITAL_LAYOUT_KEY = 'prep.hospital.layout.v1';
export const HOSPITAL_START = [-2, 0, 2.7];
export const HOSPITAL_BOUNDS = { minX: -4.6, maxX: 4.8, minZ: -3.55, maxZ: 3.6 };

export const hospitalTemplates = [
  { id: 'hospital_kit', name: 'Kit hospitalar', kind: 'kit', position: [3.5, 1.2, 1.7], portable: true, movable: false, size: [0.5, 0.45], description: 'Cópia pessoal do kit hospitalar para transportar nesta simulação.' },
  { id: 'hospital_tray', name: 'Bandeja de treino', kind: 'tray', position: [2.4, 1.25, 1.65], portable: true, movable: false, size: [0.6, 0.4], description: 'Bandeja vazia para praticar o transporte de objetos.' },
  { id: 'hospital_cart', name: 'Carrinho de apoio', kind: 'cart', position: [3.1, 0, -1.6], portable: false, movable: true, size: [0.9, 0.75], description: 'Móvel que pode ser reposicionado nas áreas livres do hospital.' },
  { id: 'hospital_chair', name: 'Cadeira', kind: 'chair', position: [-3.9, 0, 1.25], portable: false, movable: true, size: [0.65, 0.7], description: 'Móvel que pode ser reposicionado sem bloquear camas e balcão.' },
];

const fixedObstacles = [
  { x: -2.8, z: -1.6, width: 1.7, depth: 2.5 },
  { x: 0, z: -1.6, width: 1.7, depth: 2.5 },
  { x: 2.8, z: 1.6, width: 2.5, depth: 0.9 },
  { x: 1, z: 2.1, width: 0.55, depth: 0.45 },
];

function overlaps(x, z, width, depth, obstacle) {
  return Math.abs(x - obstacle.x) < (width + obstacle.width) / 2 &&
    Math.abs(z - obstacle.z) < (depth + obstacle.depth) / 2;
}

export function hospitalPlacementAllowed(position, size = [0.5, 0.5], furniture = [], ignoredId) {
  if (!Array.isArray(position) || position.length !== 3 || position.some(n => !Number.isFinite(n))) return false;
  const [x, , z] = position, [width, depth] = size;
  if (x - width / 2 < HOSPITAL_BOUNDS.minX || x + width / 2 > HOSPITAL_BOUNDS.maxX ||
      z - depth / 2 < HOSPITAL_BOUNDS.minZ || z + depth / 2 > HOSPITAL_BOUNDS.maxZ) return false;
  const obstacles = [...fixedObstacles, ...furniture.filter(item => item.id !== ignoredId).map(item => ({
    x: item.position[0], z: item.position[2], width: item.size[0], depth: item.size[1],
  }))];
  return !obstacles.some(obstacle => overlaps(x, z, width + 0.12, depth + 0.12, obstacle));
}

export function stepHospitalPlayer(position, direction, furniture = []) {
  const next = [position[0] + direction[0] * 0.45, 0, position[2] + direction[1] * 0.45];
  return hospitalPlacementAllowed(next, [0.5, 0.5], furniture) ? next : position;
}

// A small breadth-first grid route keeps the visitor out of beds and furniture.
export function routeToHospitalObject(start, target, furniture = []) {
  const step = 0.45, queue = [[start]], seen = new Set(['0,0']);
  for (let index = 0; index < queue.length && index < 1200; index++) {
    const route = queue[index], point = route.at(-1);
    if (Math.hypot(point[0] - target[0], point[2] - target[2]) <= 1.45) return route.slice(1);
    for (const [dx, dz] of [[0, 1], [1, 0], [0, -1], [-1, 0]]) {
      const next = [point[0] + dx * step, 0, point[2] + dz * step];
      const key = `${Math.round((next[0] - start[0]) / step)},${Math.round((next[2] - start[2]) / step)}`;
      if (!seen.has(key) && hospitalPlacementAllowed(next, [0.5, 0.5], furniture)) {
        seen.add(key); queue.push([...route, next]);
      }
    }
  }
  return null;
}

export function readHospitalLayout(storage) {
  const fallback = Object.fromEntries(hospitalTemplates.filter(t => t.movable).map(t => [t.id, [...t.position]]));
  try {
    const value = JSON.parse(storage.getItem(HOSPITAL_LAYOUT_KEY));
    if (value?.version !== 1 || !value.positions || typeof value.positions !== 'object') return fallback;
    for (const template of hospitalTemplates.filter(t => t.movable)) {
      const candidate = value.positions[template.id];
      const furniture = hospitalTemplates.filter(t => t.movable).map(t => ({ ...t, position: fallback[t.id] }));
      if (hospitalPlacementAllowed(candidate, template.size, furniture, template.id)) fallback[template.id] = [candidate[0], 0, candidate[2]];
    }
  } catch { /* Invalid local data falls back to the authored layout. */ }
  return fallback;
}

export function writeHospitalLayout(storage, positions) {
  try {
    storage.setItem(HOSPITAL_LAYOUT_KEY, JSON.stringify({ version: 1, positions }));
    return true;
  } catch { return false; }
}
