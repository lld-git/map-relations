# ADR 012 — Formato do gabarito e âncora de evidência

**Data:** 2026-11-21
**Status:** aceito (plano do B02 aprovado por Leon, §3, §4 e D1–D4, D7)

## Contexto

O rascunho do gabarito guardava cada prova como citação mais offset, e o offset
envelhece: quando o canônico mudou (hash `46a0…` → `7a25…`), 38 dos 40 offsets
ficaram errados e nenhum deslocamento único os corrigia. Entidades eram citadas
por nome, sem id, e o resultado esperado dos pares de controle era texto livre.

## Decisão

- **Arquivo:** `GoldFile` (`research/map_relations/evaluation/gold.py`), com JSON
  Schema gerado em `contracts/schemas/gold.schema.json` e conferido pelo
  `generate_schemas --check` (CI). Nomes dos campos como no plano (`preferredName`,
  `startOffset` e `endOffset` em camelCase; o resto em snake_case).
- **Ids de entidade (D1):** slugs legíveis, válidos só dentro do arquivo; o
  mapeamento para os UUIDs do domínio (ADR 003) é do B05.
- **Id da relação:** `r_` + 12 primeiros hex da `claim_key` (simetria lida do
  `RelationType`, `asserted_by` e `narrative_scope` na chave, classe fora), então
  o id é estável entre versões do arquivo. A visão inversa é normalizada por
  `Ontology.canonicalize` antes de calcular a chave.
- **`narrative_scope` obrigatório** no gabarito (sem a ausência implícita do
  domínio): o anotador decide sempre. `chapter` nunca é gravado: vem de `locate()`.
- **Âncora** = TextQuoteSelector (`exact`, `prefix`, `suffix`) + TextPositionSelector
  (`startOffset`, `endOffset`), em code points sobre o canônico NFC, fim exclusivo
  (ADR 004).
  - Invariante: `text[start:end] == exact`, com `prefix` logo antes e `suffix` logo
    depois (cortados na borda do texto) e `end - start == len(exact)`.
  - **Mínima suficiente:** `prefix + exact + suffix` ocorre uma vez no canônico.
    Contexto padrão de 32 code points por lado, crescendo até 128 no fill-offsets
    (D7), que ainda não existe neste commit.
  - **A citação com o contexto é a verdade; a posição é o atalho.** Quando
    divergem, vale a citação e a posição é reconstruída.
  - **Nunca chute:** ocorrência ambígua ou ausente é erro listado, nunca escolhida
    pelo offset antigo, por distância, ordinal ou casamento aproximado (D4).
- **Evidências (revisão de 2026-11-24).** Cada relação tem `evidence`, lista de 1 ou
  mais, e cada item guarda só decisões de anotação: `chapter`, `anchor`
  (`exact` obrigatório; `prefix`, `suffix` e offsets preenchidos pelo fill-offsets),
  `support` (`alto | medio | baixo`), `polarity` (`apoia | contradiz`) e `note`
  opcional. `chapter` é conferido contra `locate(startOffset)`; divergência é erro.
  - **Provada** se há evidência `alto` que `apoia`, ou se a relação declara
    `provas_em_conjunto: suficiente`. Contradição não prova nem soma.
  - **O peso não decide.** `prova_status` (peso alto=3, medio=2, baixo=1, só das que
    apoiam) apenas gera um **alerta** quando o conjunto foi declarado suficiente e a
    soma fica abaixo do corte (4). Relação sem prova também sai como alerta.
  - **Pesos e corte são provisórios**, a calibrar no B03 com execuções reais
    (constantes `SUPPORT_WEIGHTS` e `CONJOINT_CUTOFF` em `gold.py`).
  - **O gabarito não guarda nada calculado:** nem `quote` (duplicaria `anchor.exact`),
    nem `support_profile`, `support_weight`, `prova_status` ou `also_in_chapters`.
    `extra="forbid"` rejeita esses campos. Os valores existem só no relatório
    (`GoldReport.proofs`, impresso por `gold validate`).
  - A conversão do rascunho antigo cria **uma evidência alta que apoia** por relação,
    com o capítulo do rascunho (já conferido contra `locate()`).
- **Nomes e ids.** A anotação usa nomes em `subject`, `object` e `asserted_by`; a
  conversão os mapeia para o id da entidade por casamento **exato** com
  `preferredName` ou `aliases`. Nome desconhecido, ou que casa com duas entidades, é
  erro listado; nunca há casamento aproximado. Entidade nova declarada na anotação
  ganha o id gerado do `preferredName` (casefold, sem acento, `_`), uma função pura do
  nome: o mesmo personagem tem o mesmo id em todos os capítulos. Dois nomes com o
  mesmo id são colisão e erro.
- **Validação em duas camadas:** o modelo Pydantic cobre regras locais (classe ×
  `asserted_by`, `origin_detail.model`, invariante interna da âncora, hash no
  formato `sha256:<64 hex>`); `validate_gold` cobre ontologia, referências, duplicatas
  de `claim_key`, hash e âncoras contra o canônico e pares de controle. Disjunção é
  alerta, não erro. Hash diferente do canônico atual é erro com "rode fill-offsets".
- **`fictional: true`:** exemplos do arquivo; não citam a obra, então suas âncoras
  e pares de controle não são conferidos contra o canônico.
- **`Evidence` do domínio não muda** neste bloco; levar `prefix`/`suffix` a ele é
  entrada do B05.

## Consequências

- Editar o `documento.md` muda o hash: o gabarito é recusado até o fill-offsets
  (próxima fase) regravar as posições. Se a edição alterar a própria citação, o
  erro `nao_encontrada` é o comportamento correto.
- Citações curtas e repetidas dependem do contexto; o que o contexto não resolver
  vira erro para o humano.
- O gabarito pode ser anotado só com a citação (modo âncora mínima, fase 2): o
  `Anchor` deste ADR é o formato completo, gravado pelo fill-offsets.
