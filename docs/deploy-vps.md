# Deploy do Sender AI numa VPS (Docker)

> Usa Easypanel? Siga [deploy-easypanel.md](deploy-easypanel.md), que é mais simples.

O app roda como **um container** (painel web + API na porta 8000). O banco é o Oracle
Autonomous Database e os arquivos vão para o OCI Object Storage, os dois na nuvem da Oracle;
a VPS só executa o app.

Credenciais **nunca** entram na imagem nem no git. Elas ficam em quatro coisas que você
copia para a VPS à mão, na pasta do projeto:

| Na VPS | O que é | De onde vem |
|---|---|---|
| `.env` | variáveis do app (Claude, Oracle, OCI, login) | o seu `.env` local |
| `wallet/` | wallet do Autonomous DB, descompactada | a pasta `wallet/` local |
| `oci/config` | config da OCI, com `key_file=/app/oci/<chave>.pem` | o seu `~/.oci/config`, ajustando a linha `key_file` |
| `oci/<chave>.pem` | chave privada da API da OCI | o `.pem` em `~/.oci/` |

## 1. Na VPS: Docker

Precisa de Docker com o plugin Compose (`docker compose version` deve responder). Em Ubuntu/Debian:

```bash
curl -fsSL https://get.docker.com | sh
```

## 2. Código

```bash
git clone -b integra/oracle-unificado https://github.com/No-Country-simulation/G10-Brasil-Equipo-11.git sender-ai
cd sender-ai
```

## 3. Credenciais (do seu computador para a VPS)

No **seu computador**, na pasta do projeto (troque `usuario@ip-da-vps`):

```bash
scp .env usuario@ip-da-vps:~/sender-ai/.env
scp -r wallet usuario@ip-da-vps:~/sender-ai/wallet
ssh usuario@ip-da-vps "mkdir -p ~/sender-ai/oci"
scp ~/.oci/config ~/.oci/*.pem usuario@ip-da-vps:~/sender-ai/oci/
```

Na **VPS**, ajuste a linha `key_file` do `oci/config` para o caminho de dentro do container:

```bash
cd ~/sender-ai
sed -i "s|^key_file=.*|key_file=/app/oci/$(ls oci/*.pem | xargs -n1 basename)|" oci/config
chmod 600 .env oci/* && chmod 700 wallet oci
```

No `.env` da VPS, confira:

- `ADMIN_SENHA`: troque `admin123` por uma senha forte; o app vai ficar na internet.
- `OCI_STORAGE_MODE=oci` e `COMMUNITYLAB_DB_MODE=oracle`.
- Os caminhos da wallet e do config da OCI **não precisam** mudar: o `docker-compose.yml`
  já usa os caminhos de dentro do container.

## 4. Subir

```bash
docker compose up -d --build
docker compose ps                     # deve ficar "healthy" em ~1 minuto
curl -s http://127.0.0.1:8000/prontidao
```

`/prontidao` precisa mostrar `"database":"ok"` e `"object_storage":"ok"`.

## 5. Publicar com HTTPS

O container escuta só em `127.0.0.1:8000`. Quem publica é o proxy da VPS.

**Caddy** (gera o certificado sozinho), no `Caddyfile`:

```
sender.seudominio.com.br {
    reverse_proxy 127.0.0.1:8000
}
```

**nginx**, dentro do `server { ... }` com o certificado já configurado:

```nginx
location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 600s;   # lotes grandes ainda podem levar alguns minutos
}
```

O `proxy_read_timeout` alto é uma margem: com o Claude em paralelo (`LLM_CONCORRENCIA`), um lote
de 50 mensagens leva uma fração do tempo que levava com o Gemini, mas lotes grandes ou contas com limite baixo ainda demoram.

Sem proxy e sem domínio, só para um teste rápido: troque a porta no `docker-compose.yml`
por `"8000:8000"` e acesse `http://ip-da-vps:8000` (sem HTTPS, a senha trafega aberta).

## 6. Oracle: liberar o IP da VPS

Se o Autonomous Database estiver com acesso restrito por IP (*Access control list*),
adicione o IP público da VPS no console da OCI. Sem isso, `/prontidao` mostra
`"database":"indisponivel"`.

## Atualizar depois

```bash
cd ~/sender-ai
git pull
docker compose up -d --build
```

## Problemas comuns

| Sintoma | Causa provável |
|---|---|
| `database: indisponivel` | IP da VPS fora da ACL do Oracle, ou `wallet/` vazia ou no lugar errado |
| `object_storage: indisponivel` | `key_file` do `oci/config` apontando para caminho fora de `/app/oci/` |
| Login cai sozinho | Rodar mais de uma réplica: as sessões ficam na memória do processo (use uma só) |
| Processamento corta no meio | `proxy_read_timeout` baixo no nginx |

Logs: `docker compose logs -f sender-ai`.
