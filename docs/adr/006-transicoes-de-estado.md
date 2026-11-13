# ADR 006 — Tabela de transições de estado

**Data:** 2026-11-10  
**Status:** aceito

## Contexto

Claims e participations compartilham o mesmo ciclo de vida
(`proposta | verificada | rejeitada | confirmada_humano | rejeitada_humano`).
O Princípio 5 do CLAUDE.md exige que decisão humana nunca seja sobrescrita
por novo processamento. É preciso uma tabela única, testável por pares,
implementada em `core/states.py: validate_transition`.

## Decisão

Regras por ator:

- **auto** move livremente entre `proposta`, `verificada` e `rejeitada`
  (qualquer direção — reprocessamento pode reverter uma verificação anterior).
- **auto nunca altera** `confirmada_humano` nem `rejeitada_humano`.
- **humano** move de **qualquer** estado para **qualquer estado humano**
  (`confirmada_humano` ou `rejeitada_humano`), inclusive corrigindo a si
  mesmo (`confirmada_humano → rejeitada_humano` e vice-versa).
- Humano não devolve um item a estados automáticos (`proposta`, `verificada`,
  `rejeitada`): a revisão humana é sempre expressa num estado humano.
- Transição para o mesmo estado é inválida (no-op não gera ChangeLog).

Tabela completa (✓ permitida, ✗ proibida):

| De \ Para            | proposta | verificada | rejeitada | confirmada_humano | rejeitada_humano |
|----------------------|:--------:|:----------:|:---------:|:-----------------:|:----------------:|
| proposta             |    —     |  ✓ auto    |  ✓ auto   |     ✓ humano      |     ✓ humano     |
| verificada           |  ✓ auto  |     —      |  ✓ auto   |     ✓ humano      |     ✓ humano     |
| rejeitada            |  ✓ auto  |  ✓ auto    |     —     |     ✓ humano      |     ✓ humano     |
| confirmada_humano    |    ✗     |     ✗      |     ✗     |         —         |     ✓ humano     |
| rejeitada_humano     |    ✗     |     ✗      |     ✗     |     ✓ humano      |        —         |

**Toda transição aplicada gera uma entrada de ChangeLog** com
`action=state_change`, `actor` (auto | humano), `before`/`after` e `run_id`
ou `pass_id` quando originada de processamento
(`core/rules.py: transition`).

## Consequências

- `validate_transition(current, new, actor)` é a implementação direta desta
  tabela; os testes parametrizam todos os 5×5×2 pares (ator × origem × destino).
- Upsert no reprocessamento (ADR 003) passa pela mesma validação: registro
  existente em estado humano não é alterado pela proposta nova.
- Se um dia for necessário "reabrir" um item decidido por humano, isso será
  uma nova decisão explícita neste ADR — hoje é proibido.
