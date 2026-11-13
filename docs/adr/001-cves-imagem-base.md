# ADR 001 — CVEs na imagem base python:3.12-slim

**Data:** 2026-11-10  
**Status:** aceito

## Contexto

Trivy (`aquasec/trivy`) apontou 49 CVEs de severidade HIGH e 0 CRITICAL na
imagem `python:3.12-slim` (Debian 13 / trixie) usada como base do serviço `app`.

Resultados detalhados:

| Contagem | Situação                    |
|----------|-----------------------------|
| 47       | affected — sem fix Debian   |
| 2        | fix disponível (zlib1g)     |
| 0        | CRITICAL                    |

CVEs com fix aplicado:

| Biblioteca | CVE             | Fix aplicado no Dockerfile      |
|------------|-----------------|---------------------------------|
| zlib1g     | CVE-2026-76844  | apt-get install --only-upgrade  |
| zlib1g     | CVE-2026-85091  | apt-get install --only-upgrade  |

Exemplo representativo dos 47 restantes (sem fix):

| Biblioteca | CVE            | Severidade | Status   |
|------------|----------------|------------|----------|
| bsdutils   | CVE-2026-76642 | HIGH       | affected |
| util-linux | CVE-2026-76642 | HIGH       | affected |

## Decisão

1. **Fix aplicado imediatamente** para os 2 CVEs do `zlib1g` que têm versão corrigida
   disponível no Debian 13 — `RUN apt-get install -y --only-upgrade zlib1g` no Dockerfile.
2. **Aceitar os 47 restantes** sem ação imediata:
   - Zero CRITICAL.
   - Debian 13 ainda não disponibilizou pacotes corrigidos.
   - Os CVEs afetam utilitários de sistema (util-linux, shadow, libc) não invocados
     de forma que exponha as vulnerabilidades.
   - O contêiner corre como appuser (UID 1000), limitando o impacto de exploit local.

## Consequências

- Re-escanear a cada atualização da imagem base (`docker compose build --pull`)
  e ao iniciar cada bloco maior.
- Se qualquer CVE migrar para CRITICAL ou aparecer Fixed Version nos 47 restantes,
  aplicar o fix e registrar aqui.
- Comando de referência para nova varredura:
  ```
  docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
    aquasec/trivy image --severity HIGH,CRITICAL maprelations-app
  ```
