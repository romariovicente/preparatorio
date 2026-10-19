import { test } from 'node:test';
import assert from 'node:assert/strict';
import { evaluateExercise, exercises, formats } from './curriculum.js';
import { CLINICAL_KEY, emptyClinical, finishClinical, loadClinical, saveClinical, validateClinical } from './progress.js';

const answersFor = exercise => Object.fromEntries(exercise.rows.map(([id, , field]) => [id, field]));
test('each clinical exercise has four distinct rows and all format fields', () => {
  assert.equal(new Set(exercises.map(e => e.id)).size, exercises.length);
  for (const e of exercises) {
    assert.equal(e.rows.length, 4);
    assert.equal(new Set(e.rows.map(([id]) => id)).size, 4);
    assert.deepEqual(e.rows.map(([, , field]) => field).sort(), formats[e.format].map(([id]) => id).sort());
  }
});
test('missing, duplicate, swapped and unknown answers do not pass', () => {
  const e = exercises[0];
  assert.equal(evaluateExercise(e.id, {}).passed, false);
  assert.equal(evaluateExercise(e.id, null).passed, false);
  assert.equal(evaluateExercise(e.id, Object.fromEntries(e.rows.map(([id]) => [id, 'S']))).passed, false);
  const wrong = answersFor(e);
  [wrong.a, wrong.b] = [wrong.b, wrong.a];
  assert.equal(evaluateExercise(e.id, wrong).passed, false);
  assert.equal(evaluateExercise('unknown', wrong).passed, false);
});
test('only correct answers complete an exercise, and completion is idempotent', () => {
  const start = emptyClinical();
  assert.equal(finishClinical(start, exercises[0].id, {}), start);
  let progress = start;
  for (const e of exercises) progress = finishClinical(progress, e.id, answersFor(e));
  assert.equal(progress.completed.length, 4);
  assert.equal(finishClinical(progress, exercises[0].id, answersFor(exercises[0])), progress);
});
test('save validation strips unknown fields, duplicate IDs and future versions', () => {
  const id = exercises[0].id;
  assert.deepEqual(validateClinical({ version: 1, completed: [id, id, 'unknown'], patient: 'discard' }), { version: 1, completed: [id] });
  for (const value of [null, {}, { version: 2, completed: [id] }, { version: 1, completed: 'invalid' }]) assert.deepEqual(validateClinical(value), emptyClinical());
});
test('corruption, denied storage and quota failures are safe', () => {
  assert.deepEqual(loadClinical({ getItem: () => '{invalid' }), emptyClinical());
  const denied = { getItem() { throw Error('denied'); }, setItem() { throw Error('quota'); } };
  assert.deepEqual(loadClinical(denied), emptyClinical());
  assert.equal(saveClinical(denied, emptyClinical()), false);
});
test('clinical persistence round-trips without touching stage 40 storage', () => {
  const values = new Map([['preparatorio.progress.v1', 'preserved']]);
  const storage = { getItem: key => values.get(key) ?? null, setItem: (key, value) => values.set(key, value) };
  const e = exercises[0];
  const progress = finishClinical(emptyClinical(), e.id, answersFor(e));
  assert.equal(saveClinical(storage, progress), true);
  assert.ok(values.has(CLINICAL_KEY));
  assert.deepEqual(loadClinical(storage), progress);
  assert.equal(values.get('preparatorio.progress.v1'), 'preserved');
});
