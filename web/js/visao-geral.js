// web/js/visao-geral.js
// Carrega a Visão geral do banco (pendências de todos os lotes) e trata alertas a partir dela.
import { store } from './store.js';
import { api } from './api.js';

export async function carregarVisaoGeral() {
  const atual = store.getState().visaoGeral;
  if (atual.carregando) return;
  store.setState({ visaoGeral: { ...atual, carregando: true, erro: null } });
  try {
    const dados = await api.obterVisaoGeral();
    store.setState({ visaoGeral: { dados, carregando: false, erro: null } });
  } catch (err) {
    store.setState(s => ({ visaoGeral: { ...s.visaoGeral, carregando: false, erro: err.message } }));
  }
}

// Tira o alerta da tela na hora e grava no lote de origem. Se o banco recusar, recarrega.
export function tratarAlertaVisaoGeral(loteId, ordem, status) {
  store.setState(s => {
    const patch = {};
    const dados = s.visaoGeral.dados;
    if (dados) {
      const lotes = (dados.lotes_pendentes || [])
        .map(l => (l.lote_id === loteId ? { ...l, alertas_pendentes: Math.max(0, l.alertas_pendentes - 1) } : l))
        .filter(l => l.ativos_pendentes > 0 || l.alertas_pendentes > 0);
      patch.visaoGeral = {
        ...s.visaoGeral,
        dados: {
          ...dados,
          lotes_pendentes: lotes,
          alertas_pendentes: (dados.alertas_pendentes || []).filter(a => !(a.lote_id === loteId && a.ordem === ordem)),
          alertas_tratados_janela: (dados.alertas_tratados_janela || 0) + 1,
        },
      };
    }
    if (s.loteId === loteId) {
      patch.alertas = { ...s.alertas, [ordem]: status };
    }
    return patch;
  });

  const falhou = async (detalhe) => {
    await carregarVisaoGeral(); // devolve o alerta à tela, como está no banco
    store.setState(s => ({ visaoGeral: { ...s.visaoGeral,
      erro: `O alerta não foi salvo${detalhe ? `: ${detalhe}` : ''}. Tente de novo.` } }));
  };
  api.tratarAlerta(loteId, ordem, status)
    .then(res => { if (res?.salvo_no_banco !== true) falhou(res?.detalhe); })
    .catch(() => falhou());
}
