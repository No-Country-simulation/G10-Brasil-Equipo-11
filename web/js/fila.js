// web/js/fila.js
// Fila única da Curadoria: guarda o estado de cada lote e projeta o "lote em foco" nos campos
// que a tela já usa (resultado, loteId, decisoes, textosEditados, autorizado...). Assim o editor,
// a autorização do post e a gravação das decisões continuam iguais, um lote por vez por baixo.
import { store } from './store.js';
import { api } from './api.js';
import { extrairItensCuradoria } from './views/curation-view.js';

const CAMPOS = ['resultado', 'decisoes', 'textosEditados', 'autorizado', 'alertas', 'origem', 'periodo', 'processadoEm'];

export const FILA_VAZIA = { carregada: false, carregando: false, erro: null, avulso: false, ordem: [], lotes: {} };

const SEM_FOCO = {
  resultado: null, loteId: null, decisoes: {}, textosEditados: {}, autorizado: false, alertas: {}, activeItem: null,
};

function estadoDoLote(salvo) {
  const itens = extrairItensCuradoria(salvo.resultado);
  const decisoes = {};
  itens.forEach(it => { decisoes[it.id] = (salvo.decisoes || {})[it.id] || 'p'; });
  return {
    resultado: salvo.resultado,
    decisoes,
    textosEditados: {},
    autorizado: Boolean(salvo.autorizado),
    alertas: salvo.alertas || {},
    origem: salvo.origem || store.getState().origem,
    periodo: salvo.periodo || store.getState().periodo,
    processadoEm: salvo.processado_em,
  };
}

function projetar(loteId, estado, itemId) {
  const patch = { loteId, activeItem: itemId };
  CAMPOS.forEach(c => { patch[c] = estado[c]; });
  return patch;
}

// Os lotes com o lote em foco atualizado a partir do que está na tela.
export function lotesSincronizados(s = store.getState()) {
  const { fila, loteId } = s;
  if (!loteId || !fila.lotes[loteId]) return fila.lotes;
  const atual = {};
  CAMPOS.forEach(c => { atual[c] = s[c]; });
  return { ...fila.lotes, [loteId]: atual };
}

function idsDoLote(estado) {
  return extrairItensCuradoria(estado?.resultado).map(it => it.id);
}

export function primeiroPendente(estado) {
  const ids = idsDoLote(estado);
  return ids.find(id => estado.decisoes[id] === 'p') || ids[0] || null;
}

function aplicarFila(lotesApi, { avulso = false, focoLoteId = null } = {}) {
  const lotes = {};
  const ordem = [];
  lotesApi.forEach(salvo => {
    lotes[salvo.lote_id] = estadoDoLote(salvo);
    ordem.push(salvo.lote_id);
  });
  const temPendente = id => Object.values(lotes[id].decisoes).includes('p');
  const foco = (focoLoteId && lotes[focoLoteId]) ? focoLoteId : (ordem.find(temPendente) || ordem[0] || null);
  store.setState({
    fila: { ...FILA_VAZIA, carregada: true, avulso, ordem, lotes },
    ...(foco ? projetar(foco, lotes[foco], primeiroPendente(lotes[foco])) : SEM_FOCO),
    activeTab: 'curadoria',
    exportResult: null,
    exportErro: null,
  });
}

export async function carregarFila({ focoLoteId = null } = {}) {
  const atual = store.getState().fila;
  if (atual.carregando) return;
  store.setState({ fila: { ...atual, carregando: true, erro: null }, activeTab: 'curadoria' });
  try {
    const dados = await api.obterFilaCuradoria();
    if (dados.oracle_configurado === false) {
      store.setState(s => ({ fila: { ...s.fila, carregando: false, erro: dados.mensagem } }));
      return;
    }
    aplicarFila(dados.lotes || [], { focoLoteId });
  } catch (err) {
    store.setState(s => ({ fila: { ...s.fila, carregando: false, erro: err.message } }));
  }
}

// Entrada da Curadoria: reaproveita a fila carregada ou busca de novo.
export async function abrirCuradoria({ focoLoteId = null } = {}) {
  const s = store.getState();
  if (!s.fila.carregada || s.fila.avulso) return carregarFila({ focoLoteId });
  if (focoLoteId && s.fila.lotes[focoLoteId]) {
    focar(focoLoteId, primeiroPendente(lotesSincronizados(s)[focoLoteId]));
  }
  store.setState({ activeTab: 'curadoria' });
  return undefined;
}

// Lote aberto do histórico (Insights) ou o já importado: a fila vira só ele.
export function abrirFilaAvulsa(salvo, abaDestino = 'curadoria') {
  aplicarFila([salvo], { avulso: true });
  store.setState({ activeTab: abaDestino });
}

export function focar(loteId, itemId) {
  const s = store.getState();
  const lotes = lotesSincronizados(s);
  if (!lotes[loteId]) return;
  store.setState({ fila: { ...s.fila, lotes }, ...projetar(loteId, lotes[loteId], itemId) });
}

// Próximo pendente: no lote em foco depois do item atual, depois nos lotes seguintes (dando a volta),
// por fim nos itens anteriores do lote em foco.
export function proximoPendente() {
  const s = store.getState();
  const lotes = lotesSincronizados(s);
  const { ordem } = s.fila;
  const atual = s.loteId;
  const candidatos = [];
  const ids = lotes[atual] ? idsDoLote(lotes[atual]) : [];
  const pos = ids.indexOf(s.activeItem);
  ids.slice(pos + 1).forEach(id => candidatos.push([atual, id]));
  const i = ordem.indexOf(atual);
  for (let n = 1; n < ordem.length; n++) {
    const outro = ordem[(i + n) % ordem.length];
    idsDoLote(lotes[outro]).forEach(id => candidatos.push([outro, id]));
  }
  ids.slice(0, Math.max(pos, 0)).forEach(id => candidatos.push([atual, id]));
  const achado = candidatos.find(([lote, id]) => lotes[lote].decisoes[id] === 'p');
  return achado ? { loteId: achado[0], itemId: achado[1] } : null;
}

export function invalidarFila() {
  store.setState(s => ({ fila: { ...s.fila, carregada: false } }));
}

export function totaisDaFila(s = store.getState()) {
  const lotes = lotesSincronizados(s);
  const totais = { total: 0, aprovados: 0, descartados: 0, pendentes: 0 };
  s.fila.ordem.forEach(id => {
    idsDoLote(lotes[id]).forEach(item => {
      const d = lotes[id].decisoes[item] || 'p';
      totais.total += 1;
      if (d === 'a') totais.aprovados += 1;
      else if (d === 'd') totais.descartados += 1;
      else totais.pendentes += 1;
    });
  });
  return totais;
}

// Um pacote por lote, no formato que /api/curadoria/exportar e /baixar-varios esperam.
export function pacotesDosLotes() {
  const s = store.getState();
  const lotes = lotesSincronizados(s);
  const agora = new Date().toISOString();
  return s.fila.ordem.map(id => ({
    lote_id: id,
    resultado: lotes[id].resultado,
    origem_comunidade: lotes[id].origem,
    periodo_referencia: lotes[id].periodo,
    aprovado_em: agora,
    decisoes: lotes[id].decisoes,
    textos: lotes[id].textosEditados,
    autorizado: lotes[id].autorizado,
  }));
}
