import { evaluateExercise, exercises } from './curriculum.js';

export const CLINICAL_KEY = 'preparatorio.clinical.v1';

export const emptyClinical = () => ({
  version: 1,
  completed: [],
});

export function validateClinical(value) {
  if (value?.version !== 1 || !Array.isArray(value.completed)) {
    return emptyClinical();
  }

  return {
    version: 1,
    completed: exercises
      .map(item => item.id)
      .filter(id => value.completed.includes(id)),
  };
}

export function loadClinical(storage) {
  try {
    return validateClinical(JSON.parse(storage.getItem(CLINICAL_KEY)));
  } catch {
    return emptyClinical();
  }
}

export function saveClinical(storage, progress) {
  try {
    storage.setItem(
      CLINICAL_KEY,
      JSON.stringify(validateClinical(progress)),
    );
    return true;
  } catch {
    return false;
  }
}

export function finishClinical(progress, id, answers) {
  if (
    !evaluateExercise(id, answers).passed ||
    progress.completed.includes(id)
  ) {
    return progress;
  }

  return validateClinical({
    ...progress,
    completed: [...progress.completed, id],
  });
}
