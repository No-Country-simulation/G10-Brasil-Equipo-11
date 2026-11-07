// web/js/api.js
// Cliente HTTP REST para comunicação direta com o backend FastAPI (< 60 linhas)

export const api = {
  async verificarSaude() {
    const res = await fetch('/saude');
    if (!res.ok) throw new Error(`Falha no backend (${res.status})`);
    return res.json();
  },

  async carregarExemplo() {
    const res = await fetch('/api/exemplo');
    if (!res.ok) throw new Error(`Falha ao obter lote de exemplo (${res.status})`);
    return res.json();
  },

  async processarLote(corpo, isMultipart = false) {
    const options = {
      method: 'POST',
      body: isMultipart ? corpo : JSON.stringify(corpo),
    };
    if (!isMultipart) {
      options.headers = { 'Content-Type': 'application/json' };
    }
    const res = await fetch('/processar', options);
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
    if (!res.ok) throw new Error(`Falha ao exportar aprovados (${res.status})`);
    return res.json();
  },
};
