import { useState } from 'react';
import { evaluateExercise, exercises, formats } from './curriculum.js';
import {
  emptyClinical,
  finishClinical,
  loadClinical,
  saveClinical,
} from './progress.js';

export default function ClinicalLab() {
  const [progress, setProgress] = useState(() => {
    try {
      return loadClinical(window.localStorage);
    } catch {
      return emptyClinical();
    }
  });

  const [active, setActive] = useState(exercises[0].id);
  const [answers, setAnswers] = useState({});
  const [result, setResult] = useState(null);
  const [storageMessage, setStorageMessage] = useState(
    'Conclusões são salvas somente neste navegador.',
  );

  const exercise = exercises.find(item => item.id === active);
  const fields = formats[exercise.format];

  function changeExercise(event) {
    setActive(event.target.value);
    setAnswers({});
    setResult(null);
  }

  function submit(event) {
    event.preventDefault();

    const checked = evaluateExercise(active, answers);
    setResult(checked);

    if (!checked.passed) return;

    const next = finishClinical(progress, active, answers);
    setProgress(next);

    let saved = false;

    try {
      saved = saveClinical(window.localStorage, next);
    } catch {
      // A atividade continua em memória se o armazenamento for negado.
    }

    setStorageMessage(
      saved
        ? 'Conclusão salva neste navegador.'
        : 'Não foi possível salvar. A conclusão fica apenas nesta sessão.',
    );
  }

  return (
    <section className="clinical-lab" aria-labelledby="clinical-title">
      <h3 id="clinical-title">Laboratório SBAR / SOAP</h3>

      <p>
        Pratique a organização de informações em dois casos fictícios de
        comunicação hospitalar. Use cada categoria uma vez.
      </p>

      <p className="clinical-note">
        Simulação de comunicação; não é prontuário real, prescrição ou
        certificação profissional.
      </p>

      <p>
        {progress.completed.length}/{exercises.length} exercícios concluídos
      </p>

      <label htmlFor="clinical-exercise">Caso e formato</label>

      <select
        id="clinical-exercise"
        value={active}
        onChange={changeExercise}
      >
        {exercises.map(item => (
          <option key={item.id} value={item.id}>
            {item.format} · {item.title}
            {progress.completed.includes(item.id) ? ' · concluído' : ''}
          </option>
        ))}
      </select>

      <details className="clinical-guide">
        <summary>Como organizar {exercise.format}</summary>
        <dl>
          {fields.map(([key, label, hint]) => (
            <div key={key}>
              <dt>{key} · {label}</dt>
              <dd>{hint}</dd>
            </div>
          ))}
        </dl>
      </details>

      <form onSubmit={submit} noValidate>
        {exercise.rows.map(([id, text, expected], index) => {
          const incorrect = result && answers[id] !== expected;
          const hint = fields.find(([key]) => key === expected)[2];

          return (
            <fieldset
              key={`${active}-${id}`}
              className={
                incorrect
                  ? 'clinical-row clinical-incorrect'
                  : 'clinical-row'
              }
            >
              <legend>Trecho {index + 1}</legend>
              <p id={`clinical-text-${id}`}>{text}</p>

              <label htmlFor={`clinical-answer-${id}`}>
                Categoria do trecho {index + 1}
              </label>

              <select
                id={`clinical-answer-${id}`}
                value={answers[id] ?? ''}
                aria-describedby={
                  `clinical-text-${id}` +
                  (result ? ` clinical-feedback-${id}` : '')
                }
                aria-invalid={incorrect ? true : undefined}
                onChange={event => {
                  setAnswers({ ...answers, [id]: event.target.value });
                  setResult(null);
                }}
              >
                <option value="">Escolha uma categoria</option>
                {fields.map(([key, label]) => (
                  <option key={key} value={key}>
                    {key} · {label}
                  </option>
                ))}
              </select>

              {result && (
                <p id={`clinical-feedback-${id}`}>
                  {incorrect
                    ? `Revise: ${hint}`
                    : 'Classificação correta.'}
                </p>
              )}
            </fieldset>
          );
        })}

        <button type="submit">Verificar classificação</button>
      </form>

      <p role="status" aria-atomic="true">
        {result && (
          result.passed
            ? 'Muito bem: 4 de 4. Confira o registro organizado abaixo.'
            : !result.complete
              ? 'Preencha os quatro trechos e verifique novamente.'
              : `${result.correct} de 4 corretos. Revise as indicações e tente novamente.`
        )}
      </p>

      {result?.passed && (
        <section
          className="clinical-record"
          aria-label="Registro fictício organizado"
        >
          <h4>{exercise.format} · Registro fictício</h4>
          <dl>
            {fields.map(([key, label]) => (
              <div key={key}>
                <dt>{key} · {label}</dt>
                <dd>
                  {exercise.rows.find(([, , field]) => field === key)[1]}
                </dd>
              </div>
            ))}
          </dl>
        </section>
      )}

      <small role="status">{storageMessage}</small>
    </section>
  );
}
