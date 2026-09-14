export const formats = {
  SBAR: [
    ['S', 'Situação', 'O que precisa ser comunicado agora?'],
    ['B', 'Contexto', 'Que informação anterior ajuda a entender a situação?'],
    ['A', 'Avaliação', 'Qual é a síntese fundamentada do problema?'],
    ['R', 'Recomendação', 'O que você solicita à equipe?'],
  ],
  SOAP: [
    ['S', 'Subjetivo', 'O que a pessoa relata?'],
    ['O', 'Objetivo', 'O que foi observado ou verificado?'],
    ['A', 'Avaliação', 'Como interpretar os dados disponíveis?'],
    ['P', 'Plano', 'Qual é o próximo passo documentado?'],
  ],
};

// Casos autorais com trechos fixos, sem dados de pacientes reais.
export const exercises = [
  {
    id: 'return-sbar',
    format: 'SBAR',
    title: 'Orientação de retorno',
    rows: [
      [
        'a',
        'A orientação anterior não foi compreendida; há uma necessidade de comunicação ainda não atendida.',
        'A',
      ],
      [
        'b',
        'Sou estudante na recepção simulada. A pessoa fictícia solicita esclarecimento sobre o local do retorno.',
        'S',
      ],
      [
        'c',
        'Peço ao preceptor que revise a orientação e confirme com a pessoa como ela entendeu o trajeto.',
        'R',
      ],
      [
        'd',
        'Na etapa anterior da simulação, foi entregue um cartão com o local do retorno.',
        'B',
      ],
    ],
  },
  {
    id: 'return-soap',
    format: 'SOAP',
    title: 'Orientação de retorno',
    rows: [
      [
        'a',
        'O cartão apresentado contém o nome do setor, mas não contém um mapa do trajeto.',
        'O',
      ],
      [
        'b',
        'Revisar o trajeto com o preceptor e registrar a confirmação de entendimento na simulação.',
        'P',
      ],
      [
        'c',
        'A pessoa fictícia relata: não entendi onde será meu retorno.',
        'S',
      ],
      [
        'd',
        'O relato e o cartão sugerem que a orientação de localização precisa ser complementada.',
        'A',
      ],
    ],
  },
  {
    id: 'access-sbar',
    format: 'SBAR',
    title: 'Comunicação acessível',
    rows: [
      [
        'a',
        'No acolhimento anterior, a pessoa fictícia informou preferência por material com letras maiores.',
        'B',
      ],
      [
        'b',
        'Solicito ao preceptor uma versão ampliada do material e a confirmação de que ela atende à preferência informada.',
        'R',
      ],
      [
        'c',
        'Sou estudante no balcão simulado. A pessoa fictícia solicita uma versão legível do roteiro de visita.',
        'S',
      ],
      [
        'd',
        'O material oferecido não atende à preferência registrada, dificultando a comunicação.',
        'A',
      ],
    ],
  },
  {
    id: 'access-soap',
    format: 'SOAP',
    title: 'Comunicação acessível',
    rows: [
      [
        'a',
        'Há uma barreira de apresentação do material, segundo o relato e a observação disponíveis.',
        'A',
      ],
      [
        'b',
        'A pessoa fictícia relata: prefiro ler o roteiro com letras maiores.',
        'S',
      ],
      [
        'c',
        'Disponibilizar, com o preceptor, uma versão ampliada e verificar sua legibilidade com a pessoa na simulação.',
        'P',
      ],
      [
        'd',
        'O roteiro entregue está na versão padrão; nenhuma versão ampliada foi apresentada nesta cena.',
        'O',
      ],
    ],
  },
];

export function evaluateExercise(id, answers = {}) {
  const exercise = exercises.find(item => item.id === id);

  if (!exercise) {
    return { complete: false, correct: 0, passed: false };
  }

  const allowed = formats[exercise.format].map(([key]) => key);
  const complete = exercise.rows.every(
    ([key]) => allowed.includes(answers?.[key]),
  );
  const correct = exercise.rows.filter(
    ([key, , expected]) => answers?.[key] === expected,
  ).length;

  return {
    complete,
    correct,
    passed: complete && correct === exercise.rows.length,
  };
}
