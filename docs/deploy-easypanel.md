# Deploy do Sender AI no Easypanel

O Easypanel constrói a imagem a partir do `Dockerfile` do repositório, publica com HTTPS e
guarda as credenciais na configuração do serviço. Nada secreto passa pelo GitHub.

Sem Easypanel, use o `docker-compose.yml` ([deploy-vps.md](deploy-vps.md)).

## O que vai para o Easypanel

| Onde, no Easypanel | Conteúdo |
|---|---|
| Environment | as variáveis do app |
| Mount (File) `/app/wallet/tnsnames.ora` | o arquivo `wallet/tnsnames.ora` |
| Mount (File) `/app/wallet/ewallet.pem` | o arquivo `wallet/ewallet.pem` |
| Mount (File) `/app/oci/config` | o config da OCI com `key_file=/app/oci/chave.pem` |
| Mount (File) `/app/oci/chave.pem` | a chave privada `.pem` da API da OCI |

Da wallet só esses dois arquivos de texto são necessários: o driver do Oracle (modo thin)
não usa `cwallet.sso` nem `ewallet.p12`.

### Textos prontos para colar

Na sua máquina, na raiz do projeto, rode `python scripts/preparar_easypanel.py`. Ele gera a
pasta `deploy-easypanel/` (ignorada pelo git e pelo Docker) com:

- `1-variaveis-de-ambiente.txt`: o `.env` com os caminhos de dentro do container, sem
  aspas (o Easypanel guarda o valor literal) e sem variáveis repetidas;
- `3-oci-config.txt`: o `~/.oci/config` com `key_file=/app/oci/chave.pem`.

A wallet e a chave você copia dos arquivos originais (`wallet/` e `~/.oci/*.pem`).

## Passo a passo

1. **Projeto → + Service → App.**
2. **Source:** GitHub, repositório `No-Country-simulation/G10-Brasil-Equipo-11`, branch
   `integra/oracle-unificado`, Build Path `/`. Se o Easypanel não tiver acesso à organização
   no GitHub, use **Git** com a URL `https://github.com/No-Country-simulation/G10-Brasil-Equipo-11.git`
   (funciona se o repositório for público).
3. **Build:** Dockerfile, arquivo `Dockerfile`.
4. **Environment:** cole o conteúdo de `1-variaveis-de-ambiente.txt`.
   **Troque `ADMIN_SENHA`** por uma senha forte: o app fica na internet.
5. **Mounts → Add File Mount**, quatro vezes, com os caminhos da tabela acima.
6. **Domains:** adicione o domínio (ou use o automático do Easypanel) com **porta 8000**.
   O HTTPS é do Easypanel.
7. **Deploy.** A primeira construção leva alguns minutos (imagem de ~1,6 GB).
8. Abra `https://<seu-domínio>/prontidao`: precisa mostrar `"database":"ok"` e
   `"object_storage":"ok"`.

## Oracle: liberar o IP da VPS

Se o Autonomous Database estiver com acesso restrito por IP (*Access control list*), inclua
o IP público da VPS no console da OCI. Sem isso, `/prontidao` mostra `"database":"indisponivel"`.

## Cuidados

- **Uma réplica só.** As sessões de login ficam na memória do processo; com duas réplicas o
  login cai sozinho.
- **Atualizar:** depois de um `git push` na branch, clique em **Deploy** (ou ligue o
  deploy automático no Easypanel).
- **Logs:** aba *Logs* do serviço.

| Sintoma | Causa provável |
|---|---|
| `database: indisponivel` | IP fora da ACL do Oracle; senha com aspas na variável; arquivos da wallet com caminho errado |
| `object_storage: indisponivel` | `key_file` do config diferente de `/app/oci/chave.pem`, ou a chave colada incompleta |
| Login cai sozinho | Mais de uma réplica |
