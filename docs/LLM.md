# Integração com o Claude (Anthropic)

Este guia cobre a configuração segura da chave, o teste controlado, o que deixa o processamento rápido e o contrato que o pipeline usa com o backend.

> Até 11/2026 o projeto usava o Google Gemini no plano gratuito. O limite de 12 a 15 chamadas por minuto obrigava o pipeline a esperar cerca de 5 s entre uma mensagem e a seguinte, e um lote de 50 mensagens levava mais de 5 minutos. O provedor passou a ser o Claude, com chamadas em paralelo.

## 1. Configurar a chave com segurança

A chave fica **somente** no arquivo `.env` da sua máquina. O `.gitignore` já ignora `.env` e `.env.*`, então ela não vai para o GitHub.

```powershell
Copy-Item .env.example .env      # só se ainda não existir
notepad .env
```

No `.env`:

1. Preencha `ANTHROPIC_API_KEY=` com a chave criada em [platform.claude.com](https://platform.claude.com) > API Keys.
2. **Apague a linha `LLM_MODO=mock`.** Enquanto ela existir, o sistema fica no modo simulado.
3. Confira o modelo e o paralelismo (seção 3). Os padrões já servem para começar.
4. Salve e feche.

Confira que o git está ignorando o arquivo:

```powershell
git check-ignore -v .env     # deve mostrar: .gitignore:...:.env    .env
git status                   # o .env NÃO pode aparecer na lista
```

Regras:

- Nunca cole a chave em código, issue, pull request, Discord ou conversa com IA.
- Se a chave vazar, revogue-a no Console da Anthropic e gere outra.
- Use só mensagens fictícias nos testes. O texto enviado ao Claude sai da sua máquina; antes de usar dados reais de membros, confira os termos de uso da conta.

## 2. Teste controlado

```powershell
python scripts/teste_llm.py            # classificação de 7 mensagens fictícias (7 chamadas)
python scripts/teste_llm.py --gerar    # inclui post, FAQ e newsletter (cerca de 10 chamadas)
```

As 7 mensagens cobrem as 4 rotas e dois casos difíceis: uma mensagem **irônica**, que o modo simulado classifica errado, e uma que **tenta manipular o modelo** ("ignore as instruções..."). Cada uma tem a rota que uma pessoa revisora escolheria.

O resultado fica em `saida_local/teste_llm/` (ignorado pelo git):

- `relatorio_<data>.md`: tabela de esperado × obtido, erros, ativos gerados e tokens (incluindo os lidos do cache).
- `resultado_<data>.json`: todos os detalhes.

| Marca | Significado |
| --- | --- |
| `OK` / ✅ | O modelo escolheu a rota esperada |
| `ERRO` / ❌ | O modelo escolheu outra rota. Avaliar com quem cuida da classificação se é erro do modelo ou do gabarito |
| `SIM` / "(simulado)" | A chamada falhou nessa mensagem e o sistema usou o modo simulado. A seção "Erros" explica o motivo |

Para medir a qualidade na base de avaliação: `python scripts/avaliar_classificacoes.py --modo claude`.

## 3. Desempenho e configuração

| Variável | Padrão | O que faz |
| --- | --- | --- |
| `CLAUDE_MODELO` | `claude-haiku-5-5` | Modelo usado. O Haiku é o mais rápido e barato; se a qualidade da classificação ou dos textos não bastar, troque por `claude-sonnet-5-5` ou `claude-opus-5-5` e meça com `avaliar_classificacoes.py`. O Haiku não tem o modelo de reserva em caso de recusa (os outros dois têm) |
| `CLAUDE_ESFORCO_CLASSIFICACAO` | `medium` | Quanto o modelo raciocina ao classificar. `low` é um pouco mais rápido |
| `CLAUDE_ESFORCO_GERACAO` | `medium` | Mesmo controle para post, FAQ e newsletter |
| `LLM_CONCORRENCIA` | `8` | Mensagens processadas ao mesmo tempo. `1` volta ao modo sequencial |
| `LLM_RPM` | `0` | Teto opcional de chamadas por minuto. Use se a conta tiver limite baixo |
| `LLM_TENTATIVAS` | `4` | Novas tentativas automáticas do SDK em 429, 5xx e falha de rede |

O que deixa o lote rápido:

- **Paralelismo.** As mensagens de um lote são independentes. A classificação e as FAQs rodam em `LLM_CONCORRENCIA` chamadas simultâneas, e a ordem das análises é mantida.
- **Cache do prompt de sistema.** O prompt do classificador tem cerca de 2 mil tokens e é igual para todas as mensagens. Ele vai marcado com `cache_control`: a primeira mensagem roda sozinha e grava o cache, e as seguintes leem dele (mais rápido e cerca de 90% mais barato nessa parte).
- **Saída estruturada.** As respostas usam um JSON Schema (`output_config.format`). A API garante JSON válido e rótulos dentro da lista, então não sobra pedido repetido por formato.
- **Esforço ajustável.** `CLAUDE_ESFORCO_CLASSIFICACAO=low` deixa a classificação um pouco mais rápida.

Estimativa para um lote de 50 mensagens: com o Gemini gratuito, mais de 5 min só de espera entre chamadas. Com o Claude e 8 chamadas simultâneas, a classificação leva o tempo de cerca de 7 chamadas em sequência (1 de aquecimento do cache + 49 divididas em 8 filas). Os números reais dependem do modelo e do limite da conta; o `teste_llm.py` mostra o tempo de cada mensagem.

> **Limite da conta.** Contas novas da Anthropic têm limite de requisições por minuto mais baixo. Se aparecerem muitos avisos de 429 no log, reduza `LLM_CONCORRENCIA` ou defina `LLM_RPM` um pouco abaixo do limite da conta.

## 4. O que protege o pipeline

| Situação | Comportamento |
| --- | --- |
| Resposta que não é JSON, ou com rótulo desconhecido | Raro com a saída estruturada. Se acontecer, pede de novo uma vez. Persistindo, **só aquela mensagem** usa o modo simulado, e a falha é registrada. O lote continua |
| Variações de rótulo ("Positiva", "Pergunta Técnica", relevância "7") | Normalizadas para o contrato |
| Limite de requisições (HTTP 429), falha temporária (5xx) ou de rede | O SDK espera (respeitando o `retry-after`) e tenta de novo até `LLM_TENTATIVAS` vezes. Esgotadas, só aquela mensagem cai no simulado |
| Chave inválida ou modelo inexistente (4xx) | Falha na hora com mensagem clara, sem gastar tentativas |
| Filtro de segurança recusa o conteúdo | Nos modelos que aceitam, o servidor refaz o pedido num modelo de reserva (`fallbacks: "default"`). Se ainda recusar, a mensagem cai no simulado |
| Resposta cortada pelo limite de tokens | Vira erro claro e a mensagem cai no simulado |
| Mensagem que cai no modo simulado durante a **avaliação** (`--modo claude`) | A execução é marcada como **inválida**: o script avisa, termina com código 1 e registra os casos em `fallback_llm` no `resultado.json` |
| Mensagem com instruções ("ignore as instruções...") | O texto do membro vai delimitado por `<mensagem>`, e o prompt manda tratá-lo como dado |

Os testes `tests/test_llm_robustez.py` simulam todas essas situações sem chamar a API.

## 5. Contrato com o backend

O formato está em `app/schemas.py`. Qualquer mudança nele afeta pipeline, API, painel e armazenamento, então combinem antes.

**Entrada** (`LoteEntrada`, recebido em `POST /processar`):

```json
{
  "origem_comunidade": "Discord_Grupo_ONE_G10",
  "periodo_referencia": "Semana_04",
  "interacoes": [
    {"autor": "Nome", "canal": "#canal", "tipo": "depoimento", "texto": "..."}
  ]
}
```

`tipo` aceita: `depoimento`, `pergunta_tecnica`, `feedback`, `reclamacao`, `projeto`, `outro`.

**Saída** (`RespostaProcessamento`): `status`, `resumo_comunidade`, `analises` (uma por interação, com `tipo`, `sentimento`, `topico`, `relevancia` de 0 a 10 e `rota`), `ativos_distribuicao_gerados` e `armazenamento_oci`.

**Identificador do modo real.** O banco, a API (`/saude` → `modo_llm`) e os filtros do Insights continuam usando o valor `"gemini"` para o modo real, porque a restrição do banco e o histórico já salvo dependem dele. Na interface ele aparece como **Claude**. Lotes antigos processados pelo Gemini e os novos, pelo Claude, ficam no mesmo grupo "modo real".
