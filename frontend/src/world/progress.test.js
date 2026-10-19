import test from 'node:test';
import assert from 'node:assert/strict';
import { sanitizeProgress, discover, readProgress, writeProgress, rewardBalance } from './progress.js';

const ids = ['senac','ufal','hospital'];
test('discovery cannot be rewarded twice or for an unknown destination', () => {
  let p = sanitizeProgress(null, ids);
  p = discover(p, 'senac', ids);
  p = discover(p, 'senac', ids);
  p = discover(p, 'unknown', ids);
  assert.deepEqual(p.visited, ['senac']);
  assert.equal(rewardBalance(p), 20);
});
test('stored rewards are derived from validated visits, never trusted from saved balance', () => {
  const p = sanitizeProgress({version:1, visited:['ufal','ufal',null,'admin'],balance:99999},ids);
  assert.deepEqual(p, {version:1,visited:['ufal']});
  assert.equal(rewardBalance(p),20);
  assert.deepEqual(sanitizeProgress({version:2,visited:ids},ids).visited,[]);
});
test('blocked, corrupted and full storage never break exploration', () => {
  assert.deepEqual(readProgress({getItem(){throw Error('denied')}},ids).visited,[]);
  assert.deepEqual(readProgress({getItem(){return '{broken'}},ids).visited,[]);
  assert.equal(writeProgress({setItem(){throw Error('quota')}},{version:1,visited:[]}),false);
});
