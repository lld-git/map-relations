# ADR 010 — Reconhecimento do MinerU Basic (B04d, fase 6, B.3)

**Data:** 2026-11-19
**Status:** aceito (reconhecimento; nenhum adaptador escrito)

## Contexto

O plano B04d (B.3) registrou que a documentação oficial do MinerU não
especifica os campos de saída, as unidades nem a origem da bbox, e que o
formato mudou de nome entre versões. Este bloco não escreve adaptador:
só roda o MinerU uma vez sobre o PDF de teste, num serviço Docker próprio
(`docker/mineru/Dockerfile`, perfil `mineru` do Compose, como o serviço
docling do B04b), e registra aqui os campos reais, a licença e o custo.

## O que mudou desde a redação do plano

A versão testada (**4.2.3**, pinada no Dockerfile) é um redesenho completo
do projeto: já não é a biblioteca `magic-pdf`/`content_list.json` que o
plano original citava. O pacote `mineru` hoje é um CLI orientado a agente
("your personal document center"), com um servidor local (`mineru server`)
e uma biblioteca de documentos própria (SQLite). O parsing de baixo nível
que o plano queria (`content_list.json`/`middle_json.json`) está num
segundo executável **bundado no mesmo pacote**: `mineru-kit parse
<arquivo> -o <dir> --format middle_json --tier basic`, sem precisar do
servidor. É o caminho usado aqui.

Tiers disponíveis: `flash`, `basic`, `standard`, `advanced`. `basic` é o
que o plano chama de "MinerU Basic": roda local, CPU, backend ONNX, sem
VLM. `standard`/`advanced` exigem GPU com 8 GB+ de VRAM (PyTorch + vLLM) —
fora do alcance desta máquina e não testados.

## Execução

```
mineru-kit models download --tier basic         # 13 arquivos ONNX, ~70 s
mineru-kit parse <pdf> -o <dir> --pages 1-40 \
  --format middle_json --tier basic
```

Rodado sobre `o_processo.pdf` (129 páginas), por faixa de 40 páginas (a
mesma faixa do Docling, B04c) — só a primeira faixa (p.1–40) foi
processada; não há adaptador para justificar rodar as quatro.

**Tempo e memória (`/usr/bin/time -v`, container sem GPU):**

| Faixa | Páginas | Tempo (log interno) | Tempo total (wall) | Pico de RSS |
|---|---|---|---|---|
| 1–40 | 40 | 125,3 s (0,319 pág/s) | 2 min 20 s (inclui init dos modelos ONNX) | 3 937 032 KB (≈ 3,75 GiB) |

Comparável ao custo do Docling por faixa (B04c: ~2,45 GiB de pico) — um
pouco mais pesado, mas na mesma ordem de grandeza; cabe no mesmo tipo de
serviço Docker isolado, nunca no CI.

## Campos reais da saída (`middle_json`)

Schema declarado no próprio arquivo: `"schema": "docvortex.middle"`,
`"schema_version": "2.0"` — nome não documentado na página oficial citada
pelo plano. Topo do arquivo:

```json
{"metadata": {...}, "extensions": {...}, "pages": [...],
 "is_full_document": true, "schema": "docvortex.middle", "schema_version": "2.0"}
```

`metadata.document` traz `page_count` (129, físico — confere com
`pdf_loader.page_count` sobre o mesmo PDF) e metadados do PDF (título,
autor, criador). `pages` é uma lista de `{"page_idx": int (0-based),
"blocks": [...]}`.

Cada bloco:

```json
{"type": "text", "index": 2, "bbox": [0.333, 0.754, 0.713, 0.773],
 "content": [{"type": "text", "content": "...", "styles": ["bold"]}]}
```

- `type`: tipos observados nas 40 páginas processadas — `doc_title`,
  `paragraph_title` (ambos com `level` inteiro: 1 e 2 no exemplo — título
  numera profundidade, útil para `LayoutItem.level`), `text`, `image`
  (com sub-bloco `image_body`), `footer`. **Não apareceram** `table`,
  `list_item` nem nenhum tipo de número de página nestas 40 páginas — o
  PDF de teste não tem cabeçalho/rodapé/numeração repetida no corpo (já
  sabido do B04b-prova), então o tier `basic` não teve oportunidade de
  classificar isso; fica sem confirmação até rodar sobre um PDF com
  cabeçalho repetido.
- `bbox`: lista plana `[x0, y0, x1, y1]`, **já normalizada em fração da
  página (0.0–1.0)** — não em pontos nem pixels, ao contrário do Docling.
  **Origem no topo-esquerda**, confirmado por posição: um `paragraph_title`
  de capa com `y0=0.088` aparece no topo da página; um `footer` com
  `y0=0.784` aparece perto da base. É a mesma convenção de
  `layout.BBox`/`normalize_bbox` — um adaptador MinerU não precisaria
  inverter eixo nem dividir por tamanho de página, só reempacotar os 4
  floats.
- `content`: lista de spans, nunca string direta. Um bloco de texto
  simples tem um span (`{"type": "text", "content": "...", "styles":
  [...]}`); blocos compostos (`image`) têm sub-blocos com seu próprio
  `bbox`. `styles` marca formatação (ex.: `"bold"` em falas curtas em
  itálico/negrito no PDF de teste) — não tem equivalente em
  `LayoutItem` hoje; ficaria perdido num adaptador, como acontece hoje
  com o Docling.
- Não há campo `marker` (lista) nem rótulo de número de página nesta
  amostra — ver limitação acima.

## Licença

**Hallucinated-free, lida do pacote, não da página do plano:** o PyPI
declara `License-Expression: LicenseRef-MinerU-Open-Source-License`, cujo
texto (`LICENSE.md` dentro do wheel) é **Apache License 2.0 + termos
adicionais**:

1. Uso comercial livre, exceto se MAU consolidado > 100 milhões **ou**
   receita mensal > USD 20 milhões — acima disso, exige licença comercial
   separada.
2. Obrigação de atribuição: serviço online baseado em MinerU para
   terceiros deve indicar claramente o uso do MinerU.
3. Descumprimento de 1 ou 2 encerra a licença automaticamente.

Nenhum dos limiares de 1 se aplica a este projeto hoje. O item 2
(atribuição) se aplicaria à aplicação web final (v1-5), se ela expuser
parsing via MinerU a terceiros — registrar quando esse bloco existir.

**Pendência que não foi possível resolver aqui:** o plano pede "confirmar
a licença no `LICENSE` do repositório" — **este repositório não tem
arquivo `LICENSE`** (não há remoto no GitHub ainda, ver `docs/status.md`).
Não é uma omissão desta sessão: a escolha da licença do próprio projeto é
decisão do Leon, não algo para o código decidir sozinho. Registrado como
pendência.

## Consequência

Sem adaptador: `LayoutItem.converter == "mineru"` não existe ainda em
nenhum registro (`CONVERTERS` em `__main__.py` só tem `docling` e
`pdf_loader`). Quando o adaptador for escrito, a tradução de bbox é
trivial (já fração, já topo-esquerda); a tradução de `type` precisa de
mais dados reais — rodar sobre um PDF com cabeçalho/rodapé/tabela/lista
repetidos antes de fechar o mapa de rótulos (equivalente à tabela B.2 do
plano, hoje só preenchida para o Docling).

O serviço Docker (`docker/mineru/Dockerfile`, perfil `mineru`) fica no
repositório para a próxima sessão repetir a extração sem redescobrir a
versão nem o CLI.

## Três achados

Apareceu footer num livro sem rodapé. O MinerU rotulou como rodapé algo perto da base de alguma página. Pode ser a capa ou o crédito do site, mas pode ser texto do corpo. É exatamente o caso que a camada comum resolve: o rótulo vira só sugestão, e a faixa do corpo decide. Vale conferir o conteúdo desse bloco quando o adaptador for escrito.

Formatação (styles): negrito e itálico existem no MinerU, e o Docling também guarda formatação. Hoje o LayoutItem descarta isso. Vale acrescentar um campo opcional styles no adaptador: o subtítulo de capítulo costuma vir em itálico, e esse sinal ajuda a classificar sem regra de texto.

Sem list_item: o MinerU não separou as falas em itens de lista. Se ele mantiver o travessão no texto, resolve de graça o problema do marcador perdido no Docling. Confira na comparação contando os travessões na saída dos dois conversores e na camada de texto do PDF