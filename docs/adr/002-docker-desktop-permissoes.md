# ADR 002 — Permissões de volume no Docker Desktop para Linux

**Data:** 2026-11-10  
**Status:** aceito

## Contexto

No Docker Desktop para Linux, o daemon roda numa VM leve (LinuxKit). Volumes
bind-mounted aparecem dentro do contêiner com UID 0 (root), independentemente
do proprietário no host. Isso faz com que o `appuser` (UID 1000) não consiga
gravar em diretórios montados como `./eval` ou `./data`, causando
`Permission denied` ao tentar criar arquivos em `eval/runs/`.

No Docker Engine nativo (Linux sem Desktop), o mapeamento de UIDs é direto:
o proprietário no host é preservado dentro do contêiner, e o `appuser`
consegue gravar normalmente desde que o diretório pertença ao mesmo UID.

## Decisão

- **docker-compose.yml** (desenvolvimento local com Docker Desktop): usar
  `user: "0:0"` nos serviços `app` e `painel`. O root do contêiner corresponde
  ao usuário do host — não há escalada de privilégio real.
- **Dockerfile** (CI e deploy): mantém `USER appuser` (UID 1000). Em CI o
  runner usa Docker Engine nativo; em deploy não há volumes bind-mounted.
- O `appuser` continua sendo o padrão da imagem. Para sobrescrever em outros
  ambientes (Docker Engine nativo no host do desenvolvedor), basta remover ou
  comentar o `user:` no compose.

## Consequências

- O serviço `app` no compose roda como root localmente; isso é aceitável
  porque o contêiner não aceita entrada de rede e só processa arquivos locais.
- Testes de escrita em `eval/runs/` que rodam em CI usam a imagem sem
  override de usuário, garantindo que o `appuser` consegue gravar no caminho
  correto dentro da imagem (sem volume bind-mounted).
- Revisar esta decisão se o projeto migrar para Docker Engine nativo no
  ambiente de desenvolvimento.
