// web/js/lotes.js
// Reabre um lote já processado (guardado no Oracle) com as decisões e os alertas tratados.
import { store } from './store.js';
import { api } from './api.js';
import { extrairItensCuradoria } from './views/curation-view.js';

export async function abrirLoteSalvo(loteId, abaDestino = 'visao') {
  const salvo = await api.abrirLote(loteId);
  const itens = extrairItensCuradoria(salvo.resultado);
  const decisoes = {};
  itens.forEach(it => { decisoes[it.id] = salvo.decisoes[it.id] || 'p'; });
  const pendente = itens.find(it => decisoes[it.id] === 'p');
  store.setState({
    resultado: salvo.resultado,
    loteId: salvo.lote_id,
    processadoEm: salvo.processado_em,
    origem: salvo.origem || store.getState().origem,
    periodo: salvo.periodo || store.getState().periodo,
    decisoes,
    textosEditados: {},
    autorizado: Boolean(salvo.autorizado),
    alertas: salvo.alertas || {},
    activeItem: pendente ? pendente.id : (itens[0] ? itens[0].id : null),
    activeTab: abaDestino,
    isProcessing: false,
    duplicado: null,
    exportResult: null,
    exportErro: null,
  });
}
