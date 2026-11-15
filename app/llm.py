"""Cliente de LLM (Claude, da Anthropic) com validação de resposta, paralelismo e modo simulado.

Sem ANTHROPIC_API_KEY (ou com LLM_MODO=mock), tudo roda com respostas simuladas.
Isso deixa a equipe desenvolver interface e orquestração sem gastar créditos da API.

A chave fica SOMENTE no .env local (ignorado pelo git). Nada aqui imprime a chave.

O que deixa o processamento rápido:
- `mapear` processa as mensagens do lote em paralelo (LLM_CONCORRENCIA chamadas ao mesmo tempo);
- `mapear_em_cadeia` começa a FAQ de cada mensagem assim que ela é classificada, sem esperar as outras;
- `aquecer_cliente_em_segundo_plano` carrega o SDK quando o servidor sobe, e não no primeiro lote;
- o prompt de sistema vai com `cache_control`: a partir da 2ª chamada ele é lido do cache,
  o que reduz o tempo até a resposta e o custo de entrada;
- respostas JSON usam saída estruturada (`output_config.format`): o modelo não devolve
  JSON quebrado, então não há novos pedidos por formato;
- classificação e geração usam esforço `medium` (CLAUDE_ESFORCO_* no .env).
"""
import json
import logging
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Iterable, TypeVar

log = logging.getLogger("communitylab.llm")

# Identificador do modo real gravado no banco, nos lotes e na API (/saude -> modo_llm).
# Continua "gemini" para não quebrar o histórico já salvo nem a restrição do banco;
# o provedor por trás dele agora é o Claude.
MODO_REAL = "gemini"

MODELO_PADRAO = "claude-haiku-5-5"  # rápido e barato para classificar lotes
ESFORCO_CLASSIFICACAO_PADRAO = "medium"
ESFORCO_GERACAO_PADRAO = "medium"
CONCORRENCIA_PADRAO = 8
TENTATIVAS_SDK_PADRAO = 4  # o SDK repete 408/409/429/5xx e falhas de rede, respeitando o retry-after
TIMEOUT_S = 120.0

# Modelos que aceitam o fallback do servidor quando o filtro de segurança recusa um pedido.
MODELOS_COM_FALLBACK = {"claude-opus-5-5", "claude-opus-5", "claude-fable-5-1", "claude-fable-5-2",
                        "claude-sonnet-5-5"}
BETA_FALLBACK = "server-side-fallback-2026-07-01"

# Contadores para o relatório do teste controlado (scripts/teste_llm.py)
ESTATISTICAS = {"chamadas": 0, "respostas_invalidas": 0, "tokens_entrada": 0,
                "tokens_cache_lidos": 0, "tokens_saida": 0}
_trava_estatisticas = threading.Lock()


def _contar(**incrementos: int):
    with _trava_estatisticas:
        for chave, valor in incrementos.items():
            ESTATISTICAS[chave] = ESTATISTICAS.get(chave, 0) + (valor or 0)


class ErroLLM(RuntimeError):
    """Falha definitiva ao obter uma resposta válida do modelo."""


def _inteiro_env(nome: str, padrao: int, minimo: int = 0) -> int:
    try:
        return max(minimo, int(os.getenv(nome) or padrao))
    except ValueError:
        return padrao


def modelo() -> str:
    return os.getenv("CLAUDE_MODELO") or MODELO_PADRAO


def esforco_classificacao() -> str:
    return os.getenv("CLAUDE_ESFORCO_CLASSIFICACAO") or ESFORCO_CLASSIFICACAO_PADRAO


def esforco_geracao() -> str:
    return os.getenv("CLAUDE_ESFORCO_GERACAO") or ESFORCO_GERACAO_PADRAO


def concorrencia() -> int:
    """Quantas chamadas ao modelo podem acontecer ao mesmo tempo (LLM_CONCORRENCIA). 1 = sequencial."""
    return _inteiro_env("LLM_CONCORRENCIA", CONCORRENCIA_PADRAO, minimo=1)


def chamadas_por_minuto() -> float:
    """Teto opcional de chamadas por minuto (LLM_RPM). 0 (padrão) desliga: o SDK já trata o HTTP 429."""
    try:
        return max(0.0, float(os.getenv("LLM_RPM") or 0))
    except ValueError:
        return 0.0


_trava_ritmo = threading.Lock()
_proxima_vaga = 0.0


def _aguardar_vez():
    """Reserva o próximo horário livre dentro do teto por minuto. Seguro com várias threads."""
    global _proxima_vaga
    rpm = chamadas_por_minuto()
    if not rpm:
        return
    with _trava_ritmo:
        agora = time.monotonic()
        vaga = max(agora, _proxima_vaga)
        _proxima_vaga = vaga + 60.0 / rpm
    if vaga > agora:
        time.sleep(vaga - agora)


def modo_mock() -> bool:
    return os.getenv("LLM_MODO", "").lower() == "mock" or not os.getenv("ANTHROPIC_API_KEY")


_cliente = None
_chave_do_cliente = None
_trava_cliente = threading.Lock()


def _obter_cliente():
    """Reaproveita o cliente (e suas conexões) entre chamadas e threads; recria se a chave mudar."""
    global _cliente, _chave_do_cliente
    chave = os.environ["ANTHROPIC_API_KEY"]
    with _trava_cliente:
        if _cliente is None or chave != _chave_do_cliente:
            import anthropic
            _cliente = anthropic.Anthropic(
                api_key=chave,
                max_retries=_inteiro_env("LLM_TENTATIVAS", TENTATIVAS_SDK_PADRAO),
                timeout=TIMEOUT_S,
            )
            _chave_do_cliente = chave
        return _cliente


def _parametros(sistema: str, usuario: str, schema: dict | None, esforco: str | None,
                max_tokens: int) -> dict:
    nome_modelo = modelo()
    parametros: dict[str, Any] = {
        "model": nome_modelo,
        "max_tokens": max_tokens,
        # O prompt de sistema é igual em todas as mensagens do lote: fica no cache.
        "system": [{"type": "text", "text": sistema, "cache_control": {"type": "ephemeral"}}],
        "messages": [{"role": "user", "content": usuario}],
    }
    config: dict[str, Any] = {}
    if esforco:
        config["effort"] = esforco
    if schema:
        config["format"] = {"type": "json_schema", "schema": schema}
    if config:
        parametros["output_config"] = config
    if nome_modelo in MODELOS_COM_FALLBACK:
        parametros["betas"] = [BETA_FALLBACK]
        parametros["fallbacks"] = "default"
    return parametros


def chamar_llm(sistema: str, usuario: str, json_saida: bool = False, *, schema: dict | None = None,
               esforco: str | None = None, max_tokens: int = 8000) -> str:
    """Chama o Claude e devolve o texto da resposta.

    Novas tentativas em 429/5xx/rede ficam com o SDK. Erro de chave, modelo ou pedido falha na hora.
    `json_saida` existe por compatibilidade: o formato JSON vem do `schema` (saída estruturada).
    """
    import anthropic

    parametros = _parametros(sistema, usuario, schema, esforco, max_tokens)
    cliente = _obter_cliente()
    criar = cliente.beta.messages.create if "betas" in parametros else cliente.messages.create
    _aguardar_vez()
    _contar(chamadas=1)
    try:
        resposta = criar(**parametros)
    except anthropic.APIStatusError as erro:
        codigo = erro.status_code
        if codigo in (408, 409, 429) or codigo >= 500:
            raise ErroLLM(f"Claude indisponível depois das novas tentativas (HTTP {codigo}).") from erro
        raise ErroLLM(f"Claude recusou o pedido (HTTP {codigo}). Confira a chave e o nome do modelo "
                      f"({modelo()}).") from erro
    except anthropic.APIConnectionError as erro:
        raise ErroLLM(f"Sem conexão com a API do Claude ({type(erro).__name__}).") from erro

    uso = getattr(resposta, "usage", None)
    if uso is not None:
        _contar(tokens_entrada=getattr(uso, "input_tokens", 0) or 0,
                tokens_cache_lidos=getattr(uso, "cache_read_input_tokens", 0) or 0,
                tokens_saida=getattr(uso, "output_tokens", 0) or 0)

    if resposta.stop_reason == "refusal":
        raise ErroLLM("O modelo recusou responder a este conteúdo (filtro de segurança).")
    if resposta.stop_reason == "max_tokens":
        raise ErroLLM(f"A resposta passou do limite de {max_tokens} tokens e veio cortada.")
    texto = "".join(bloco.text for bloco in resposta.content if bloco.type == "text").strip()
    if not texto:
        raise ErroLLM("O modelo devolveu uma resposta vazia.")
    return texto


def _extrair_json(texto: str) -> Any:
    texto = texto.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(texto)


def chamar_llm_json(sistema: str, usuario: str, validar: Callable[[Any], dict] | None = None,
                    tentativas_formato: int = 2, *, schema: dict | None = None,
                    esforco: str | None = None, max_tokens: int = 8000) -> dict:
    """Pede JSON ao modelo e valida. Resposta fora do formato gera um novo pedido; persistindo, ErroLLM.

    `schema` liga a saída estruturada (JSON garantido pela API). `validar` recebe o JSON e devolve
    o dicionário normalizado, ou levanta ValueError (regras que o schema não expressa).
    """
    ultimo = None
    for _ in range(tentativas_formato):
        texto = chamar_llm(sistema, usuario, json_saida=True, schema=schema, esforco=esforco,
                           max_tokens=max_tokens)
        try:
            dados = _extrair_json(texto)
            if not isinstance(dados, dict):
                raise ValueError("a resposta não é um objeto JSON")
            return validar(dados) if validar else dados
        except (json.JSONDecodeError, ValueError, TypeError, KeyError) as erro:
            ultimo = erro
            _contar(respostas_invalidas=1)
            log.warning("Claude: resposta fora do formato (%s). Pedindo de novo.", erro)
    raise ErroLLM(f"Resposta fora do formato após {tentativas_formato} tentativas: {ultimo}")


T = TypeVar("T")
R = TypeVar("R")


S = TypeVar("S")


def mapear(funcao: Callable[[T], R], itens: Iterable[T], *, aquecer_cache: bool = True) -> list[R]:
    """Aplica `funcao` a cada item em paralelo, mantendo a ordem.

    O primeiro item roda sozinho: ele grava o prompt de sistema no cache e as chamadas
    seguintes, já em paralelo, leem do cache. Com `aquecer_cache=False` todos começam juntos
    (vale para prompts curtos, em que esperar a primeira chamada custa mais do que o cache poupa).
    No modo simulado tudo roda em sequência.
    """
    itens = list(itens)
    limite = concorrencia()
    if modo_mock() or limite <= 1 or len(itens) <= 1:
        return [funcao(item) for item in itens]
    if not aquecer_cache:
        with ThreadPoolExecutor(max_workers=min(limite, len(itens)),
                                thread_name_prefix="llm") as executor:
            return list(executor.map(funcao, itens))
    primeiro = funcao(itens[0])
    with ThreadPoolExecutor(max_workers=min(limite, len(itens) - 1),
                            thread_name_prefix="llm") as executor:
        return [primeiro, *executor.map(funcao, itens[1:])]


def mapear_em_cadeia(primeira: Callable[[T], R], segunda: Callable[[R], S],
                     itens: Iterable[T]) -> list[tuple[R, S]]:
    """Aplica `primeira` a cada item e, assim que cada resultado sai, `segunda` sobre ele.

    Devolve os pares (resultado da primeira, resultado da segunda) na ordem dos itens.
    A segunda etapa de um item não espera a primeira etapa dos outros: as duas se sobrepõem
    dentro das mesmas LLM_CONCORRENCIA chamadas simultâneas.

    Como em `mapear`, a primeira chamada de `primeira` roda sozinha para gravar o prompt de
    sistema no cache. No modo simulado tudo roda em sequência: primeiro toda a etapa 1,
    depois toda a etapa 2.
    """
    itens = list(itens)
    limite = concorrencia()
    if modo_mock() or limite <= 1 or len(itens) <= 1:
        resultados = [primeira(item) for item in itens]
        return [(resultado, segunda(resultado)) for resultado in resultados]

    def cadeia(item: T) -> tuple[R, S]:
        resultado = primeira(item)
        return resultado, segunda(resultado)

    primeiro = primeira(itens[0])
    with ThreadPoolExecutor(max_workers=min(limite, len(itens)),
                            thread_name_prefix="llm") as executor:
        futuros = [executor.submit(lambda: (primeiro, segunda(primeiro))),
                   *(executor.submit(cadeia, item) for item in itens[1:])]
        return [futuro.result() for futuro in futuros]


def aquecer_cliente() -> None:
    """Carrega o SDK e cria o cliente antes do primeiro lote. No modo simulado não faz nada.

    Importar o SDK leva vários segundos; sem isto, quem paga é o primeiro lote depois de
    o servidor subir. Falha aqui nunca derruba nada: o primeiro lote tenta de novo.
    """
    if modo_mock():
        return
    try:
        _obter_cliente()
    except Exception as erro:
        log.warning("Não foi possível preparar o cliente do Claude (%s).", type(erro).__name__)


def aquecer_cliente_em_segundo_plano() -> threading.Thread | None:
    """Dispara `aquecer_cliente` numa thread, sem atrasar a subida do servidor."""
    if modo_mock():
        return None
    thread = threading.Thread(target=aquecer_cliente, name="llm-aquecimento", daemon=True)
    thread.start()
    return thread
