// web/js/lotes.js
// Reabre um lote já processado (guardado no Oracle) com as decisões e os alertas tratados.
// A Curadoria passa a mostrar só esse lote, com o aviso "Lote aberto do histórico".
import { store } from './store.js';
import { api } from './api.js';
import { abrirFilaAvulsa } from './fila.js';

export async function abrirLoteSalvo(loteId, abaDestino = 'curadoria') {
  const salvo = await api.abrirLote(loteId);
  abrirFilaAvulsa(salvo, abaDestino);
  store.setState({
    isProcessing: false,
    duplicado: null,
    exportResult: null,
    exportErro: null,
  });
}
