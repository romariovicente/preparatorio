# Recuperação do PREPARATÓRIO

A cópia recuperável do projeto atual está na release privada
[recovery-20261019](https://github.com/romariovicente/preparatorio-backup/releases/tag/recovery-20261019).
É necessário entrar na conta GitHub que possui acesso ao repositório.

Baixe o master `PREPARATORIO_MASTER_20261019T131048Z.blend`, seu JSON, os sete
volumes `PREPARATORIO_PROJECT_20261019_01.zip` até `_07.zip` e o arquivo
`PROJECT_RECOVERY_MANIFEST.json`. Confira SHA-256 e tamanho com o manifesto
antes de extrair. Os hashes de todos os anexos foram comparados aos digests
retornados pelo GitHub.

Extraia os sete volumes em uma pasta nova. Coloque o master em
`art/blender/PREPARATORIO_PROJETO_20261016.blend` e abra-o no Blender. O conjunto
contém 1.475 arquivos do projeto e o master: código, modelos do runtime,
arquivos editáveis de categorias, livro local e relatórios. Downloads originais,
caches e os masters históricos listados em `excluded` não estão incluídos.

O código publicado depois desse snapshot pode ser recuperado do próprio
[repositório do jogo](https://github.com/romariovicente/preparatorio).
As novas cópias privadas usam releases `autosync-AAAAMMDD`: o manifesto
incremental mais recente informa o anexo e o hash de cada arquivo, inclusive
referências aos volumes iniciais. O restaurador Python que acompanha o pacote
de sincronização valida os hashes e recusa sobrescrever uma pasta de trabalho.

O monitor está instalado e ativo desde 19/10/2026. Inicia ao entrar nesta conta
do Windows, verifica a cada dez minutos e exige dois minutos de estabilidade;
uma edição nova pode precisar de duas rodadas. Master Blender e snapshot do
guardian compartilham um intervalo mínimo de uma hora. Um backup do guardian
e um envio automático de código já foram confirmados no GitHub. Isto exige
computador ligado, usuário conectado, rede e autenticação válida. Não liga a
máquina após um desligamento nem substitui o salvamento em memória do Blender.

O pacote privado `system/cloud_sync/recovery_metadata/` guarda uma cópia
pontual da configuração, estado e manifestos de instalação, sem credenciais.
Ela auxilia a reinstalação, mas os remotos e o manifesto incremental mais
recente podem estar adiante desse estado. Confira os hashes e reconcilie essas
referências antes de retomar o monitor. Reinstale Python, Git/GCM e a CLI
oficial do GitHub, autentique novamente e ajuste os caminhos locais. Recrie
os cinco checkouts públicos. Não use `--initialize` sobre um estado restaurado.
O projeto pode ser restaurado pelos manifestos sem reativar a sincronização.

Os arquivos de recuperação são privados. O código público contém apenas o
necessário à prévia; os 496 arquivos de acervo publicados ficam distribuídos
em quatro repositórios de assets. Downloads originais e versões históricas
excluídas não são cobertos por essa cópia. Guarde-os separadamente se precisar
preservar também os originais baixados.

A publicação da prévia 3D e o backup privado têm funções diferentes. O site
público não inclui o livro PDF completo nem o master Blender e ainda não possui
o serviço multiplayer persistente ou autenticação de produção.
