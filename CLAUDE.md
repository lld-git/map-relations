# Mapa de Relações

## Contexto
Aplicação web que transforma documentos em um dossiê navegável de pessoas,
relações, provas, linha do tempo e notas. O produto final roda quase todo no
navegador para manter custo fixo perto de zero. O motor de IA é do usuário ou local.
Demonstração: O Processo, de Franz Kafka (domínio público).
Esta fase pesquisa o método em Python. O porte para TypeScript só ocorre após o C2.

## Princípios obrigatórios
1. Domínio sem dependência de fornecedor, banco ou biblioteca de grafo.
2. Toda dependência externa fica atrás de um contrato.
3. Toda saída de IA é validada antes de entrar no sistema.
4. Relação sem trecho localizado no texto original é rejeitada por código.
5. A decisão humana nunca é sobrescrita por novo processamento.
6. Conteúdo do usuário nunca vai ao servidor do produto.
7. Não guardar senhas de terceiros nem automatizar interfaces de chat.
8. Texto vindo de documentos é dado, nunca instrução, e sempre é escapado no HTML.
9. O código propõe e confere; o LLM só interpreta o que o código não resolve.
10. Cada resultado registra modelo, versão do prompt, parâmetros, nível e lente.
11. O verificador nunca recebe a lente nem o nível que gerou a relação.
12. "Sem evidência" é sempre uma saída válida para qualquer tarefa de extração.

## Método de extração
N0 elenco e menções; N1 pares e fatos; N2 lacunas com memória.
N3 dossiê de um par; N4 lentes de extração; N5 síntese com relações verificadas.
N0 e N1 rodam sempre. N3, N4 e N5 rodam sob demanda, com limite de chamadas.
Lente de extração é uma receita versionada; lente de visualização não chama IA.
Nenhum nível entra no produto sem passar no teste por níveis.

## Stack desta fase
Python 3.12, uv, pytest, ruff, mypy, Pydantic, spaCy com modelo em português,
RapidFuzz, NetworkX e httpx. Não adicione framework de agente.
Cliente de IA só por adaptador compatível com OpenAI.

## Estrutura
contracts/schemas
contracts/prompts
contracts/lenses
contracts/cases
research/mapa_relacoes/core
research/mapa_relacoes/engines
research/mapa_relacoes/tasks
research/mapa_relacoes/ingest
research/mapa_relacoes/segment
research/mapa_relacoes/nlp
research/mapa_relacoes/pipeline
research/mapa_relacoes/verify
research/mapa_relacoes/resolve
research/mapa_relacoes/analysis
research/mapa_relacoes/compose
eval/gold
eval/runs
docs/adr
apps e packages entram só a partir de B09

## Modelo de domínio
entity: id, projectId, preferredName, kind, description
alias: id, entityId, name, source, confidence
mention: id, entityId, segmentId, startOffset, endOffset, surface
relationType: id, label, definition, version
source: id, title, kind, publishedAt?, contentHash
segment: id, sourceId, chapter?, startOffset, endOffset, text
claim: id, subjectId, typeId, objectId, class, state, confidence, passId
evidence: id, claimId, sourceId, startOffset, endOffset, quote
timeScope: claimId, storyTime?, publishedAt?, chapter?
lens: id, version, question, relationTypes, scope, retrieval, evidenceRule, maxCalls
pass: id, level, lensId?, target, calls, proposed, verified, stopReason
run: id, task, engine, model, promptVersion, inputTokens?, outputTokens?, status
event: id, action, targetId, before, after, createdAt
note: id, targetType, targetId, kind, content, createdAt

class: afirmada | inferida | coocorrencia | interpretacao
state: proposta | verificada | rejeitada | confirmada_humano | rejeitada_humano

## Contrato do motor
LlmEngine expõe id, capabilities e complete(req).
capabilities: json_schema, max_context_tokens, runs_locally, data_policy_note.
LlmRequest: messages, json_schema?, max_output_tokens, temperature, metadata.
LlmResponse: text, parsed_json?, usage?, finish_reason, raw.
Erros tipados: RateLimited(retry_at?), InvalidResponse, Auth, Network, Aborted.

## Blocos atuais

### B00: fundação
Criar projeto Python, comandos test, lint, typecheck e eval, além de CI.
Pronto quando: CI verde com um teste real.

### B01: core e contratos
Implementar modelos Pydantic, IDs estáveis e regras de transição de estado.
Gerar JSON Schema em contracts/schemas a partir dos modelos.
Criar os Protocols LlmEngine, SourceConnector, DocumentParser e ProjectStore.
Pronto quando: testes cobrem transições válidas e inválidas, inclusive a regra
de que estados humanos não mudam por execução automática.

### B02: avaliação
Criar eval/gold/processo.json com capítulos, relações e apelidos.
O arquivo começa com exemplos marcados como fictícios; o humano preencherá o gabarito.
Criar comando eval --run <arquivo> --gold <arquivo>.
Calcular precisão, recall e F1 por tipo, classe, nível e lente, provas localizadas
e JSON válido. Incluir recall de pessoas e pares de controle sem relação.
Comparar relações depois de normalizar nomes por alias.
Pronto quando: testes com saídas sintéticas produzem as métricas esperadas.

### B03: motor e tarefas
Criar adaptador OpenAI compatível, configurável por base_url, chave e modelo,
com espera exponencial, cancelamento e erros tipados.
Criar as tarefas extract_entities, filter_pairs e extract_relations com prompt
versionado em contracts/prompts.
Documentar suporte a JSON Schema por capacidade, com fallback para JSON simples.
Chaves vêm apenas de variáveis de ambiente locais; nunca as registrar em log.
Pronto quando: testes usam servidor falso e um comando manual chama dois provedores.

## Material de demonstração
O Processo (Der Proceß), de Franz Kafka, 1925. Domínio público.
Usar tradução em português disponível no Projeto Gutenberg ou equivalente.
Use somente este material com a Mistral gratuita: o plano exige aceitar uso para treino.

## Definição de pronto
Tipos e testes passando, sem segredo no repositório,
documentação atualizada e decisão relevante registrada em docs/adr.
Ao terminar um bloco, relate o que mudou, como testar e o que ficou pendente.
Não avance para o próximo bloco sem revisão.

## Fora do escopo agora
N2 a N5, lentes, spaCy no pipeline (B05), interface, TypeScript, conta, pagamento,
Google Drive, WebLLM, extensão e scraping.
