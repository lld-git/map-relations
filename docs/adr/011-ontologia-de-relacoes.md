# ADR 011 — Ontologia de relações versionada

**Data:** 2026-11-21
**Status:** aceito (decisões D1–D6 fechadas por Leon na mesma data)

## Contexto

Os tipos de relação precisam ser estáveis entre execuções, gabarito e porte
para TypeScript. O `RelationType` sozinho não expressa hierarquia, inversa nem
disjunção. A `claim_key` recebia a flag `symmetric` do chamador, o que permitia
passar a flag errada, e o modelo não distinguia o que a narração afirma do que
uma personagem alega.

## Decisão

- **Fonte:** YAML único (`contracts/ontology/relations.yaml`), com ids estáveis
  e obsolescência em vez de remoção. Versão inteira por arquivo e por tipo.
- **Mudança semântica = id novo** (definition, domain, range, symmetric,
  irreflexive, parent); mudança editorial só sobe `version`.
- **Trava** (`relations.lock.json`, gerada): impede apagar, reaproveitar ou
  mudar ids publicados. Só acrescenta entradas.
- **Hierarquia (D1):** dois níveis; o abstrato não é anotável e não tem pai.
- **Inversa:** só visão de consulta, normalizada por `Ontology.canonicalize`.
- **Disjunção (D5):** recíproca, vale para o par não ordenado, e é **alerta**
  (`Ontology.disjoint_conflicts`), não rejeição, até existir janela temporal.
  **Irreflexividade** continua rejeição.
- **Mappings (D4):** só equivalência exata; o aproximado fica em `mappings_note`.
- **`RelationType` gerado, sem campos novos** (`id` = slug da ontologia).
- **`claim_key(s, relation_type, o, *, asserted_by, narrative_scope)` (D3):** a
  simetria vem do `RelationType`; `asserted_by` e `narrative_scope` entram no
  hash só quando não são `None` (chave de claim comum inalterada); a classe
  fica fora da chave (`afirmada` e `inferida` do mesmo trio são a mesma claim).
- **`rules.new_claim`** é o único caminho de criação: rejeita tipo abstrato
  (`AbstractType`), obsoleto (`ObsoleteType`), reflexivo em tipo irreflexivo
  (`ReflexiveClaim`) e kind incompatível.
- **Classe `alegada`** com `asserted_by` obrigatório se e somente se alegada.
- **`narrative_scope` (D2):** `obra | texto_encaixado`; `None` = `obra`. A V1
  avalia só `obra`; relações de `texto_encaixado` saem dos dois lados e são
  contadas à parte; as não marcadas pelo modelo contam como falso positivo.
- **Gabarito de obra protegida** em `data/golden/`, fora do Git; `eval/gold/` só
  para domínio público e dados sintéticos.

## Consequências

- Renomear tipo depois do congelamento custa um id novo. Antes de qualquer
  publicação da trava a renomeação é simples: `vigia` virou
  `exerce_vigilancia_sobre` nesse regime (relatório do B02a).
- Claims antigas de tipo obsoleto continuam legíveis (`relation-types.json`
  inclui obsoletos).
- A trava protege só a parte semântica dos abstratos (não têm `version`).
- A regra do verificador para `alegada` fica para o B05.
- O B02 depende deste bloco. D5 será revista quando o `timeScope` entrar no pipeline.
