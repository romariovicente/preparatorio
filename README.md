# PREPARATÓRIO — cidade, ilha, campus e acervo 3D

Atualização salva em **16/10/2026**: master editável `art/blender/PREPARATORIO_PROJETO_20261016.blend`, com 82 cenas e 15.744 objetos. A reabertura independente registrada em `reports/DELIVERY_READBACK_20261016.json` passou sem modificar o arquivo. Foram acrescentados 13 modelos ao acervo: seis animais com os esqueletos e animações originais, quatro conjuntos anatômicos, uma composição ferroviária, trilhos e uma estação. O frontend passou em 161 testes, lint e build. Esses modelos estão disponíveis para inspeção no Acervo 3D; isto não afirma que todos já sejam dirigíveis ou estejam posicionados na cidade jogável.

O mapa macro permanece uma cena de planejamento separada. Realismo integral, autenticação de produção, multiplayer público e sincronização com um Jarvis externo ainda exigem validação própria. A preparação do backup remoto e da publicação está em andamento; o salvamento local não equivale a um envio confirmado ao GitHub.

Retomada de **09/10/2026**: o jogo abre com o smartphone fechado e o botão **Jogar agora**, que ativa o teclado e o áudio conforme as preferências salvas. Fechar o smartphone, visitar a sala de aula ou entrar num carro/moto devolve o foco ao cenário. Use **WASD ou setas**, **Espaço** para pular e **F** para entrar/sair de veículos. O launcher reutiliza os serviços deste projeto já ativos, sem criar instâncias duplicadas.

O apoio dos pés considera uma pequena área ao redor do personagem, corrigindo a sobreposição com bordas de calçadas sem alterar os clips ou o esqueleto. **111 testes do frontend passaram**, lint das áreas alteradas e build concluídos. A sessão inicial vazia do Blender foi preservada antes de reabrir o master existente com **6.521 objetos**. Detalhes e limitações em [retomada verificada de 09/10](reports/RETOMADA_VERIFICADA_20261009.md).

Checkpoint atual de **08/10/2026**: `art/blender/PREPARATORIO_PROJETO_20261008.blend`, cena `00_ARAPIRACA_CYBER_20261005`, com 6.521 objetos. A sala de aula integrada possui 12 alunos com os esqueletos Remy originais, porta animada, mobiliário e anatomia. Ônibus, terminal, paradas, novas vias/ciclofaixas e veículos articulados também foram integrados. A moto pode ser chamada pelo smartphone, pilotada e recolhida no estacionamento; apenas um veículo pessoal fica ativo.

Validação: **101 testes do frontend e 13 do backend aprovados**, compilação concluída e entrada na sala conferida no navegador. O Blender foi restaurado, a montagem da sala foi corrigida e 497 posições/hierarquias foram comparadas ao arquivo original. Ele fica aberto numa vista de inspeção da sala; a cidade completa permanece salva. Consulte [a entrega verificada e suas limitações](reports/ENTREGA_VERIFICADA_20261008.md). O realismo integral da cidade e o acabamento de todas as roupas/animações ainda estão em desenvolvimento.

## Histórico da integração de 02/10/2026

Atualização de **02/10/2026**: o acervo derivado contém **151 modelos com exportação e reimportação registradas**, incluindo **18 personagens com rig**, **seis motocicletas**, veículos, naves, cenários, equipamentos e três modelos de anatomia. Uma auditoria independente conferiu os 151 GLBs por tamanho e SHA-256. Há 12 opções de locomoção em teste; cinco rigs derivados conservam poses limitadas. A ilha permanece integrada com 16 destinos e versões leve/detalhada, e os 32 módulos urbanos continuam disponíveis na aba Kit.

No Blender, o arquivo atual é **`art/blender/PREPARATORIO_PROJETO_20261002.blend`**, salvo com a cena principal **00_PREP_CAMPUS** e os materiais visíveis. As oito cenas **ACERVO_*** organizam os modelos por categoria, incluindo Personagens e Motocicletas. Cada categoria também possui um arquivo `.blend` separado na mesma pasta. O ambiente **ENV_PREP_Campus_v2.glb** foi exportado e reimportado com sucesso.

O arquivo principal foi **reaberto no Blender 5.2.2 LTS**: 151 modelos, 18 personagens, seis motos, unidades de 1 m por BU e movimento do carrinho entre os frames 1 e 60 confirmados. As cores do anime foram corrigidas preservando o rig e os clips Idle/Walk. Consulte `reports/saved_master_reopen_validation_20261002.json` e `reports/material_qa/anime_color_fix.json`.

Execute `Start-Preparatorio.ps1` no Windows para iniciar o frontend local. Use **Acervo 3D** para consultar os modelos e seus créditos. O projeto também contém o livro local de 150 páginas, 54 módulos de leitura, oito exercícios de matemática e o índice de 66 itens diretos do Drive. O livro foi indexado; não há afirmação de revisão clínica completa de todas as fontes.

O launcher também inicia a **sala compartilhada local** na porta 5180. Duas abas recebem jogadores distintos, podem criar e carregar suas cópias de objetos e enxergam as alterações confirmadas pelo servidor. O hospital permite reposicionar cópias de móveis em áreas livres. Os objetos base permanecem disponíveis. Leia [as instruções da demonstração](multiplayer/README.md); quatro testes de HTTP/SSE e transporte passaram, incluindo a recuperação automática da conexão. Os fluxos de campus e hospital foram conferidos no navegador com duas abas, e 30 testes do frontend passaram. As salas usam memória do processo, e esta etapa compartilha abas na mesma máquina.

Verificação final desta atualização: **30/30 testes frontend**, **4/4 testes multiplayer**, lint das áreas alteradas e **build Vite com 2.451 módulos** passaram. O build conserva um aviso de tamanho do chunk da dependência 3D OrbitControls, aproximadamente 981 KB. A interface foi conferida em tela de **390 × 844**, sem overflow horizontal, com movimento do campus e rolagem do painel hospitalar funcionando. Evidências em `reports/multiplayer_checks_20261002.json` e nas imagens `campus_*_20261002.png` e `hospital_*_20261002.png`.

Consulte [a auditoria atual de arquivos](reports/EXPANSAO_20261002.md), [o relatório anterior de integração](reports/INTEGRACAO_MAPA_E_ACERVO.md), [os créditos](THIRD_PARTY_ASSETS.md) e [o estado dos 37 requisitos](reports/REQUISITOS_E_STATUS.md). Os resultados por modelo ficam em `reports/supplied/*.json`; a conferência atual está em `reports/source_expansion_audit_20261002.json`. A montagem Blender, os novos rigs e as interações recebem verificações próprias. O histórico técnico da Fase 1 abaixo registra a situação de 28/09, anterior às expansões.

## Histórico — Fase 1 em 28/09/2026

Projeto reconstruído no Windows em 28/09/2026. Blender **5.2.2 LTS**, conectado ao complemento MCP em `127.0.0.1:9876`. O caminho Linux anterior não existe nesta máquina; esta pasta é a nova raiz do projeto, conforme autorizado.

## Entregas verificadas

- `art/blender/PREPARATORIO_CITY_KIT_01.blend`: kit editável, cena original preservada e cena de reimportação GLB.
- `art/blender/checkpoints/BEFORE_PHASE1_20260928.blend`: cópia da cena original antes de qualquer alteração.
- `frontend/public/assets/models/`: **33 GLBs**, sendo 32 módulos individuais com pivô na origem e um catálogo com disposição de apresentação.
- `frontend/src/config/assetRegistry.js`: somente os 32 assets gerados, mais a URL do catálogo.
- `reports/CITY_KIT_01_overview.png`: render Cycles inspecionado visualmente.
- `reports/kit_manifest.json`: nomes, categorias, medidas e coleções.
- `reports/glb_validation.json`: reimportação dos 32 módulos, comparação de limites/pivôs e hashes SHA-256 de todos os GLBs.
- `reports/script_tests.json` e `reports/frontend_checks.json`: verificações executadas.

## Convenções do kit

32 módulos: fachadas de vidro e concreto, paredes inteira/meia/com abertura, janela, porta, fachada comercial, cantos interno/externo, pilar, viga, laje, cobertura, parapeito, painéis de vidro/metal, brises horizontal/vertical, sacada, guarda-corpo, marquise, calçadas reta/canto, meio-fio, rua, cruzamento, faixa de pedestre, canteiro, rampa PCD, piso tátil e preenchimento de grama.

Coleções do kit: `PREP_CITY`, `PREP_Facades`, `PREP_Structure`, `PREP_Details`, `PREP_Streets`, `PREP_Presentation`.

Unidades métricas, 1 BU = 1 m. Encaixes principais em múltiplos de 0,25/0,5 m, com detalhes menores para caixilhos e acabamentos. Snap incremental absoluto ativo; grade visual 0,5 m com duas subdivisões. O incremento visual do Blender depende do zoom: não há promessa de travamento numérico em ambos os passos ao mesmo tempo. Pivôs na base de cada módulo; origem de montagem nos cantos em L. Blender Z para cima e frente -Y; GLB +Y para cima. A rampa é uma peça geométrica do kit, não uma certificação de acessibilidade de uma implantação.

10 materiais `MAT_PREP_*`, compartilhados: Concrete, Plaster, Metal, Glass, Asphalt, White, Yellow, Earth, Grass e Accent. Principled PBR e mapas ORM de 32×32 gerados proceduralmente e incorporados: R=1 (AO neutra, sem baking de oclusão), G=roughness, B=metallic. UVs planares; vidro com transmissão parcial. A apresentação não entra nas exportações.

## Scripts Blender

Execute pelo console/script Python do Blender ou pelo complemento MCP, usando `runpy.run_path(caminho, run_name='__main__')` para scripts de operação.

- `scripts/prep_prepare_asset.py`: `prepare(objects, apply_transforms=False)`, somente objetos identificados como PREP. Normais suaves, Bevel 0,015 m/2 segmentos/Angle e Weighted Normals. Nunca aplica localização. Rotação/escala são opcionais e recusadas para hierarquias, constraints, animação ou shape keys.
- `scripts/prep_materials.py`: `create_materials()`, reutiliza os materiais existentes e usa o grupo glTF completo da versão instalada do Blender.
- `scripts/prep_export_glb.py`: `export_assets(objects, path, center_single=False)`. Cópias temporárias preservam os originais; exportação estática +Y Up com modificadores avaliados. Recusa sobrescrever qualquer arquivo existente.
- `scripts/prep_build_kit.py`: constrói o kit em uma nova cena. Recusa executar se `PREP_CITY` já existe.
- `scripts/prep_validate_export.py`: exporta os 33 arquivos e reimporta o catálogo. Para uma nova execução use uma nova pasta de exportação, pois os arquivos existentes são protegidos.
- `scripts/prep_test_pipeline.py`: verificações de idempotência, pivôs, transformação explícita segura, bloqueio de hierarquias e sobrescrita.
- `scripts/prep_render_kit.py`: cria a base de apresentação e renderiza. No arquivo entregue a base já existe; use o render normal para uma nova imagem.

Não execute novamente a construção sobre o kit pronto. Os três scripts de biblioteca foram executados no Blender; uma incompatibilidade inicial no grupo glTF foi corrigida antes da reimportação bem-sucedida. A cena vazia da tentativa interrompida pode permanecer como registro; não contém o kit validado.

## Frontend recuperado

Fonte recuperada da pasta local `2026-09-14/referenced-chatgpt-conversation-this-is-an/work/stage41-fixed`, preservada sem alterações. Este é um ponto de recuperação encontrado, não uma afirmação de que corresponde à última versão perdida. As dependências locais foram recuperadas para permitir validação; não houve instalação limpa a partir de um lockfile.

Na pasta `frontend`, com Node/npm disponíveis:

```text
npm install
npm run dev
npm test
npm run build
```

Build Vite 8.3.0 concluído: 577 módulos. Avisos preexistentes sobre `eval` em eruda e bundle maior que 500 kB. **8 testes passaram** (6 do frontend recuperado e 2 de arquivos GLB/registro). O comando de testes recuperado apontava para uma pasta ausente; foi ajustado para os testes realmente existentes.

O catálogo foi reimportado no Blender: 32 meshes, limites e pivôs com erro máximo medido de **0 m**. Os 33 arquivos têm estrutura GLB, nomes, UVs e texturas embutidas conferidos. A inspeção visual foi feita no render Blender; a aparência dos GLBs no navegador e o fluxo completo do jogo ainda não foram testados. Os modelos estão disponíveis no registro; a montagem de um bairro jogável pertence à fase seguinte.

## Referência

`manual_definitivo_jogos_lowpoly_3d.pdf`, revisão 07, fornecido na conversa: convenções de nomes, preservação de pivôs, exportação selecionada GLB +Y Up e reimportação. As orientações para Blender 4.5 foram adaptadas e executadas no Blender 5.2.2 LTS instalado, sem alterar o manual.
