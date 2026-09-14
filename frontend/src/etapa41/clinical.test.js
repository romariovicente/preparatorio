import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  evaluateExercise,
  exercises,
  formats,
} from './curriculum.js';
import {
  CLINICAL_KEY,
  emptyClinical,
  finishClinical,
  loadClinical,
  saveClinical,
  validateClinical,
} from './progress.js';

const answersFor = exercise => Object.fromEntries(
  exercise.rows.map(([id, , field]) => [id, field]),
);

test('cada exercício contém quatro trechos e todos os campos', () => {
  assert.equal(
    new Set(exercises.map(e => e.id)).size,
    exercises.length,
  );

  for (const exercise of exercises) {
    assert.equal(exercise.rows.length, 4);
    assert.equal(
      new Set(exercise.rows.map(([id]) => id)).size,
      4,
    );
    assert.deepEqual(
      exercise.rows.map(([, , field]) => field).sort(),
      formats[exercise.format].map(([id]) => id).sort(),
    );
  }
});

test('respostas ausentes, repetidas ou trocadas não aprovam', () => {
  const exercise = exercises[0];

  assert.equal(evaluateExercise(exercise.id, {}).passed, false);
  assert.equal(evaluateExercise(exercise.id, null).passed, false);

  const repeated = Object.fromEntries(
    exercise.rows.map(([id]) => [id, 'S']),
  );
  assert.equal(evaluateExercise(exercise.id, repeated).passed, false);

  const wrong = answersFor(exercise);
  [wrong.a, wrong.b] = [wrong.b, wrong.a];

  assert.equal(evaluateExercise(exercise.id, wrong).passed, false);
  assert.equal(evaluateExercise('unknown', wrong).passed, false);
});

test('somente acertos concluem e repetir não duplica conclusão', () => {
  const start = emptyClinical();
  assert.equal(finishClinical(start, exercises[0].id, {}), start);

  let progress = start;

  for (const exercise of exercises) {
    progress = finishClinical(
      progress,
      exercise.id,
      answersFor(exercise),
    );
  }

  assert.equal(progress.completed.length, 4);
  assert.equal(
    finishClinical(
      progress,
      exercises[0].id,
      answersFor(exercises[0]),
    ),
    progress,
  );
});

test('validação remove dados desconhecidos e versões incompatíveis', () => {
  const id = exercises[0].id;

  assert.deepEqual(
    validateClinical({
      version: 1,
      completed: [id, id, 'unknown'],
      patient: 'discard',
    }),
    { version: 1, completed: [id] },
  );

  for (const value of [
    null,
    {},
    { version: 2, completed: [id] },
    { version: 1, completed: 'invalid' },
  ]) {
    assert.deepEqual(validateClinical(value), emptyClinical());
  }
});

test('corrupção, armazenamento negado e cota excedida são tratados', () => {
  assert.deepEqual(
    loadClinical({ getItem: () => '{invalid' }),
    emptyClinical(),
  );

  const denied = {
    getItem() { throw Error('denied'); },
    setItem() { throw Error('quota'); },
  };

  assert.deepEqual(loadClinical(denied), emptyClinical());
  assert.equal(saveClinical(denied, emptyClinical()), false);
});

test('persistência clínica preserva o progresso anterior do jogo', () => {
  const values = new Map([
    ['preparatorio.progress.v1', 'preserved'],
  ]);

  const storage = {
    getItem: key => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, value),
  };

  const exercise = exercises[0];
  const progress = finishClinical(
    emptyClinical(),
    exercise.id,
    answersFor(exercise),
  );

  assert.equal(saveClinical(storage, progress), true);
  assert.ok(values.has(CLINICAL_KEY));
  assert.deepEqual(loadClinical(storage), progress);
  assert.equal(values.get('preparatorio.progress.v1'), 'preserved');
});
