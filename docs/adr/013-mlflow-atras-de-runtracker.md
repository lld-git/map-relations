# ADR 013 — MLflow atrás de `RunTracker`

**Data:** 2026-11-25
**Status:** aceito (plano do B02 §8, D6)

## Contexto

O `eval` produz dezenas de métricas por execução, e comparar execuções ao longo
do tempo (modelo, prompt, nível, lente) é trabalho de uma ferramenta de
experimentos, não de telas do painel. Ao mesmo tempo, o relatório cita trechos
da obra: o princípio 6 proíbe que conteúdo do usuário saia da máquina, e o
princípio 2 manda manter toda dependência externa atrás de um contrato.

## Decisão

- **Contrato:** `RunTracker` em `core/protocols.py` (`start`, `log_params`,
  `log_metrics`, `log_artifact`, `set_tags`, `end`). O domínio e o avaliador só
  conhecem o Protocol. Adaptadores em `research/map_relations/tracking/`:
  `NullTracker` (padrão) e `MlflowTracker`.
- **Recusa de endereço fora da máquina:** `check_local_tracking_uri` (no mesmo
  módulo do contrato) é chamada pelo `MlflowTracker` antes de qualquer conexão e
  pelo `eval --track` antes de calcular qualquer coisa. Aceita `http(s)` só com
  host `mlflow` (rede do compose), `localhost` ou `127.0.0.1`, e armazenamento em
  disco (`file:`, `sqlite:`, caminho). Recusa o resto, inclusive
  `http://127.0.0.1@outro.host` (vale o `hostname` de `urlparse`, não o texto) e
  as palavras `databricks`, `databricks-uc` e `uc`, que o MLflow trata como
  serviço remoto. Há um teste por forma de endereço.
- **Só números e ids no servidor:** parâmetros, métricas e tags nunca carregam
  trecho da obra, nome de pessoa ou citação (teste com um gravador que confere
  isso). O relatório (`report.md` e `report.json`, que citam a obra) vai só como
  artefato, para o servidor local em `./mlflow_data/`.
- **Serviço:** `mlflow` no `docker-compose.yml`, perfil `mlflow` (nunca no CI),
  imagem `ghcr.io/mlflow/mlflow:v3.18.0`, publicado só em `127.0.0.1:5010`, dados
  (SQLite e artefatos) em `./mlflow_data/`, listado no `.gitignore` e no
  `.dockerignore`. `--allowed-hosts` lista os três hosts de acesso; o servidor
  recusa os demais. `make mlflow` sobe, `make mlflow-stop` para.
- **Cliente:** `mlflow-skinny==3.18.0` no grupo dev, com a **mesma versão** do
  servidor (um teste confere as duas). Import local no adaptador: a imagem de
  produção não o instala nem o carrega.
- **Nomes das métricas** (estáveis): `p|r|f1.<medida>.<tipo>`,
  `p|r|f1.<medida>.micro`, `f1.<medida>.macro`, `p|r|f1.familia.<medida>.<pai>`,
  `atribuicao.classe|asserted_by|correta`, `prova.<medida>.*`,
  `nivel.<n>.f1.<medida>`, `lente.<l>.f1.<medida>`, `controle.violacoes|taxa`,
  `pessoas.recall`, `json_valido.taxa`, `encaixado.*`.
- **CI sem servidor:** os testes usam `NullTracker`, um gravador falso e um
  teste do adaptador em `file://` num diretório temporário.

## Consequências

- O MLflow 3.x deixou o armazenamento em arquivos em modo de manutenção e o
  bloqueia por padrão (`MLFLOW_ALLOW_FILE_STORE`). Só o teste do adaptador opta
  por ele; o serviço usa SQLite. Se uma versão futura remover o modo, o teste
  passa a usar `sqlite:///` num diretório temporário.
- `make eval … TRACK=1` exige o serviço no ar (`make mlflow`); o endereço padrão
  vem do `docker-compose.yml` (`http://mlflow:5000`) e pode ser trocado no `.env`.
- Tabelas de métricas, histórico e comparação entre execuções são do MLflow. O
  B02b fica só com as telas de domínio (plano §8).
- Peso da dependência: `mlflow-skinny` e suas 25 dependências entram só na
  imagem dev. Se pesar demais, o plano prevê falar com a API REST por `httpx`
  atrás do mesmo `RunTracker`.
