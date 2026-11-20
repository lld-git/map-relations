# ADR 009 — Camada comum de layout entre conversores (Opção B do B04d)

**Data:** 2026-11-19
**Status:** aceito

## Contexto

O plano [B04d](../plans/B04d.md) apontou dois erros reais de conversão do
Docling — falso cabeçalho (item dentro da área de texto do corpo rotulado
como `page_header` e removido) e número de página sobrando no texto — e
ofereceu duas opções para corrigi-los:

- **Opção A — mínima:** a regra da faixa do corpo só na rota Docling
  (`ingest/convert_docling.py`).
- **Opção B — completa:** a mesma regra, mas numa camada comum
  (`LayoutItem`, `ingest/layout.py`) entre conversores, preparada para o
  MinerU.

## Decisão

Opção B. Motivo: o pdf_loader já tinha sua própria versão, com código
diferente, da mesma lógica que a Opção A corrigiria só no Docling —
remoção de cabeçalho/rodapé por repetição e junção de parágrafo que
atravessa página. Corrigir só o Docling teria deixado as duas rotas ainda
mais divergentes (uma com a faixa do corpo, outra sem), e qualquer
conversor futuro (MinerU) teria que reimplementar a lógica de novo. A
camada comum paga esse custo uma vez: `LayoutItem` (dataclass imutável,
não Pydantic — estrutura de passagem interna, nunca em
`contracts/schemas`) e as regras de pós-processamento (`join_crossing_items`,
`classify_titles`, `drop_page_furniture`, `compute_body_band` +
`apply_body_band`) ficam em `ingest/layout.py`, escritas uma vez; cada
conversor só traduz sua saída nativa para `LayoutItem[]` (adaptador fino,
sem decisão).

## Migração sem mudar comportamento (fases 0-4)

Princípio: refatoração pura primeiro, regra nova depois, cada fase um
commit com a suíte verde. `classify_titles` (Docling, com sinal fraco via
`LayoutLabel.titulo` e promoção a subtítulo) e `canonical.classify_headings`
(pdf_loader, sinal fraco via heurística de maiúsculas, sem subtítulo)
**não foram unificadas**: são sinais de título de natureza diferente (um
estrutural do conversor, outro heurística de texto) e alertam com
mensagens literalmente diferentes que `alerts.py`/`test_ingest_contract`
casam por texto — ver pendência em `docs/status.md` e a tentativa registrada
nesta sessão.

## Regra nova (fase 5)

`compute_body_band` mede a faixa vertical típica do corpo por percentis
(5º/95º) sobre todas as bboxes de itens de corpo do documento inteiro (não
por página nem por faixa de conversão do B04c — um corte só, calculado
depois do merge). `apply_body_band` usa essa faixa: cabeçalho/rodapé
**dentro** volta a ser texto, na posição original; **fora** é removido;
número de página fora da faixa é removido mesmo rotulado `text`, mas
número dentro (citação no meio do parágrafo) é mantido. Sem faixa confiável
(poucas páginas, ou item sem bbox — caso do pdf_loader) o comportamento é o
de antes da fase 5, com alerta.

## Consequência

`convert_docling.py` e `canonical.py` (rota pdf_loader) viraram adaptadores
finos sobre `ingest/layout.py`. `docling_compare.compare` (fase 6, ver ADR
010) passa a operar sobre `LayoutItem[]` em vez do JSON nativo do Docling,
o que permite `make compare --converter <nome>` comparar qualquer
conversor registrado contra o pdf_loader, não só Docling — sem precisar
reescrever o relatório para cada formato novo.

## Pendências desta decisão

- MinerU: reconhecimento feito (ADR 010), adaptador não escrito.
- Unificação de `classify_titles`/`classify_headings`: registrada como
  pendência em `docs/status.md`, não resolvida.
