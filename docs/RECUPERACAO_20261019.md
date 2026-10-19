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

A publicação da prévia 3D e o backup privado têm funções diferentes. O site
público não inclui o livro PDF completo nem o master Blender e ainda não possui
o serviço multiplayer persistente ou autenticação de produção.
