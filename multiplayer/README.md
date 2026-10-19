# Sala compartilhada local do PREPARATÓRIO

Este servidor mantém o estado dos objetos de duas salas, `campus` e `hospital`, na memória do processo. Ele usa apenas recursos nativos do Node.js, escuta em **127.0.0.1:5180** e aceita o frontend local em **127.0.0.1:5173** ou **localhost:5173**. `Start-Preparatorio.ps1` inicia a sala junto do frontend.

Abra duas abas independentes do jogo para testar dois jogadores. Cada aba recebe sua própria sessão em `sessionStorage`; recarregar a mesma aba retoma seu jogador enquanto o servidor continua aberto. As posições, a ação atual, as cópias carregadas e as alterações de objetos chegam às outras abas por SSE.

Pegar um objeto base cria uma cópia com dono. Reposicionar uma cadeira ou carrinho base cria uma cópia colocada no destino; o modelo base conserva sua posição. O dono pode carregar, usar, mover, colocar e devolver suas cópias. O servidor obtém a identidade pelo token de sessão, verifica proximidade, espaço livre, revisão do objeto e limites de cópias, e rejeita a edição de itens pertencentes a outro jogador.

O hospital verifica a área ocupada pelas camas, balcão, móveis, visitantes e cópias. O campus verifica a área delimitada, os obstáculos e os jogadores. Conflitos com uma revisão antiga retornam o estado atual para que a interface selecione o objeto novamente.

Para iniciar somente o servidor ou executar a verificação:

```text
cd multiplayer
npm start
npm test
```

Foram testados quatro cenários de integração com um servidor HTTP real, incluindo dois clientes simultâneos, o mesmo adaptador usado pelo frontend e a recuperação depois de reiniciar o servidor na mesma porta. O cliente tenta reconectar após 1, 2, 4 e até 8 segundos; tentativas e streams são cancelados quando a interface fecha. Uma nova sessão reinicia a guarda de revisão, e ações durante a desconexão permanecem bloqueadas. O relatório fica em `../reports/multiplayer_checks_20261002.json`.

Os fluxos também foram conferidos visualmente em duas abas do campus e do hospital, incluindo pegar cópias distintas, colocar, recolher, devolver, dançar e mover uma cópia do carrinho. A interface em 390 × 844 passou na conferência de movimento, rolagem e ausência de overflow horizontal.

A demonstração compartilha abas desta máquina. O estado das salas é reiniciado ao encerrar o processo; ela ainda não inclui contas, banco de dados, hospedagem pública ou conexão entre computadores. O servidor permite até 64 sessões e 256 cópias por sala, além dos limites pessoais definidos pelo redutor compartilhado.
