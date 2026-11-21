# ADR 003 — IDs estáveis: UUID como identidade, chaves de conteúdo para upsert

**Data:** 2026-11-10  
**Status:** aceito

## Contexto

Reprocessar um documento não pode duplicar claims nem perder decisões humanas.
IDs derivados de conteúdo quebram quando a normalização de texto muda entre
implementações; IDs aleatórios puros impedem reconhecer "a mesma claim" num
novo processamento.

## Decisão

Dois mecanismos complementares:

1. **Identidade: UUIDv4** gerado na criação (`core/ids.py: new_id`). Opaco,
   nunca derivado de conteúdo, nunca reaproveitado. Evidence, ChangeLog e Note
   referenciam objetos por esse id.

2. **Chaves de conteúdo** (sha256, únicas por projeto) usadas para upsert no
   reprocessamento:
   - `claim_key = hash(subject_id, type_id, object_id)` (desde o ADR 011, calculada
     por `claim_key(s, RelationType, o, *, asserted_by, narrative_scope)`; ver lá) — para tipos simétricos
     (`RelationType.symmetric = True`), `subject_id` e `object_id` são ordenados
     lexicograficamente antes do hash, de modo que A→B e B→A produzam a mesma chave.
   - `participation_key = hash(event_id, entity_id, role)`
   - `evidence_key = hash(source_content_hash, start, end)`

   Os componentes são concatenados com separador `\x00` antes do hash para
   evitar colisões por justaposição.

No reprocessamento: se a chave já existe no projeto, a proposta nova faz
upsert sobre o registro existente — preservando o UUID e, portanto, o estado.
Estados humanos nunca são sobrescritos (ADR 006).

## Consequências

- O verificador e o painel sempre referenciam UUIDs; as chaves são detalhe
  do pipeline de ingestão/extração.
- Mudar `relation_type.version` não muda a `claim_key` (usa `type_id`);
  uma nova versão do tipo é um novo `type_id` se a semântica mudar.
- `evidence_key` depende do `content_hash` da fonte: texto novo → evidências
  novas, como esperado.
