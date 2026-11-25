# Documentação

Ponto de entrada das pastas de `docs/`. O estado atual do trabalho está em
[status.md](status.md); o site local (`make docs`, http://127.0.0.1:8020) reúne tudo.

| Pasta | O que guarda | Quando é escrita |
|---|---|---|
| [plans/](plans/) | **Antes.** Plano de um bloco: o que fazer, decisões em aberto, fases, critério de pronto. | Antes de implementar o bloco, com aprovação do Leon. |
| [blocks/](blocks/) | **Depois.** Relatório de conclusão de cada bloco (verbatim, com commit e data no topo e a seção "Revisão humana" para o humano preencher). | Ao concluir o bloco. |
| [adr/](adr/) | **Decisões.** Um registro por decisão relevante, numerado e imutável depois de aceito. | No momento da decisão. |
| [mapa/](mapa/) | **Gerado do código.** Grafo de imports, candidatos a código morto, fluxo e lista de arquivos. Não editar à mão; `make map` regenera. | Ao concluir cada bloco. |
| [old/](old/) | **Arquivo morto.** Versões antigas da especificação; só para consulta histórica. | Nunca mais. |

Arquivos soltos: [status.md](status.md) (estado e handoff), [architecture.md](architecture.md)
(contratos e camadas), [phases.md](phases.md) (fases e checkpoints) e
[mapa_rel_v1-5.md](mapa_rel_v1-5.md) (especificação vigente).

## Site local

`make docs` serve o site (Zensical) em http://127.0.0.1:8020; `make docs-stop` para;
`make docs-build` gera `site/` (no .gitignore) e falha se a conversão falhar. Nada é
publicado. A navegação está em `zensical.toml`: ao criar um arquivo em `adr/`, `blocks/`
ou `plans/`, acrescente-o lá (o site só lista o que está na navegação).

**Limitação conhecida:** o Zensical 0.1.3 não embute o Mermaid; carrega
`mermaid.min.js` de `unpkg.com` ao abrir a página. Com internet, os diagramas de
`architecture.md` e `mapa/fluxo.md` aparecem (conferido em Chrome headless com captura de
tela); sem internet, a página mostra o espaço vazio no lugar do diagrama. O código-fonte do
diagrama continua legível nos arquivos `.md`.
