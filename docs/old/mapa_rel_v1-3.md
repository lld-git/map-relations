# Mapa de Relações: projeto da versão 1

Nov 3, 2026 · @leon

A versão 1 é uma aplicação web que roda quase toda no navegador e transforma documentos em um dossiê navegável, com relações, provas, linha do tempo e notas. O servidor cuida só de conta, licença e assinatura da exportação; o motor de IA é do usuário ou roda na máquina dele. Isso mantém o custo fixo perto de zero enquanto a demanda é testada.

## Produto e decisões

**Promessa:** enviar uma obra ou um conjunto de documentos e receber um mapa que mostra o que a leitura linear não evidencia, com cada afirmação ligada ao trecho original.

| Tema | Decisão da V1 | Motivo |
| --- | --- | --- |
| Público inicial | Comentaristas e criadores que precisam citar fontes | É o grupo mais provável de pagar; geek e religioso servem para demonstração |
| Demonstração | *O Processo*, em domínio público | Curto, em português e sem risco de direitos autorais |
| Processamento | No navegador, em Web Workers | Sem custo de servidor por página processada |
| Motor de IA | OpenRouter por PKCE, chave do próprio usuário e modelo local | Você não paga por uso nem guarda credenciais |
| Dados | Armazenamento local; no servidor, só nome do projeto e contagens | Reduz custo, vazamento e exposição à LGPD |
| Entrada | Arquivo local e seleção no Google Drive | Links e sites com login ficam fora da V1 |
| Plano gratuito | Dossiê completo durante a sessão | A pessoa precisa sentir o valor antes de pagar |
| Plano pago | Guardar, exportar, importar e conectar projetos | Paga para não perder o conhecimento acumulado |
| Linguagem | Python até provar o valor (B00 a B09); TypeScript no produto (a partir de B10) | Testa o método mais rápido, sem abrir mão da execução no navegador |

## Hipóteses a validar

1. O dossiê entrega achados verdadeiros e novos para quem já conhece o assunto.
2. O método em níveis supera um bom prompt em obras longas e múltiplas fontes, com relações novas e verificadas.
3. Modelos gratuitos ou locais entregam qualidade suficiente para o plano gratuito.
4. O usuário aceita conectar um motor de IA para obter o resultado.
5. Parte dos usuários paga para guardar e continuar o projeto.

## Fora da V1

- Coleta em sites com assinatura, armazenamento de senhas e automação de interfaces de chat.
- Docling e OCR de PDF escaneado, que exigem etapa fora da página estática.
- Colaboração em equipe, acervo próprio de notícias e motor pago por você.
- Edição completa em celular; nele, a V1 oferece leitura dos achados e das fichas.

## Camada 1: arquitetura e blocos

A regra central é que o domínio não conhece fornecedor, biblioteca de grafo nem banco. Cada dependência externa fica atrás de um contrato pequeno, então trocar OpenRouter por modelo próprio, ou SQLite local por servidor, não altera o restante.

&#91;embedded content: arquitetura da V1 · contratos entre o pipeline e cada dependência externa\]

O pipeline fala só com os quatro contratos. O texto do usuário sai do navegador apenas para o motor de IA que ele escolheu.

### Python e TypeScript

A pesquisa do método roda em Python, onde spaCy, avaliação e treino são mais simples. A página continua em TypeScript, e o pipeline só é portado depois do C2, se o valor for comprovado.

| Parte | Linguagem | Observação |
| --- | --- | --- |
| Gabarito, avaliação e comparativos | Python | `eval`, com pytest e relatórios |
| Pipeline de pesquisa, N0 a N5 | Python | Linha de comando, com spaCy, regras e APIs |
| Análise e validação de achados | Python | NetworkX; depois, Graphology no navegador |
| Treino de BERTimbau e modelos pequenos | Python | Fora do produto |
| Página, filtros e grafo | TypeScript | React e Cytoscape.js |
| Pipeline no navegador | TypeScript | Porte em B13, com NER em ONNX |
| Motor pago futuro | Python | Docling, spaCy ou GPU; exige servidor e deixa de ter custo perto de zero |

spaCy no navegador via Pyodide [exige wheels WASM próprios](https://github.com/maymay-wa/spacy), o que é pesado demais para a V1. O equivalente previsto é um NER ONNX via Transformers.js, como o [BERTimbau large treinado no HAREM](https://huggingface.co/rchuluc/bertimbau-large-ner-total-onnx), com tamanho e velocidade a medir.

**O que evita fazer tudo duas vezes:** JSON Schema, prompts, receitas de lente, formato `.grafo` e casos de teste ficam em `contracts/`, sem depender de linguagem. As duas implementações passam nos mesmos testes. Na fase Python, os contratos abaixo são `Protocol`, e em TypeScript, `interface`.

### Blocos do sistema

| Bloco | Responsabilidade | Tecnologia da V1 | Como trocar depois |
| --- | --- | --- | --- |
| `core` | Tipos, regras, IDs, schema e eventos | Pydantic na pesquisa; TypeScript e Zod no produto | Permanece |
| `ingest` | Lê arquivos e extrai texto com posição | File API, PDF.js e leitor de EPUB | Novo `DocumentParser`, inclusive Docling em servidor |
| `sources` | Entrega arquivos ao pipeline | Upload local; [Google Picker com `drive.file`](https://developers.google.com/picker/docs/) | Novo `SourceConnector`: links ou extensão |
| `segment` | Cria blocos com posição e sobreposição | Código próprio | Nova estratégia sem mudar o restante |
| `engines` | Executa tarefas de IA | OpenAI compatível, OpenRouter e WebLLM | Novo `LlmEngine`, inclusive API própria |
| `tasks` | Prompts versionados e saídas validadas | Modelos de prompt e Zod | Nova versão por tarefa |
| `pipeline` | Orquestra, retoma e registra custo | Máquina de estados em Worker | Execução em fila no servidor |
| `verify` | Confere provas e sustentação | Comparação de texto e tarefa de verificação | Modelo NLI ou motor mais forte |
| `resolve` | Une nomes e aponta ambiguidades | Regras e tarefa de desempate | Modelo próprio de entidades |
| `analysis` | Calcula pontes, grupos e mudanças no tempo | [Graphology](https://ithelp.ithome.com.tw/articles/10387358) em Worker | Banco de grafo no servidor |
| `store` | Guarda projeto, checkpoint e notas | [SQLite WASM com OPFS em Worker](https://blog.openreplay.com/sqlite-browser-opfs/) | Novo `ProjectStore`: Postgres ou Neo4j |
| `compose` | Monta achados, fichas e ganchos | Código e tarefa de narração | Novos modelos de texto |
| `graph-view` | Desenha o mapa | [Cytoscape.js](https://ithelp.ithome.com.tw/articles/10387358) | Sigma.js, se passar de alguns milhares de nós |
| `ui` | Telas e estado compartilhado | React, Vite e Zustand | Telas substituídas uma a uma |
| `exporter` | Gera `.html` e `.grafo` | Viewer único e SQLite compactado | Novos formatos |
| `account-api` | Conta, licença e assinatura | [Cloudflare Workers e D1](https://freetier.co/cloudflare-free-tier) | Outro serviço com a mesma API |
| `eval` | Compara prompt e ferramenta | Scripts Python e gabaritos JSON | Permanece e cresce |
| deepen | Prioriza pares e pessoas, seleciona trechos e executa N2 a N5 | Código próprio, índice de menções e receitas de lente | Nova lente ou busca semântica, sem mudar o pipeline |

Escolhi Cytoscape.js porque a V1 deve ter centenas de nós, e essa é a faixa em que suas [opções de layout e estilo](https://ithelp.ithome.com.tw/articles/10387358) ajudam mais. A análise fica no Graphology, em separado, para o renderizador poder mudar sem refazer os cálculos.

### Contratos que protegem a troca

```ts
interface LlmEngine {
  id: string;
  capabilities: {
    jsonSchema: boolean;
    maxContextTokens: number;
    runsLocally: boolean;
    dataPolicyNote: string;
  };
  complete(req: LlmRequest, signal: AbortSignal): Promise<LlmResponse>;
}

interface SourceConnector {
  id: string;
  pick(): Promise<SourceRef[]>;
  fetch(ref: SourceRef): Promise<Blob>;
}

interface DocumentParser {
  accepts(file: FileMeta): boolean;
  parse(file: Blob): Promise<ParsedDocument>;
}

interface ProjectStore {
  open(projectId: string): Promise<ProjectTx>;
  checkpoint(run: RunState): Promise<void>;
  exportDatabase(): Promise<Uint8Array>;
  importDatabase(data: Uint8Array): Promise<void>;
  destroy(projectId: string): Promise<void>;
}

interface GraphView {
  render(model: GraphViewModel): void;
  applyState(state: ViewState): void;
  on(event: GraphEvent, handler: GraphHandler): void;
}
```

O contrato AccountApi, de licença e assinatura, entra em B17. Cada resposta de IA é validada na borda. Um motor que devolve JSON inválido gera nova tentativa ou falha registrada, nunca dado corrompido no grafo.

### Modelo de dados

| Tabela | Campos principais | Por que importa |
| --- | --- | --- |
| `source` | título, tipo, data, hash, licença declarada | Permite filtrar e citar a origem |
| `segment` | fonte, capítulo, posição inicial e final, texto temporário | Liga cada prova ao original |
| `entity` | nome preferido, tipo, descrição curta | É o nó do grafo |
| `alias` | entidade, nome, origem, confiança | Une apelidos e permite desfazer |
| `relation_type` | rótulo, definição, versão | Mantém a lista fechada aprovada pelo usuário |
| `claim` | sujeito, tipo, objeto, classe, estado, confiança | É a relação extraída |
| `evidence` | claim, fonte, posição, trecho curto | Sustenta a relação |
| `time_scope` | data da história, data da publicação, capítulo | Separa as duas linhas do tempo |
| `finding` | tipo, cálculo, claims de apoio, texto | Compõe a primeira tela |
| `note` | alvo, conteúdo, tipo | Forma a camada do usuário |
| `run` | etapa, modelo, prompt, tokens, erros | Permite reproduzir e medir |
| `event` | ação, alvo, antes, depois | Desfazer e preservar correções |
| mention | entidade, segmento, posição, nome usado | Permite selecionar os trechos de cada pessoa ou par |
| lens | pergunta, tipos, regra de trechos e de prova, versão | Torna cada aprofundamento repetível |
| pass | nível, lente, alvo, chamadas, novas relações, verificadas, parada | Mede o rendimento e mostra o que mudou |

A `classe` da relação tem quatro valores: `afirmada`, `inferida`, `coocorrencia` e `interpretacao`. O `estado` tem cinco: `proposta`, `verificada`, `rejeitada`, `confirmada_humano` e `rejeitada_humano`. Uma decisão humana nunca é sobrescrita por um novo processamento.

### Fluxo do pipeline

1. **Ingerir:** lê os arquivos, calcula o hash e guarda texto com posições.
2. **Segmentar:** divide em blocos de 5 a 15 parágrafos, respeita capítulos e repete 1 ou 2 parágrafos.
3. **Sugerir relações:** usa o objetivo do usuário e uma amostra do material, e espera a aprovação.
4. **Elenco (N0):** identifica pessoas, apelidos e menções por bloco.
5. **Fatos (N1):** filtra pares candidatos e extrai relações em JSON validado.
6. **Conferir provas:** rejeita o que não localiza no original; este passo é só código.
7. **Verificar às cegas:** uma tarefa separada avalia se o trecho sustenta a relação, sem saber sua origem.
8. **Resolver identidade:** une nomes por regras e pede revisão nos casos ambíguos.
9. **Lacunas (N2):** busca o que faltou, com o que já foi verificado como memória.
10. **Analisar:** calcula grupos, pontes, mudanças no tempo, conflitos e relações raras.
11. **Compor:** gera achados, fichas e ganchos usando só fatos confirmados.
12. **Aprofundar sob demanda (N3 a N5):** a nova relação volta aos passos 6 a 11, e a tela mostra só o que mudou.

Cada etapa grava checkpoint. A chave de cada bloco combina hash do texto, versão do prompt e modelo, então uma nova execução só refaz o necessário. Se a cota acabar, o projeto pausa e retoma depois.

### Formato de exportação

| Arquivo | Conteúdo | Uso |
| --- | --- | --- |
| `projeto.html` | Viewer completo, dados embutidos e notas | Abre offline; permite filtrar, editar notas e salvar nova cópia |
| `projeto.grafo` | SQLite compactado e `manifest.json` | Reimportação no site para continuar o trabalho |
| Manifesto | Versão do schema, app, modelos, contagens, hash e assinatura | Migração e validação da importação |

A exportação guarda trechos curtos, não o texto completo. Para extrair mais depois, o usuário reenvia o documento, e o hash o vincula à fonte já registrada. A assinatura é feita no Worker e comprova a origem do arquivo, mas não impede cópia: é controle de produto, não DRM.

### Passo a passo para montar

1. Crie o repositório com `contracts/`, `research/`, `eval/`, `apps/*` e `packages/*`.
2. Defina schemas, estados e casos de teste em `contracts/`.
3. Monte em Python o `eval` e o adaptador compatível com OpenAI.
4. Implemente ingestão, segmentação, N0 com spaCy, N1 e conferência de prova.
5. Acrescente verificação, N2, resolução, N3, N4, N5, análise e achados.
6. Construa o dossiê sobre um arquivo fixo gerado em *O Alienista*.
7. Se o C2 passar, conclua as telas e porte o pipeline para TypeScript e Workers.
8. Adicione `store` com SQLite no navegador e as conexões.
9. Adicione conta, licença, exportação e pagamento por último.

### Custo da V1

| Item | Custo mensal esperado | Observação |
| --- | --- | --- |
| Site estático | US$ 0 | [Requisições estáticas gratuitas](https://developers.cloudflare.com/workers/platform/pricing/index.md) |
| Worker e banco | US$ 0 | [100 mil requisições/dia](https://temps.sh/blog/cloudflare-pages-free-tier-limits-2026) e [5 GB no D1](https://freetier.co/cloudflare-free-tier) |
| Se exceder | US$ 5 | [Plano pago do Workers](https://temps.sh/blog/cloudflare-pages-free-tier-limits-2026) |
| Motor de IA em produção | US$ 0 para você | Pago pelo usuário ou rodando na máquina dele |
| Domínio e e-mail | A confirmar | Baixo; varia por fornecedor |

O limite gratuito é um [bloqueio, não cobrança extra](https://freetier.co/cloudflare-free-tier), então a API deve falhar de forma clara sem afetar o trabalho local.

## Camada 2: experiência do usuário

O dossiê começa pelos achados, não pelo grafo. As fontes consultadas convergem em mostrar primeiro o que importa, deixar o detalhe sob demanda e manter todas as visões coordenadas, porque um grafo completo costuma virar um emaranhado.

### O que a pesquisa indica

| Padrão | Evidência | Aplicação |
| --- | --- | --- |
| Foco no trabalho, não no modelo de dados | [Emaranhados podem existir nos dados, mas não na interface](https://cambridge-intelligence.com/how-to-fix-hairballs/) | Abrir com achados e um mapa reduzido |
| Visão geral primeiro, detalhe sob demanda | [Agrupamento visual do SemSpect](https://ceur-ws.org/Vol-3526/paper-07.pdf) | Grupos no mapa; ficha ao clicar |
| Filtros e análise de rede | [Usuários buscam as entidades e conexões importantes](https://cambridge-intelligence.com/getting-the-perfect-look-and-feel-for-your-network-visualizations/) | Lentes prontas, não só filtros manuais |
| Linha do tempo integrada | [Barra de tempo com histograma, integrada ao grafo](https://cambridge-intelligence.com/methods-visualizing-dynamic-networks/) | Barra inferior com seleção e reprodução |
| Evitar comparar quadros separados | [Pequenos múltiplos viram jogo de sete erros](https://cambridge-intelligence.com/methods-visualizing-dynamic-networks/) | Mesmo mapa, sem telas paralelas |
| Modo acumulado por capítulo | [Story Ribbons](https://arxiv.org/pdf/2508.06772) | Alternar entre "até aqui" e "só este trecho" |
| Texto sincronizado com a visualização | [Story Ribbons](https://arxiv.org/pdf/2508.06772) | Leitor que acompanha a seleção |
| Foco temporário e aviso de itens ocultos | [Foco](https://docs.kumu.io/guides/focus) e [ajuda do Kumu](https://docs.kumu.io/frequently-asked-questions/my-map-disappeared-how-do-i-bring-it-back) | Faixa de estado e tecla Esc |
| Perfil no painel lateral | [Editor de mapas do Kumu](https://docs.kumu.io/overview/user-interfaces/map-editor) | Ficha sem sair do mapa |
| Várias perspectivas do mesmo dado | [Visões do Kumu](https://docs.kumu.io/guides/views) | Lentes salvas, sem duplicar dados |
| Correção dentro da análise | [Análise visual de redes de personagens](https://www.creta.uni-stuttgart.de/en/blog/2019/01/21/new-article-on-visualizing-character-networks/) | Corrigir no próprio contexto |

### Jornada do usuário

1. **Início:** explica a proposta e abre um dossiê de demonstração sem cadastro.
2. **Novo projeto:** nome, objetivo e material.
3. **Motor:** recomenda uma opção e informa para onde o texto será enviado.
4. **Relações:** mostra uma lista sugerida a partir da amostra, editável.
5. **Processamento:** mostra progresso, primeiros nomes e opção de pausar.
6. **Dossiê:** abre em Achados.
7. **Saída:** copiar um gancho, gerar imagem ou exportar o projeto.

### Disposição da tela principal

- **Barra superior:** nome, busca global, seletor de visão, estado do processamento, Exportar.
- **Coluna esquerda, 280 px, recolhível:** lentes, filtros e contagens.
- **Área central:** a visão ativa.
- **Painel direito, 380 px, redimensionável:** ficha, relação ou prova selecionada, com abas Detalhes, Trechos e Notas.
- **Barra inferior, 112 px:** linha do tempo, sempre visível nas visões Mapa e Relações.

&#91;embedded content: tela principal · wireframe da visão Mapa\]

Selecionar uma pessoa, uma lente ou um período atualiza mapa, ficha e linha do tempo ao mesmo tempo.

### Visões

| Visão | Pergunta respondida | Elementos e interação |
| --- | --- | --- |
| Achados | O que eu não tinha notado? | 5 cards, com tipo, frase, força da evidência e ações Ver no mapa, Abrir prova, Criar gancho |
| Mapa | Como tudo se liga? | Grupos, foco, seleção múltipla, lentes e legenda |
| Linha do tempo | Quando isso mudou? | Faixas por pessoa e eventos, ligadas ao mapa |
| Pessoas | Quem é quem? | Grade de fichas, ordenável por relevância, pontes ou aparições |
| Relações | Quais são os fatos? | Tabela filtrável, em lote, com estado e prova |
| Caminho | Como A chega a B? | Dois seletores, caminhos curtos e narração passo a passo |
| Leitor | Onde está escrito? | Texto ou trecho com destaques sincronizados |
| Ganchos e notas | O que vou publicar? | Editor de tese, provas e contraponto, mais as notas |

### Linha do tempo e movimento na história

- **Eixo:** capítulo em obras; data em documentos com data. Os dois coexistem, mas um fica ativo por vez.
- **Histograma:** mostra o volume de relações, empilhado por tipo.
- **Seleção:** duas alças definem o intervalo; o clique no histograma salta para o ponto.
- **Modos:** "Acumulado" mostra tudo até aquele ponto; "Janela" mostra só o trecho.
- **Reprodução:** avançar, voltar, tocar e velocidade; setas do teclado avançam uma unidade.
- **Estabilidade:** as posições dos nós ficam fixas durante a reprodução, para preservar o mapa mental. Isso é decisão de projeto, a validar nos testes.
- **Marcadores:** achados e notas aparecem como pontos na barra.

### Seleção de personagens e lentes de visualização

- **Clique:** seleciona, abre a ficha e destaca as relações diretas.
- **Duplo clique ou F:** entra em foco, escondendo o restante.
- **Shift + clique:** acrescenta nomes à seleção.
- **Dois selecionados:** oferece Comparar e Ver caminho.
- **Esc:** sai do foco. Uma faixa sempre indica itens ocultos, com Limpar.
- **Busca:** encontra pessoa, apelido, relação ou trecho e sugere o nome correto.

| Lente | O que mostra | Cálculo |
| --- | --- | --- |
| Visão geral | Grupos e pessoas principais | Comunidades e relevância |
| Pontes | Quem liga grupos | Intermediação |
| Conflitos | Relações adversas e contradições | Tipo e fontes divergentes |
| Evolução | O que surgiu ou mudou no período | Comparação entre intervalos |
| Pouco citados, decisivos | Baixa frequência com alta intermediação | Frequência contra posição |
| Por fonte | Quem afirma o quê | Agrupamento por fonte |
| Só minhas notas | O que o usuário marcou | Camada pessoal |

As lentes acima só reorganizam o que já foi extraído e não usam IA. As lentes de extração, descritas a seguir, buscam relações novas.

### Aprofundar: lentes de extração

O botão Aprofundar aparece na ficha de uma pessoa, em um par selecionado e em cada achado. É aqui que o conhecimento visivelmente cresce.

1. **Escolher:** o painel mostra lentes sugeridas para aquela pessoa ou par, com uma frase sobre o que cada uma procura.
2. **Prever:** antes de rodar, mostra trechos lidos, chamadas, custo ou cota estimados e o motor usado.
3. **Acompanhar:** o progresso aparece no painel, sem bloquear o mapa, com opção de parar.
4. **Comparar:** o resultado mostra "+7 relações, 2 contradições, 3 rejeitadas" e destaca a diferença no mapa.
5. **Revisar:** cada novidade abre sua prova, com ações Confirmar, Rejeitar e Anotar.
6. **Encadear:** o sistema sugere o próximo passo, como "analisar a ligação com esta pessoa".

- **Resultado vazio:** "Sem novas evidências nesta lente" é um resultado legítimo e mostra o que foi lido.
- **Origem:** o filtro "Veio de" separa nível e lente, e a relação informa qual passada a encontrou.
- **Interpretação:** aparece com selo próprio e nunca se mistura aos fatos.
- **Histórico:** o painel do projeto lista cada aprofundamento e o que ele acrescentou.

### Filtros, tabelas e rolagem

- **Filtros:** tipo de relação, classe, estado, fonte, período, grupo, pessoa e quantidade de provas.
- **Contagens:** cada opção mostra o total disponível; opções vazias ficam desativadas.
- **Chips:** filtros ativos aparecem no topo, com remoção individual.
- **Paginação:** Relações usa 50 linhas por página e cabeçalho fixo; Pessoas e Trechos usam rolagem virtual.
- **Painel direito:** rola sozinho, sem mover o mapa.
- **URL:** guarda visão, filtros, foco e período, para voltar exatamente ao mesmo estado.
- **Desfazer:** mantém histórico de navegação e de edições.

### Atualização durante o processamento

- **Dados chegam por bloco:** contadores sobem em tempo real, sem esperar o fim.
- **O mapa não salta:** novos itens entram como "12 novos", e o usuário escolhe quando incorporar.
- **Estado por item:** proposta, verificada ou rejeitada aparecem sem recarregar.
- **Pausa e retomada:** cota esgotada vira um aviso com horário sugerido, e o trabalho fica salvo localmente.
- **Placar:** a qualidade fica no fim e num botão fixo, sem competir com os achados.

### Notas e ganchos

- **Onde anotar:** pessoa, relação, trecho, achado ou um período.
- **Como:** selecione o texto no Leitor ou clique em Anotar no painel.
- **Separação visual:** nota do usuário nunca se parece com um fato extraído.
- **Tipos:** interpretação, pergunta, a verificar e pauta.
- **Gancho:** o usuário escolhe achados e o sistema monta tese, provas e contraponto; a tese fica editável.
- **Formatos:** comentário curto, roteiro de vídeo, thread e imagem do mapa recortado.
- **Citação:** copiar sempre leva fonte, posição e link.

### Linguagem visual e acessibilidade

- **Cor:** por categoria de relação, nunca como único sinal.
- **Linha:** contínua para afirmada, tracejada para inferida, pontilhada para coocorrência.
- **Tamanho do nó:** relevância na lente ativa, explicada na legenda.
- **Tipografia e densidade:** visual de publicação, com muito respiro; [desordem é um dos principais problemas](https://cambridge-intelligence.com/getting-the-perfect-look-and-feel-for-your-network-visualizations/).
- **Alternativa ao grafo:** a visão Relações oferece a mesma informação em tabela, com teclado completo.
- **Celular:** Achados, Pessoas e Leitor em coluna única; o mapa só para consulta.

### Estados que precisam de desenho

| Estado | O que mostrar |
| --- | --- |
| Sem WebGPU | Motor por API, sem mencionar erro técnico |
| Modelo baixando | Tamanho, tempo estimado e opção de cancelar |
| Cota encerrada | Horário de retomada e outras opções de motor |
| Sem relações encontradas | Sugestão de ajustar a lista ou o material |
| Nome ambíguo | Fila de revisão com trechos lado a lado |
| Prova não localizada | Relação rejeitada, visível só no placar e no filtro |
| Exportação no plano gratuito | Prévia do que será guardado e preço |
| Lente sem novidade | Trechos lidos, resultado vazio e outras lentes sugeridas |
| Aprofundamento acima do limite | Custo ou cota previstos e opção de reduzir o escopo |

## Método central: extração em níveis

O ganho principal não vem de um prompt melhor, e sim de uma orquestração que decide o que cada passada lê, usa o que já foi achado, verifica cada relação e acumula o resultado. Isso ainda é hipótese para o caso em português, e o teste por níveis abaixo decide o que fica no produto.

&#91;embedded content: níveis de extração · fluxo base e aprofundamento sob demanda\]

N0 a N2 formam a base. N3 e N4 usam o grafo para escolher o que ler, e o resultado volta pelo mesmo verificador.

### Níveis de extração

| Nível | Pergunta | Lê o quê | Quando roda |
| --- | --- | --- | --- |
| N0. Elenco | Quem aparece, com quais nomes e onde? | Todos os blocos | Sempre |
| N1. Fatos | Quais pares têm relação e qual é ela? | Blocos com pares candidatos | Sempre |
| N2. Lacunas | O que ficou de fora? | Mesmos blocos, com a lista já encontrada | Nos blocos com sinal de perda |
| N3. Dossiê do par | Como A e B se relacionam ao longo da fonte? | Trechos de A e B reunidos | Pares prioritários ou pedido do usuário |
| N4. Lentes | O que este ângulo revela sobre esta pessoa? | Trechos dessa pessoa e dos seus pares | Pedido do usuário |
| N5. Síntese | O que mudou e o que se contradiz? | Só relações verificadas | Depois de N3 ou N4 |

Cada relação passa por uma escada de profundidade: existe, tem tipo, tem episódio, mudou no tempo, sugere algo. O último degrau recebe a classe `interpretacao` e precisa de ao menos duas provas.

### Receita de lente

Uma lente de extração não é um filtro. É uma receita versionada que muda a pergunta, os trechos lidos e os tipos aceitos:

```ts
interface ExtractionLens {
  id: string;
  version: string;
  question: string;
  relationTypes: string[];
  scope: "person" | "pair" | "group";
  retrieval: "ego" | "ego_and_top_pairs" | "pair_segments";
  evidenceRule: "literal" | "literal_two_or_more";
  outputClasses: ClaimClass[];
  maxCalls: number;
}
```

| Pacote inicial | Lentes | Observação |
| --- | --- | --- |
| Geral | Família, alianças, conflito, poder, mudança ao longo do tempo | Base para qualquer área |
| Obras | Papel na trama, segredo, quem sabe o quê, narrador e versão dos fatos | Testar primeiro em *O Alienista* |
| Política e notícias | Apoio público, rompimento, nomeação, financiamento citado, quem afirma o quê | Exige fonte e data; nunca afirma crime ou intenção |

A lista é um ponto de partida. A lente sugerida ao usuário vem do objetivo dele e de uma amostra do material, nunca só do nome da obra.

### Como a orquestração funciona

1. **Indexar menções:** N0 grava em quais blocos cada pessoa aparece.
2. **Priorizar:** o código ordena pares e pessoas por frequência, intermediação, mudança no tempo e poucas provas.
3. **Selecionar trechos:** a lente lê só o material relevante, não o livro inteiro.
4. **Dar memória:** a passada recebe as relações já verificadas e deve buscar o que é novo.
5. **Permitir o vazio:** "sem evidência" é sempre uma resposta válida.
6. **Verificar às cegas:** o verificador recebe só relação e trecho, sem saber qual lente a gerou.
7. **Registrar a origem:** cada relação guarda passada, lente e versão do prompt.
8. **Parar:** a passada encerra com menos de 2 relações novas verificadas por 10 chamadas, valor a calibrar.

### O que o código resolve sem LLM

A regra é: **o código propõe e confere; o LLM só interpreta o que o código não resolve.** Minha estimativa é que cerca de metade das etapas dispense LLM, e o filtro reduza bastante as chamadas, mas isso ainda precisa ser medido.

| Etapa | Sem LLM | Quando chamar o LLM |
| --- | --- | --- |
| Ingestão e blocos | Tudo | Nunca |
| N0. Elenco | NER do spaCy, regex, títulos e apelidos | "O alienista", "o ex-ministro", pronomes |
| N1. Pares candidatos | Coocorrência por janela | Decidir se há relação real |
| N1. Relações explícitas | Padrões como "filho de" e "casou com", com Matcher | O restante |
| Conferência de prova | Tudo, com busca exata e RapidFuzz | Nunca |
| União de nomes | Normalização, iniciais e similaridade | Casos ambíguos |
| Datas e capítulos | Regex e estrutura do documento | Tempo implícito da história |
| Pontes, grupos e mudanças | Tudo, com NetworkX ou Graphology | Nunca |
| Achados | Detecção e ranking | Só para redigir |
| Verificação | Primeiro um modelo NLI pequeno, [como no RelEx-PT](https://aclanthology.org/2026.lrec-1.609.pdf) | Casos incertos |
| N3, N4 e relações implícitas | Seleção de trechos | Interpretação |

**Limites a medir:**

- **Recall:** pessoa não detectada em N0 não chega às etapas seguintes.
- **Referências indiretas:** "o alienista" não é um nome próprio, e os modelos em português, pelo que sei, não trazem correferência pronta. Confirmar na documentação do spaCy.
- **Domínio e época:** matérias tendem a ir melhor que textos de Machado; medir os dois.
- **No navegador:** o NER em ONNX [entrega subtokens](https://huggingface.co/rchuluc/bertimbau-large-ner-total-onnx), então o código precisa juntá-los.

### Por que essas escolhas

| Estudo | Resultado relatado | Decisão |
| --- | --- | --- |
| [GraphRAG](https://arxiv.org/pdf/2404.16130) | Blocos de 600 tokens renderam quase o dobro de entidades em relação a 2.400 | Blocos curtos e passada de lacunas |
| [EP-RSR](https://preview.aclanthology.org/moar-dois/2025.findings-naacl.224.pdf) | Par, relações candidatas e fato: +7,42 de F1 no DocRED | N1 começa pelos pares |
| [RelPrior](https://arxiv.org/pdf/2511.08143) | Sem filtrar pares, cerca de −20 de F1; sem etapa complementar, cerca de −5 | Filtrar, mas recuperar em N2 |
| [Pipeline por ontologia](https://ceur-ws.org/Vol-4293/paper59.pdf) | Múltiplas passadas: +51,7% de entidades | Ciclo guiado por lacunas |
| [LEC-KG](https://arxiv.org/pdf/2602.02090) | Refinamento: +11,88 pontos de recall sobre few-shot | Reavaliar confiança média |
| [Verificação por crítico](https://ceur-ws.org/Vol-4258/paper1.pdf) | 58,5% menos falsos positivos | Verificador separado |
| [Relações em romances](https://arxiv.org/abs/2507.04852v1) | Separar dimensões melhorou a extração | Lentes por ângulo |

Os domínios, modelos e métricas variam, e parte vem de resumos. Modelos grandes também [tendem a prever relações em excesso](https://preview.aclanthology.org/moar-dois/people/h/huangming-xu), então mais passadas sem verificação podem piorar o grafo.

### Riscos do método e travas

| Risco | Trava | Como medir |
| --- | --- | --- |
| A lente cria o que procura | Verificador cego e resposta vazia válida | Falso positivo por lente |
| O modelo responde de memória | Prova literal e cópia da obra com nomes trocados | Queda de acerto na cópia |
| Passadas repetem o mesmo resultado | Memória e parada por rendimento | Novas relações verificadas por chamada |
| Custo ou cota explodem | Limite por lente e preço antes de executar | Chamadas e tokens por nível |
| Verificador rejeita relações certas | Amostra revisada à mão | Recall antes e depois |

### Custo e cota

Um livro de 60 blocos usa cerca de 180 chamadas em N0, N1 e verificação. No Haiku 5.5, supondo 3,5 mil tokens de entrada e 1 mil de saída por chamada, isso custa cerca de US$ 0,15. Uma lente com 50 chamadas custa cerca de US$ 0,04.

A cota grátis do OpenRouter, de [50 requisições por dia](https://benchlm.ai/md/free-tier.md), levaria cerca de 4 dias para o mesmo livro. Por isso, o gratuito precisa de um modo econômico, com material menor ou menos etapas, e a qualidade desse modo também deve ser medida.

### Teste por níveis

| Execução | Pergunta |
| --- | --- |
| N1 | Qual é a linha de base? |
| N1 + N2 | Quanto recall as lacunas recuperam? |
| + N3 | Melhoram relações implícitas e mudanças no tempo? |
| + N4 | Surgem achados novos, verdadeiros e utilizáveis? |
| + verificador | Quanto ruído sai e quantas relações certas se perdem? |

Um nível permanece se somar ao menos 5 pontos de recall sem perder mais de 2 de precisão, ou se elevar a taxa de achados novos no teste com pessoas. Esses cortes são sugestão minha, a fixar antes de rodar.

### Híbrido contra LLM

| Execução | O que mostra |
| --- | --- |
| LLM em tudo | Referência de qualidade e de custo máximo |
| spaCy, regras e LLM | Versão candidata ao produto |
| Só spaCy e regras | Piso sem custo de IA |

Compare recall, precisão, chamadas e custo. O híbrido vence se cortar muitas chamadas sem perder mais que 2 pontos de recall, um limite que sugiro fixar antes de rodar.

## Camada 3: modelos

Cada nível da extração pode usar um motor próprio. Comece pela API gratuita da Mistral para desenvolver, use o Haiku 5.5 como referência e ofereça OpenRouter ao usuário; modelo no navegador entra como opção depois de medido. Ainda não há evidência de qual modelo vence no seu caso, então a escolha final sai do teste abaixo, e cada tarefa pode usar um motor diferente.

### Candidatos

| Papel | Modelo ou serviço | Acesso | Cuidado |
| --- | --- | --- | --- |
| Desenvolvimento | [Mistral, plano gratuito](https://openrouter.ai/blog/tutorials/free-llm-apis-compared/) | Chave de API; [JSON Schema nativo](https://www.developersdigest.tech/blog/structured-outputs-across-ai-apis-2026) | Exige aceitar uso para treino; use só domínio público |
| Desenvolvimento, velocidade | [Groq, Llama 3.3 70B](https://openrouter.ai/blog/tutorials/free-llm-apis-compared/) | Chave de API | Limites por minuto e por dia |
| Referência de qualidade e custo | [Claude Haiku 5.5](https://apidog.com/blog/claude-haiku-5-5-pricing/) | API paga, cerca de US$ 0,05 por livro | Não é aberto |
| Usuário sem custo inicial | [OpenRouter, modelos `:free`](https://benchlm.ai/md/free-tier.md), via [PKCE](https://openrouter.ai/docs/guides/overview/auth/oauth) | Login do próprio usuário | 50 requisições/dia até comprar US$ 10; modelos variam |
| Usuário com chave própria | Mistral, OpenAI, Claude e outros compatíveis | Chave guardada só no navegador | Conferir CORS de cada um |
| Local no navegador | [Qwen3.5 e Llama 3.2 no WebLLM](https://pinggy.io/blog/run_llm_in_browser_webgpu/) | WebGPU | Sem dado em português; [1 a 3 bilhões é a faixa confiável](https://tianpan.co/blog/2026-04-17-browser-native-llm-inference-webgpu) |
| Local em português | [Tucano2-qwen-3.7B-Instruct](https://featherless.ai/models/Polygl0t/Tucano2-qwen-3.7B-Instruct) | Teste offline primeiro | Sem build confirmado para WebLLM |
| Referência aberta em português | [Gemma 3 27B](https://aclanthology.org/2026.lrec-1.609.pdf) | API ou máquina maior | Melhor aberto em triplas no RelEx-PT, em frases da Wikipédia |

No RelEx-PT, a extração sem ajuste foi [bem mais fraca em modelos pequenos](https://aclanthology.org/2026.lrec-1.609.pdf), embora os testados fossem de gerações antigas. Por isso, não prometa qualidade do modelo local antes do teste.

### Cada tarefa tem seu contrato

| Tarefa | Entrada | Saída validada | Exigência |
| --- | --- | --- | --- |
| `suggest_relations` | Objetivo e amostra | Tipos, definição e exemplo | Média |
| `extract_entities` | Bloco e lista conhecida | Pessoas, apelidos e referências | Baixa a média |
| `extract_relations` | Bloco, pessoas e tipos aprovados | Relação, classe, trecho, confiança | Alta |
| `verify_claim` | Relação e trecho | Sustenta, não sustenta, incerto | Média |
| `resolve_alias` | Dois nomes e seus trechos | Mesmo, diferente, incerto | Média |
| `narrate_finding` | Cálculo e relações confirmadas | Frase com IDs citados | Média |
| filter\_pairs | Bloco, pessoas e tipos aprovados | Pares com possível relação | Média |
| find\_gaps | Bloco e relações já verificadas | Novas relações ou vazio | Alta |
| analyze\_pair | Trechos de A e B, em ordem | Episódios, mudanças e provas | Alta |
| apply\_lens | Receita, trechos e memória | Relações, classe e provas, ou vazio | Alta |
| synthesize | Relações verificadas de um alvo | Mudanças, contradições e IDs citados | Alta |

As tarefas recebem só o que o código não resolveu. Pares candidatos, posições e nomes já normalizados chegam prontos, o que reduz chamadas e erros de formato.

### Saída de `extract_relations`

```json
{
  "relations": [
    {
      "subject": "Simão Bacamarte",
      "type": "conflito",
      "object": "Porfírio",
      "class": "afirmada",
      "evidence": "trecho copiado literalmente do bloco",
      "confidence": 0.82
    }
  ]
}
```

O exemplo mostra só o formato. O código localiza `evidence` no bloco, e a falha rejeita a relação. A `confidence` do modelo serve para ordenar a revisão, não como prova de acerto.

### Acoplamento

```json
{
  "routes": {
    "extract_relations": { "engine": "openrouter", "model": "definido-no-teste", "promptVersion": "rel-001" },
    "verify_claim": { "engine": "openrouter", "model": "definido-no-teste", "promptVersion": "ver-001" },
    "narrate_finding": { "engine": "openrouter", "model": "definido-no-teste", "promptVersion": "nar-001" }
  }
}
```

- **Adaptador:** só ele conhece URL, autenticação, formato e limite de cada serviço.
- **Capacidades:** com JSON Schema nativo, o adaptador usa-o; sem ele, tenta JSON simples e valida.
- **Limite:** o adaptador informa quanto texto cabe, e o pipeline ajusta o bloco.
- **Falha:** erro temporário gera nova tentativa com espera; cota esgotada pausa; resposta inválida fica registrada.
- **Reprodução:** cada resultado guarda modelo, prompt e parâmetros.
- **Evolução:** adicionar um motor exige um adaptador e passar no mesmo teste, sem alterar o pipeline.

### Teste de escolha

**Material:** *O Alienista* e 100 matérias com gabarito próprio. Dados de terceiros só entram em motores sem uso para treino.

**Medidas por tarefa:** precisão, recall, JSON válido, provas válidas, tokens, tempo e falhas.

**Regra de escolha:** escolher o motor mais barato que fique a até 5 pontos de F1 do melhor em cada grupo: relações explícitas e implícitas. Essa margem é uma sugestão minha, a revisar depois do primeiro resultado.

**Plano gratuito no navegador:** só aparece como recomendado se terminar um livro curto em tempo aceitável num notebook comum e tiver qualidade próxima da opção via API. Caso contrário, fica marcado como experimental.

## Camada 4: requisitos e blocos de projeto

A ordem prova o valor antes de construir o produto inteiro: primeiro a extração em linha de comando, depois o dossiê com dados fixos e, por último, conta e pagamento. Cada bloco termina em algo que pode ser testado sem depender dos seguintes.

### Documentação no repositório

| Arquivo | Conteúdo |
| --- | --- |
| `README.md` | Como rodar, testar e publicar |
| `CLAUDE.md` | Contexto e regras para o Code |
| `docs/00-produto.md` | Promessa, público, escopo e hipóteses |
| `docs/01-arquitetura.md` | Blocos, dependências e decisões |
| `docs/02-dados.md` | Schema, estados, migrações e exportação |
| `docs/03-pipeline.md` | Etapas, checkpoint, retomada e falhas |
| `docs/04-modelos.md` | Adaptadores, tarefas, rotas e resultados |
| `docs/05-ux.md` | Telas, estados, atalhos e sistema visual |
| `docs/06-seguranca-privacidade.md` | Fluxo de dados, chaves, CSP, LGPD e termos |
| `docs/07-avaliacao.md` | Gabarito, métricas e execução do comparativo |
| `docs/adr/` | Uma decisão de arquitetura por arquivo |

### Requisitos funcionais

| ID | Requisito | Prioridade |
| --- | --- | --- |
| RF01 | Abrir dossiê de demonstração sem cadastro | Essencial |
| RF02 | Criar projeto com nome, objetivo e material | Essencial |
| RF03 | Aceitar TXT, EPUB e PDF com texto | Essencial |
| RF04 | Selecionar arquivos no Google Drive | Importante |
| RF05 | Conectar motor por PKCE ou chave própria | Essencial |
| RF06 | Informar destino e política de dados antes de enviar | Essencial |
| RF07 | Sugerir relações a partir do objetivo e da amostra | Essencial |
| RF08 | Editar e aprovar a lista de relações | Essencial |
| RF09 | Processar com progresso, pausa e retomada | Essencial |
| RF10 | Rejeitar relação sem prova no original | Essencial |
| RF11 | Verificar sustentação e classificar a relação | Essencial |
| RF12 | Unir apelidos e mostrar casos ambíguos | Essencial |
| RF13 | Gerar até 5 achados, todos com prova | Essencial |
| RF14 | Oferecer Mapa, Pessoas, Relações, Linha do tempo, Caminho e Leitor | Essencial |
| RF15 | Sincronizar filtros, foco e período entre as visões | Essencial |
| RF16 | Criar notas ligadas a qualquer item | Essencial |
| RF17 | Criar ganchos com tese, provas e contraponto | Importante |
| RF18 | Copiar citação com fonte e posição | Essencial |
| RF19 | Corrigir relações e nomes, preservando a decisão | Essencial |
| RF20 | Exibir placar de qualidade do projeto | Essencial |
| RF21 | Criar conta e guardar só metadados | Essencial |
| RF22 | Exportar `.html` e `.grafo` no plano pago | Essencial |
| RF23 | Importar `.grafo` e continuar o projeto | Essencial |
| RF24 | Rodar modelo no navegador como opção | Importante |
| RF25 | Conectar dois projetos pela mesma entidade | Depois da V1 |
| RF26 | Aprofundar uma pessoa ou um par por lente de extração | Essencial |
| RF27 | Prever chamadas, custo ou cota antes de aprofundar | Essencial |
| RF28 | Mostrar a diferença entre o grafo anterior e o novo | Essencial |
| RF29 | Criar e salvar lentes personalizadas | Depois da V1 |

### Requisitos não funcionais

| ID | Requisito | Meta inicial |
| --- | --- | --- |
| RNF01 | Custo fixo com zero clientes | Próximo de US$ 0, mais domínio |
| RNF02 | Conteúdo do usuário | Nunca enviado ao servidor do produto |
| RNF03 | Credenciais | Nenhuma senha de terceiros; chave só no navegador |
| RNF04 | Interface durante processamento | Trabalho pesado sempre em Worker |
| RNF05 | Interação no mapa | Fluida com 500 nós e 2.000 arestas, a medir |
| RNF06 | Reprodutibilidade | Modelo, prompt e parâmetros salvos por resultado |
| RNF07 | Segurança do HTML | CSP e escape de todo texto vindo de documentos |
| RNF08 | Injeção de prompt | Documento tratado como dado; saída sempre validada |
| RNF09 | Armazenamento | Sem [fallback silencioso para memória](https://blog.openreplay.com/sqlite-browser-opfs/) |
| RNF10 | Navegadores | Chromium, Firefox e Safari atuais; WebGPU tratado como opcional |
| RNF11 | Acessibilidade | Teclado, contraste e alternativa em tabela |
| RNF12 | Telemetria | Só eventos e contagens, nunca conteúdo |
| RNF13 | Verificação | Sem acesso à lente ou ao nível que gerou a relação |
| RNF14 | Aprofundamento | Limite de chamadas por lente e parada por rendimento |

### Blocos em ordem de execução

| Bloco | Entrega | Depende de | Pronto quando |
| --- | --- | --- | --- |
| B00 | Repositório Python, CI, testes e contratos | Nada | CI verde com um teste real |
| B01 | `core`: Pydantic, JSON Schema e regras de estado | B00 | Estados e IDs cobertos por testes |
| B02 | Gabarito de *O Alienista* e `eval` | B01 | Comando calcula precisão, recall e provas válidas |
| B02b | Painel de testes: P0 e P1; P2 a P4 acompanham B05 a B08 | B02 | Execução fictícia aberta no painel, sem acesso a escrever o gabarito |
| B03 | Adaptador OpenAI compatível e tarefas | B01 | Mistral e Haiku respondem no mesmo contrato |
| B04 | Leitura de TXT e EPUB; segmentação | B01 | Posição de cada bloco volta ao texto exato |
| B05 | Pipeline Python com spaCy e regras: N0, N1 e prova | B03, B04 | Capítulo processado, retomado e sem prova inválida |
| B06 | Comparativo A/B/C e híbrido contra LLM | B02, B05 | Relatório fecha o checkpoint C1 |
| B07 | Verificador cego, N2 e resolução de nomes | B05 | Ganho de N2, precisão e união de nomes medidos |
| B08 | N3, N4, N5, cinco lentes, análise e achados | B07 | Teste por níveis fecha o C1b; 5 achados com provas |
| B09 | Dossiê com dados fixos e teste de percepção | B08 | Resultado fecha o checkpoint C2 |
| B10 | Achados, Pessoas e Leitor | B09 | Item abre sua prova em até 2 cliques |
| B11 | Mapa, lentes e linha do tempo | B10 | Filtros e período sincronizados |
| B12 | Relações, Caminho, Notas, Ganchos e Aprofundar | B11 | Notas persistem; aprofundar mostra custo e diferença |
| B13 | Porte para TypeScript, NER ONNX, Workers e SQLite OPFS | B05, B12 | Mesmos testes do Python; livro retomado após fechar a aba |
| B14 | Conexões: PKCE, chave, arquivo e Drive | B13 | Fluxo completo sem guardar segredo no servidor |
| B15 | WebLLM experimental | B13 | Tempo e qualidade medidos em notebook comum |
| B16 | Exportação e importação | B13 | Projeto exportado volta igual, e o HTML abre offline |
| B17 | Conta, licença e assinatura | B16 | Exportação paga é assinada e validada |
| B18 | Início, termos, telemetria e segurança | B14, B16 | Revisão de CSP, XSS e privacidade concluída |
| B19 | Beta fechado e lançamento | B17, B18 | Checkpoint C4 atendido |

### Decisões a registrar logo no início

- [ ] Nome do produto e domínio
- [ ] Gateway de pagamento e emissão de nota, com taxas confirmadas
- [ ] Lista inicial de relações para política e para obras literárias
- [ ] Revisão jurídica de LGPD, direitos autorais e termos

## Camada 5: checkpoints, execução e prazo

A V1 deve levar de 240 a 375 horas de trabalho, ou 10 a 15 semanas a 25 horas semanais. A primeira resposta sobre valor chega bem antes: o teste de percepção sai em 90 a 140 horas, sem conta nem pagamento. A estimativa é minha, com ajuda do Code, e deve ser revista no C1.

&#91;embedded content: roteiro da V1 · fases e checkpoints, sem escala de tempo\]

C4 ocorre 8 semanas depois do início do beta, além das horas acima.

### Prazo por fase

| Fase | Blocos | Horas | 10 h/sem | 15 h/sem | 25 h/sem |
| --- | --- | --- | --- | --- | --- |
| A. Motor em Python e painel | B00–B06 | 45–70 | 5–7 sem | 3–5 sem | 2–3 sem |
| B. Método, valor e percepção | B07–B09 | 45–70 | 5–7 sem | 3–5 sem | 2–3 sem |
| C. Dossiê completo | B10–B12 | 60–90 | 6–9 sem | 4–6 sem | 3–4 sem |
| D. Porte, navegador e conexões | B13–B15 | 45–75 | 5–8 sem | 3–5 sem | 2–3 sem |
| E. Conta, exportação e segurança | B16–B18 | 30–45 | 3–5 sem | 2–3 sem | 1–2 sem |
| F. Beta e ajustes | B19 | 15–25 | 2–3 sem | 1–2 sem | 1 sem |
| **Total** |  | **240–375** | **24–38 sem** | **16–25 sem** | **10–15 sem** |

### Checkpoints

| Marco | Pergunta | Critério para seguir | Se falhar |
| --- | --- | --- | --- |
| C0, fim de B03 | O motor de teste funciona? | Mesmo contrato em 2 serviços; JSON válido acima de 95% | Trocar serviço ou prompt |
| C1, fim de B06 | A base compete com o prompt? | N1 com precisão e recall ao menos iguais aos do melhor prompt; 100% de provas localizadas | Refazer N0 e N1 antes de seguir |
| C1b, fim de B08 | O aprofundamento vale? | Recall 15 pontos acima do melhor prompt, sem perder precisão; cada nível passa na regra do teste; híbrido medido contra LLM; falso positivo por lente medido | Remover níveis ou lentes sem ganho |
| C2, fim de B09 | O dossiê cria valor percebido? | 2 ou 3 de 5 achados verdadeiros, novos e utilizáveis para a maioria de 5 pessoas | Trocar lentes, cálculos ou formato |
| C3, fim de B15 | O plano gratuito é viável? | Pessoa conclui um projeto sozinha; motor recomendado atende a regra da Camada 3 | Motor por API vira o padrão |
| C4, 8 semanas após o beta | Vale continuar investindo? | 20 usuários ativos por semana, 5 conteúdos publicados e 10 exportações pagas ou 1 piloto institucional | Tratar como portfólio ou mudar o público |

Os cortes são propostas minhas, não padrões de mercado. Fixe-os antes de ver os resultados, para não adaptar a meta depois.

### O que medir

| Grupo | Métrica | Quando | Fonte |
| --- | --- | --- | --- |
| Extração | Precisão e recall, por relação explícita e implícita | A cada mudança de prompt ou motor | `eval` |
| Extração | % de provas localizadas e de JSON válido | Toda execução | `run` |
| Identidade | F1 da união de nomes | C1 em diante | `eval` |
| Valor | Achados verdadeiros, novos e utilizáveis | C2 e beta | Teste com pessoas |
| Valor | Conteúdos publicados com a ferramenta | Beta | Entrevista e relato |
| Produto | Visita → motor → projeto concluído → retorno | Beta | Eventos anônimos |
| Produto | Tempo até o primeiro achado | Beta | Eventos anônimos |
| Monetização | Clique em exportar, compra e segunda compra | Beta | API de licença |
| Motor | Tokens, tempo por bloco, erros e pausas por cota | Toda execução | `run` |
| Navegador | Pico de memória, travamentos e queda para API | C3 e beta | Telemetria sem conteúdo |
| Custo | Gasto mensal e uso dos limites gratuitos | Semanal | Painel do provedor |
| Método | Ganho de recall, precisão e achados novos por nível | C1b e a cada novo prompt | eval |
| Método | Falso positivo em pares de controle, por lente | C1b e a cada nova lente | eval |
| Método | Novas relações verificadas por chamada | Toda passada | pass |
| Produto | Uso de Aprofundar e novidades confirmadas | Beta | Eventos anônimos |
| Método | Recall de pessoas no NER e chamadas evitadas pelo filtro | C1 e C1b | eval |

### Plano de ação das primeiras semanas

1. **Antes de codificar:** defina as 8 a 12 relações de *O Alienista* e anote o gabarito de 30 a 50 relações, sem olhar a saída de nenhum modelo.
2. **Semana 1:** B00 a B03, com chaves de teste.
3. **Semana 2:** B04 e B05, processando 2 capítulos com revisão manual.
4. **Semana 3:** B06, rodando os cenários A, B e C e publicando o relatório interno.
5. **Decisão:** abra o C1 antes de escrever qualquer tela, e ajuste o plano com o tempo real gasto.

## Camada 6: descritivo para o Code

Você numerou duas camadas como 5; tratei esta como a sexta. Copie o bloco abaixo para o `CLAUDE.md` do repositório e peça ao Code para executar só de B00 a B03, parando para revisão ao fim de cada bloco.

```markdown
# Mapa de Relações

## Contexto
Aplicação web que transforma documentos em um dossiê navegável de pessoas,
relações, provas, linha do tempo e notas. O produto final roda quase todo no
navegador para manter custo fixo perto de zero. O motor de IA é do usuário ou local.
Demonstração: O Alienista, de Machado de Assis (domínio público).
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
Criar eval/gold/alienista.json com capítulos, relações e apelidos.
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

## Definição de pronto
Tipos e testes passando, sem segredo no repositório,
documentação atualizada e decisão relevante registrada em docs/adr.
Ao terminar um bloco, relate o que mudou, como testar e o que ficou pendente.
Não avance para o próximo bloco sem revisão.

## Fora do escopo agora
N2 a N5, lentes, spaCy no pipeline (B05), interface, TypeScript, conta, pagamento,
Google Drive, WebLLM, extensão e scraping.
```

### Como conduzir o Code

1. Crie o repositório e adicione este texto como `CLAUDE.md`.
2. Peça: "Leia o `CLAUDE.md`, proponha o plano de B00 e execute só esse bloco".
3. Revise o resultado, rode os testes e faça o commit antes do bloco seguinte.
4. Anote o gabarito à mão antes de pedir a primeira execução real.
5. Use somente *O Alienista* com a Mistral gratuita, porque esse plano exige aceitar uso para treino.

## Painel de testes

O painel é uma página local, somente para desenvolvimento, que mostra o que cada execução fez, onde errou, quanto custou e se passou nos checkpoints. Ele segue o padrão do painel do WhatBot, mas lê arquivos de execução e não depende de banco nem altera o gabarito.

### Decisões

| Tema | Decisão | Motivo |
| --- | --- | --- |
| Stack | FastAPI, Jinja2, HTMX, Tailwind e daisyUI | Mesmo padrão do WhatBot, sem etapa de build |
| Acesso | Apenas `127.0.0.1` | O painel pode exibir texto protegido e respostas brutas |
| Dados | Arquivos em `eval/runs/` | Cada execução fica reproduzível, e o painel é substituível |
| Atualização | Polling HTMX de 2 s durante a execução | Simples e suficiente para acompanhar o processamento |
| Gabarito | Somente leitura | O painel não pode ajustar a resposta para o teste passar |
| Terceiros | CSS e JS salvos no repositório | Funciona sem internet e não envia dados a uma CDN |

### Contrato dos arquivos

| Arquivo em `eval/runs/<run_id>/` | Conteúdo | Vai ao Git? |
| --- | --- | --- |
| `manifest.json` | Data, commit, corpus e hash, variante, cenário, níveis, motor, modelo, prompts, parâmetros e versão do gabarito | Sim |
| `metrics.json` | Precisão, recall e F1 por tipo, classe, nível e lente; provas válidas, JSON válido, recall de pessoas, chamadas, tokens, custo e tempo | Sim |
| `traces.jsonl` | Etapa, bloco, tarefa, determinístico ou LLM, tokens, tempo, custo, tentativas e estado | Sim, sem texto |
| `claims.jsonl` | Relação, classe, estado, motivo de rejeição, posições da prova, passada e lente | Não |
| `mentions.jsonl` | Pessoas, apelidos e posições | Não |
| `raw/` | Prompts e respostas brutas | Não |
| `eval/reports/junit.xml` | Resultado do pytest | Não |
| `eval/reviews/<run_id>.jsonl` | Revisão humana dos erros | Sim, sem trechos longos |

O `.gitignore` cobre `data/raw/`, `raw/`, `claims.jsonl` e `mentions.jsonl`, porque podem conter trechos de obra protegida.

### Telas

| Tela | Pergunta | Conteúdo |
| --- | --- | --- |
| Visão geral | Estamos passando? | Último pytest, última execução, C0 a C2 e tendência de recall, precisão e custo |
| Execuções | O que já rodou? | Tabela filtrável por corpus, variante, cenário, modelo e nível, com seleção para comparar |
| Comparar | O que melhorou? | Diferença das métricas e relações só em A, só em B e em ambas |
| Erros | Onde errou? | Acertos, falsos positivos e falsos negativos, filtráveis por tipo, classe, nível e lente |
| Relação | Por que esse resultado? | Trecho destacado, resposta do modelo, verificador, motivo e passada |
| Trace | O que aconteceu em cada bloco? | Linha do tempo de etapas, com prompt, resposta, tempo, tokens e custo |
| Elenco | O NER funcionou? | Recall de pessoas, nomes perdidos, apelidos unidos e casos ambíguos |
| Pytest | O código está são? | Passou, falhou e ignorou, com duração e mensagem de erro |

### Testes que o painel precisa destacar

- **Memória contra texto:** resultado do original comparado com a cópia de nomes trocados.
- **Prompt contra método:** cenários A, B e C lado a lado.
- **Híbrido contra LLM:** recall perdido e chamadas evitadas.
- **Ganho por nível:** o que N2, N3, N4 e o verificador acrescentaram.
- **Falso positivo por lente:** resultado dos pares de controle.

### Revisão de erros

Cada erro recebe uma marcação: `erro_do_modelo`, `gabarito_incompleto`, `ambiguo` ou `erro_de_nome`. Ela é salva em `eval/reviews/` e nunca altera o gabarito. O painel mostra as métricas oficiais e, ao lado, quantos erros foram contestados. Mudar o gabarito continua sendo um ato manual, com commit próprio.

Isso importa porque [um gabarito incompleto pode subestimar a qualidade](https://aclanthology.org/people/jaan-ubi/unverified/), mas também não pode virar uma forma de melhorar a nota. No WhatBot, respostas esperadas já foram ajustadas indevidamente para o teste passar, e esta regra evita repetir o problema.

### Ordem de construção

| Etapa | Entrega | Pronto quando |
| --- | --- | --- |
| P0 | Contrato, escrita dos arquivos e execução fictícia de exemplo | Testes validam todos os formatos |
| P1 | Visão geral, Execuções e Pytest | Painel abre a execução de exemplo |
| P2 | Trace ao vivo e Relação | Dá para seguir um bloco até a relação final |
| P3 | Erros, Elenco e revisão | Cada erro abre sua evidência e aceita marcação |
| P4 | Comparar e checkpoints | Duas execuções mostram a diferença e o C1 calculado |

### Descritivo para o Code

```markdown
Implemente o painel de testes como bloco B02b, em research/mapa_relacoes/painel.
Leia a seção "Painel de testes" do projeto e siga o contrato de arquivos.

Regras:
1. Stack: FastAPI, Jinja2, HTMX, Tailwind e daisyUI, com assets locais e sem build.
2. Servir apenas em 127.0.0.1. Comando: python -m mapa_relacoes.painel.
3. Ler somente eval/runs, eval/reports, eval/reviews e o texto em data/raw.
4. O painel nunca escreve em eval/gold nem em contracts.
5. A única escrita permitida é a revisão em eval/reviews/<run_id>.jsonl.
6. Escapar todo texto vindo de documentos ou modelos.
7. Não colocar texto de obra, prompt preenchido ou resposta bruta em arquivo versionado.
8. Execução sem arquivos deve mostrar estado vazio claro, não erro.

Comece só por P0 e P1. Crie uma execução de exemplo totalmente fictícia em
eval/examples, escreva testes dos formatos e das rotas, e pare para revisão.
Relate o que mudou, como abrir o painel e o que ficou pendente.
```

## Riscos e questões em aberto

O maior risco é de produto: achados corretos, mas óbvios, que não justifiquem usar a ferramenta. Os riscos técnicos têm saída prevista, porque cada um está atrás de um contrato substituível.

| Risco | Sinal de alerta | Resposta |
| --- | --- | --- |
| Achados óbvios | Menos de 2 achados novos no C2 | Mudar cálculos e tipos de achado antes de seguir |
| Prompt empata com o método | C1 sem ganho de recall | Focar em múltiplas fontes e trabalho contínuo |
| Modelo local fraco ou lento | C3 reprovado | Deixar experimental e priorizar motor por API |
| Motor gratuito muda ou sai do ar | Falhas ou cota instável | Trocar a rota e oferecer alternativas |
| Configuração afasta usuários | Queda entre visita e motor | Demonstração melhor e, se houver sinal de compra, motor pago |
| Relação falsa sobre pessoa real | Reclamação ou erro no teste | Classes visíveis, prova sempre visível e canal de correção |
| Uso abusivo sobre pessoa privada | Relato ou padrão externo | Termos e orientação; a moderação é limitada no modo local |
| Direitos autorais | Questionamento de um titular | Sem acervo próprio, trechos curtos e nada público com conteúdo pago |
| Lente fabrica relações | Falso positivo alto nos pares de controle | Reescrever ou remover a lente; manter verificador cego |
| NER perde pessoas ou apelidos | Recall baixo no elenco | Passada de elenco com LLM em amostra e filtro menos rígido |
| Porte diverge do Python | Testes falham em uma das linguagens | Contratos e casos de teste compartilhados; TypeScript só após o C2 |

### Questões em aberto

- [ ] A Mistral e outros serviços aceitam chamadas diretas do navegador? Testar em B14.
- [ ] O escopo `drive.file` permite ler o conteúdo de uma pasta escolhida no Picker? O [seletor aceita pastas](https://developers.google.com/workspace/drive/picker/guides/desktop-mobile-picker), mas a leitura precisa de teste.
- [ ] A verificação de sessão e a assinatura cabem nos [10 ms de CPU](https://developers.cloudflare.com/workers/platform/pricing/index.md) do Workers gratuito?
- [ ] Tucano 2 pode ser convertido para o navegador sem perda relevante?
- [ ] Qual preço por exportação funciona na prática? R$ 9,90 é só o ponto de partida.

Este documento não é parecer jurídico. LGPD, direitos autorais, termos dos provedores e responsabilidade por conteúdo gerado precisam de revisão antes do lançamento.

## Fontes

Consultadas em 3 de novembro de 2026. Limites e preços mudam com frequência; confirme na página do provedor antes de usar. Alguns dados vêm de trechos de busca e guias de terceiros, então confira a fonte original antes de decisões definitivas.

**Interface:** [Cambridge Intelligence: emaranhados](https://cambridge-intelligence.com/how-to-fix-hairballs/) · [Cambridge Intelligence: UX](https://cambridge-intelligence.com/getting-the-perfect-look-and-feel-for-your-network-visualizations/) · [Redes dinâmicas](https://cambridge-intelligence.com/methods-visualizing-dynamic-networks/) · [SemSpect](https://ceur-ws.org/Vol-3526/paper-07.pdf) · [Story Ribbons](https://arxiv.org/pdf/2508.06772) · [Kumu: foco](https://docs.kumu.io/guides/focus) · [Kumu: visões](https://docs.kumu.io/guides/views) · [Kumu: editor](https://docs.kumu.io/overview/user-interfaces/map-editor) · [Redes de personagens](https://www.creta.uni-stuttgart.de/en/blog/2019/01/21/new-article-on-visualizing-character-networks/)

**Tecnologia:** [Cytoscape.js e Sigma.js](https://ithelp.ithome.com.tw/articles/10387358) · [SQLite com OPFS](https://blog.openreplay.com/sqlite-browser-opfs/) · [Google Picker](https://developers.google.com/picker/docs/) · [Cloudflare Workers](https://developers.cloudflare.com/workers/platform/pricing/index.md) · [Limites da Cloudflare](https://freetier.co/cloudflare-free-tier) · [IA no navegador](https://pinggy.io/blog/run_llm_in_browser_webgpu/) · [Limites do WebGPU](https://tianpan.co/blog/2026-04-17-browser-native-llm-inference-webgpu)

**Modelos:** [RelEx-PT](https://aclanthology.org/2026.lrec-1.609.pdf) · [Tucano 2](https://arxiv.org/html/2603.03543v1) · [OpenRouter PKCE](https://openrouter.ai/docs/guides/overview/auth/oauth) · [Comparação de APIs gratuitas](https://openrouter.ai/blog/tutorials/free-llm-apis-compared/) · [Limites gratuitos](https://benchlm.ai/md/free-tier.md) · [Saídas estruturadas](https://www.developersdigest.tech/blog/structured-outputs-across-ai-apis-2026) · [Preço do Haiku 5.5](https://apidog.com/blog/claude-haiku-5-5-pricing/)

**Método:** [GraphRAG](https://arxiv.org/pdf/2404.16130) · [EP-RSR](https://preview.aclanthology.org/moar-dois/2025.findings-naacl.224.pdf) · [RelPrior](https://arxiv.org/pdf/2511.08143) · [Pipeline por ontologia](https://ceur-ws.org/Vol-4293/paper59.pdf) · [LEC-KG](https://arxiv.org/pdf/2602.02090) · [Verificação por crítico](https://ceur-ws.org/Vol-4258/paper1.pdf) · [Relações em romances](https://arxiv.org/abs/2507.04852v1) · [KGGen](https://arxiv.org/html/2502.09956v2)

**Ferramentas determinísticas:** [spaCy no navegador](https://github.com/maymay-wa/spacy) · [BERTimbau NER em ONNX](https://huggingface.co/rchuluc/bertimbau-large-ner-total-onnx)
