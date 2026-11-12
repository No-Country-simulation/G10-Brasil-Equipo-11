// web/js/api.js
// Cliente HTTP REST para comunicação direta com o backend FastAPI (< 60 linhas)

export const api = {
  async verificarSaude() {
    const res = await fetch('/saude');
    if (!res.ok) throw new Error(`Falha no backend (${res.status})`);
    return res.json();
  },

  async carregarExemplo(tipo = 'padrao') {
    const url = tipo === 'padrao' ? '/api/exemplo' : `/api/exemplo?tipo=${encodeURIComponent(tipo)}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`Falha ao obter lote de exemplo (${res.status})`);
    return res.json();
  },

  async obterFontes() {
    const res = await fetch('/api/fontes');
    if (!res.ok) throw new Error(`Falha ao obter fontes (${res.status})`);
    return res.json();
  },

  // Pergunta ao backend se estas mensagens já foram processadas. Qualquer falha vira "não".
  async verificarLote(interacoes) {
    try {
      const res = await fetch('/api/lotes/verificar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ interacoes }),
      });
      if (!res.ok) return null;
      return (await res.json()).existente || null;
    } catch {
      return null;
    }
  },

  async abrirLote(loteId) {
    const res = await fetch(`/api/lotes/${encodeURIComponent(loteId)}`);
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Falha ao abrir o lote (${res.status})`);
    }
    return res.json();
  },

  async processarLote(corpo, isMultipart = false, reprocessar = false) {
    const options = {
      method: 'POST',
      body: isMultipart ? corpo : JSON.stringify(corpo),
    };
    if (!isMultipart) {
      options.headers = { 'Content-Type': 'application/json' };
    }
    const res = await fetch(reprocessar ? '/processar?reprocessar=true' : '/processar', options);
    if (!res.ok) {
      const detalhe = await res.text();
      try {
        const json = JSON.parse(detalhe);
        throw new Error(json.detail || 'Erro ao processar lote.');
      } catch {
        throw new Error(detalhe || 'Erro desconhecido ao processar lote.');
      }
    }
    return res.json();
  },

  async exportarAprovados(pacote) {
    const res = await fetch('/api/curadoria/exportar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(pacote),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Falha ao exportar aprovados (${res.status})`);
    }
    return res.json();
  },

  async salvarDecisao(loteId, chave, decisao, textos = {}, autorizacao = false) {
    const res = await fetch('/api/curadoria/decidir', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        lote_id: loteId,
        chave,
        decisao,
        textos,
        autorizacao,
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      console.warn('Falha ao salvar decisão no banco:', err.detail || res.status);
    }
    return res.json().catch(() => ({}));
  },

  async tratarAlerta(loteId, ordem, status) {
    const res = await fetch('/api/alertas/tratar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        lote_id: loteId,
        ordem,
        status,
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      console.warn('Falha ao atualizar alerta no banco:', err.detail || res.status);
    }
    return res.json().catch(() => ({}));
  },

  async obterStatusAuth() {
    const res = await fetch('/api/auth/status');
    if (!res.ok) throw new Error(`Falha ao checar status de auth (${res.status})`);
    return res.json();
  },

  async login(usuario, senha) {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ usuario, senha }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Falha ao realizar login.');
    }
    return res.json();
  },

  async logout() {
    const res = await fetch('/api/auth/logout', { method: 'POST' });
    if (!res.ok) throw new Error(`Falha no logout (${res.status})`);
    return res.json();
  },

  async obterInsights(filtros = {}) {
    const params = new URLSearchParams();
    if (filtros.inicio) params.set('inicio', filtros.inicio);
    if (filtros.fim) params.set('fim', filtros.fim);
    if (filtros.modo) params.set('modo', filtros.modo);
    if (filtros.comunidade) params.set('comunidade', filtros.comunidade);
    if (filtros.canal) params.set('canal', filtros.canal);
    if (filtros.demo) params.set('demo', 'true');
    const qs = params.toString();
    const res = await fetch(qs ? `/api/insights?${qs}` : '/api/insights');
    if (!res.ok) throw new Error(`Falha ao obter insights (${res.status})`);
    return res.json();
  },
};
