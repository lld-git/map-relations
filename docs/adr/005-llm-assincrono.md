# ADR 005 — LlmEngine assíncrono; domínio síncrono

**Data:** 2026-11-10  
**Status:** aceito

## Contexto

Chamadas a LLM têm latência de segundos e os níveis N3–N5 fazem várias
chamadas por passada. Async permite concorrência sem threads. Mas espalhar
async pelo domínio contamina tudo (função síncrona não chama async) e
complica testes de regras puras.

## Decisão

1. **Apenas `LlmEngine.complete()` é `async def`.** Modelos, transições de
   estado, validações e regras de domínio são síncronos e puros.
2. **A camada de tarefa** (`tasks/`, a partir do B03) **é assíncrona**:
   orquestra chamadas concorrentes com `asyncio.gather` e limita concorrência
   com `asyncio.Semaphore` (respeitando `max_calls` da lente e rate limits).
3. **Nada de `asyncio.run()` por chamada.** Um único event loop por comando,
   criado no ponto de entrada (CLI ou painel). A lógica de domínio nunca chama
   `complete()` diretamente — recebe resultados já resolvidos.

## Consequências

- Testes de domínio não precisam de `pytest.mark.asyncio`; só os de tarefa.
- O adaptador OpenAI (B03) usa `httpx.AsyncClient`.
- Cancelamento (erro `Aborted`) propaga pelo `gather` naturalmente.
- O painel FastAPI (B02b) já roda em event loop próprio; tarefas se integram
  sem ponte síncrono→assíncrono.
