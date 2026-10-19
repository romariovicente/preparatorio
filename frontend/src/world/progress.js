export const PROGRESS_KEY = 'preparatorio.island.progress.v1';
export const DISCOVERY_REWARD = 20;
export const INTRO_LOCATIONS = ['senac', 'ufal', 'hospital'];

export function sanitizeProgress(value, ids) {
  const allowed = new Set(ids);
  if (!value || value.version !== 1) return { version: 1, visited: [] };
  const visited = Array.isArray(value.visited)
    ? [...new Set(value.visited.filter(id => typeof id === 'string' && allowed.has(id)))] : [];
  return { version: 1, visited };
}

export function discover(progress, id, ids) {
  const clean = sanitizeProgress(progress, ids);
  if (!ids.includes(id) || clean.visited.includes(id)) return clean;
  return { ...clean, visited: [...clean.visited, id] };
}

export function readProgress(storage, ids) {
  try { return sanitizeProgress(JSON.parse(storage.getItem(PROGRESS_KEY)), ids); }
  catch { return { version: 1, visited: [] }; }
}

export function writeProgress(storage, progress) {
  try { storage.setItem(PROGRESS_KEY, JSON.stringify(progress)); return true; }
  catch { return false; }
}

export function rewardBalance(progress) { return progress.visited.length * DISCOVERY_REWARD; }
