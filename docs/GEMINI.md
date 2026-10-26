# Integração com o Gemini

Responsável: Renato. Este guia cobre a configuração segura da chave, o teste controlado e o contrato que o pipeline usa com o backend.

## 1. Configurar a chave com segurança

A chave fica **somente** no arquivo `.env` da sua máquina. O `.gitignore` já ignora `.env` e `.env.*`, então ela não vai para o GitHub.

```powershell
Copy-Item .env.example .env      # só se ainda não existir
notepad .env
```

No `.env`:

1. Preencha `GEMINI_API_KEY=` com a sua chave.
2. **Apague a linha `LLM_MODO=mock`.** Enquanto ela existir, o sistema fica no modo simulado.
3. Salve e feche.

Confira que o git está ignorando o arquivo:

```powershell
git check-ignore -v .env     # deve mostrar: .gitignore:...:.env    .env
git status                   # o .env NÃO pode aparecer na lista
```

Regras:

- Nunca cole a chave em código, issue, pull request, Discord ou conversa com IA.
- Se a chave vazar, apague-a no [Google AI Studio](https://aistudio.google.com/apikey) e gere outra.
- Use só mensagens fictícias nos testes. O texto enviado ao Gemini sai da sua máquina; antes de usar dados reais de membros, confira os termos de uso do plano.

## 2. Teste controlado

```powershell
python scripts/teste_gemini.py            # classificação de 7 mensagens fictícias (cerca de 7 chamadas)
python scripts/teste_gemini.py --gerar    # inclui post, FAQ e newsletter (cerca de 10 chamadas)
```

As 7 mensagens cobrem as 4 rotas e dois casos difíceis: uma mensagem **irônica**, que o modo simulado classifica errado, e uma que **tenta manipular o modelo** ("ignore as instruções..."). Cada uma tem a rota que uma pessoa revisora escolheria.

O resultado fica em `saida_local/teste_gemini/` (ignorado pelo git):

- `relatorio_<data>.md`: tabela de esperado × obtido, erros e ativos gerados. É este arquivo que você compartilha com a equipe.
- `resultado_<data>.json`: todos os detalhes.

Como ler o relatório:

| Marca | Significado |
| --- | --- |
| `OK` / ✅ | O Gemini escolheu a rota esperada |
| `ERRO` / ❌ | O Gemini escolheu outra rota. Avaliar com o Matheus se é erro do modelo ou do gabarito |
| `SIM` / "(simulado)" | O Gemini falhou duas vezes nessa mensagem e o sistema usou o modo simulado. A seção "Erros" explica o motivo |

## 3. O que protege o pipeline

| Situação | Comportamento |
| --- | --- |
| Resposta que não é JSON, ou com rótulo desconhecido | Pede de novo uma vez. Persistindo, **só aquela mensagem** usa o modo simulado, e a falha é registrada. O lote continua |
| Variações de rótulo ("Positiva", "Pergunta Técnica", relevância "7") | Normalizadas para o contrato |
| Limite de requisições (HTTP 429) | Espera 10, 20 e 40 s antes de tentar de novo |
| Falha temporária do servidor (5xx) ou de rede | Espera 2, 4 e 8 s antes de tentar de novo |
| Chave inválida ou modelo inexistente (4xx) | Falha na hora com mensagem clara, sem gastar tentativas |
| Mensagem com instruções ("ignore as instruções...") | O texto do membro vai delimitado por `<mensagem>`, e o prompt manda tratá-lo como dado |

Os testes `tests/test_gemini_robustez.py` simulam todas essas situações sem chamar a API.

## 4. Contrato com o backend

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

**Ponto para decidir com o backend:** hoje, quando o Gemini falha numa mensagem, o pipeline usa o modo simulado e só registra isso no log. Vale avaliar um campo opcional, por exemplo `avisos`, na resposta, para a API e o painel mostrarem quais itens não vieram do Gemini.
