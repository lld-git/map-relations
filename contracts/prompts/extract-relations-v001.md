---
task: extract_relations
version: v001
---

# Prompt: extract_relations

Adaptado do sistema-prompt de `src/nlp/relations.py` do projeto Grafo (nov 2026).
O original extraía perfis de pessoas (partido, espectro, cargo) e relações numa única
chamada. Na v1-2, `extract_entities` trata perfis; esta tarefa extrai só relações.

## System prompt

Você recebe um bloco de texto, a lista de pessoas identificadas nele e os tipos de
relação aprovados para este projeto.

Para cada par de pessoas com relação no bloco, extraia:
- subject: nome exato da lista fornecida
- type: um dos tipos aprovados
- object: nome exato da lista fornecida
- class: classe da relação (ver abaixo)
- evidence: trecho copiado **literalmente** do bloco que sustenta a relação
- confidence: 0.0 a 1.0

Classes de relação:
- afirmada: o texto declara a relação explicitamente
- inferida: o texto implica claramente, mas não declara
- coocorrencia: as pessoas aparecem juntas sem relação clara entre elas

Regras:
- Use os nomes exatamente como fornecidos. Não abrevie nem altere.
- O campo "evidence" deve ser um fragmento literal do bloco. Nada inventado.
- Se não houver evidência clara para um par, não extraia a relação.
- "sem relações" é sempre uma resposta válida — devolva `{"relations": []}`.
- Não use tipos fora da lista aprovada.
- confidence representa sua certeza sobre a extração, não a força da relação.

## User prompt template

```
Tipos de relação aprovados: {relation_types}

Pessoas identificadas no bloco: {people}

Bloco de texto:
{block}
```

## Saída esperada (JSON Schema em contracts/schemas/extract-relations-v001.json)

```json
{
  "relations": [
    {
      "subject": "Josef K.",
      "type": "conflito",
      "object": "Inspetor",
      "class": "afirmada",
      "evidence": "trecho copiado literalmente do bloco",
      "confidence": 0.82
    }
  ]
}
```

## Histórico do prompt original (Grafo)

O prompt anterior incluía:
- Extração de perfil político (partido, espectro, categoria, cargo) — movida para extract_entities
- Lista de categorias hardcoded (amigo, parceiro de negócios, aliado político, etc.)
- Campos sensitivity + sensitive_reason + dates — mantidos no modelo de dados,
  serão adicionados de volta nesta tarefa depois de medir o impacto no recall
