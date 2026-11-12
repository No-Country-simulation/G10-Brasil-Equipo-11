// web/js/insights-controller.js
// Comportamento da tela Insights: carregar dados, filtros, dica flutuante e tabelas abertas.
import { store } from './store.js';
import { api } from './api.js';
import { abrirLoteSalvo } from './lotes.js';
import { PRESETS } from './views/insights-view.js';

const detalhesAbertos = new Set();
let dicaEl = null;
let alvoDica = null;
let ultimaAba = null;

const iso = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;

export function intervaloDoPreset(id) {
  const preset = PRESETS.find(p => p.id === id);
  const hoje = new Date();
  if (!preset) return null;
  if (preset.dias === null) return { inicio: '2000-01-01', fim: iso(hoje) };
  const inicio = new Date(hoje);
  inicio.setDate(hoje.getDate() - (preset.dias - 1));
  return { inicio: iso(inicio), fim: iso(hoje) };
}

function filtrosIniciais() {
  const modo = store.getState().saudeInfo?.modo_llm === 'gemini' ? 'gemini' : 'mock';
  return { preset: '90', ...intervaloDoPreset('90'), comunidade: '', canal: '', modo };
}

export async function carregarInsights({ demo = false } = {}) {
  const estado = store.getState();
  const filtros = estado.insightsFiltros?.iniciado ? estado.insightsFiltros : { ...filtrosIniciais(), iniciado: true };
  store.setState({ insightsCarregando: true, insightsFiltros: filtros });
  const usarDemo = demo || estado.insightsModoDemo;
  try {
    const pedido = { inicio: filtros.inicio, fim: filtros.fim, canal: filtros.canal };
    if (usarDemo) pedido.demo = true;
    else Object.assign(pedido, { modo: filtros.modo, comunidade: filtros.comunidade });
    const dados = await api.obterInsights(pedido);
    store.setState({
      insightsData: dados,
      insightsCarregando: false,
      insightsErro: null,
      insightsModoDemo: Boolean(usarDemo && dados.modo_demo),
    });
  } catch (err) {
    store.setState({ insightsCarregando: false, insightsErro: err.message || 'Falha ao consultar o histórico.' });
  }
}

function atualizarFiltros(patch) {
  const atual = store.getState().insightsFiltros || filtrosIniciais();
  store.setState({ insightsFiltros: { ...atual, ...patch, iniciado: true } });
  carregarInsights();
}

// ---------------------------------------------------------------------------
// Dica flutuante: uma só, montada com textContent (os rótulos vêm dos dados)
// ---------------------------------------------------------------------------
function garantirDica() {
  if (dicaEl) return dicaEl;
  dicaEl = document.createElement('div');
  dicaEl.className = 'ins-dica';
  dicaEl.setAttribute('role', 'tooltip');
  dicaEl.hidden = true;
  document.body.appendChild(dicaEl);
  return dicaEl;
}

function mostrarDica(alvo, x, y) {
  let dados;
  try { dados = JSON.parse(alvo.dataset.dica); } catch { return; }
  const el = garantirDica();
  el.replaceChildren();
  const titulo = document.createElement('div');
  titulo.className = 'ins-dica-titulo';
  titulo.textContent = dados.t || '';
  el.appendChild(titulo);
  for (const linha of dados.l || []) {
    const row = document.createElement('div');
    row.className = 'ins-dica-linha';
    const chave = document.createElement('i');
    chave.style.background = linha.c;
    const valor = document.createElement('b');
    valor.textContent = linha.v;
    const rotulo = document.createElement('span');
    rotulo.textContent = linha.r;
    row.append(chave, valor, rotulo);
    el.appendChild(row);
  }
  if (dados.e) {
    const extra = document.createElement('div');
    extra.className = 'ins-dica-titulo';
    extra.style.margin = '4px 0 0';
    extra.textContent = dados.e;
    el.appendChild(extra);
  }
  el.hidden = false;
  posicionar(el, x, y);
  alvoDica = alvo;
}

function posicionar(el, x, y) {
  const margem = 12;
  const { width, height } = el.getBoundingClientRect();
  let left = x + margem;
  let top = y + margem;
  if (left + width > window.innerWidth - 8) left = x - width - margem;
  if (top + height > window.innerHeight - 8) top = y - height - margem;
  el.style.left = `${Math.max(8, left)}px`;
  el.style.top = `${Math.max(8, top)}px`;
}

function esconderDica() {
  if (dicaEl) dicaEl.hidden = true;
  alvoDica = null;
}

export function initInsightsEvents() {
  document.addEventListener('pointermove', (e) => {
    const alvo = e.target.closest?.('[data-dica]');
    if (!alvo) { if (alvoDica) esconderDica(); return; }
    if (alvo !== alvoDica) mostrarDica(alvo, e.clientX, e.clientY);
    else posicionar(dicaEl, e.clientX, e.clientY);
  });
  document.addEventListener('pointerleave', esconderDica);
  document.addEventListener('focusin', (e) => {
    const alvo = e.target.closest?.('[data-dica]');
    if (!alvo) return;
    const r = alvo.getBoundingClientRect();
    mostrarDica(alvo, r.left + r.width / 2, r.top);
  });
  document.addEventListener('focusout', (e) => { if (e.target.closest?.('[data-dica]')) esconderDica(); });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') esconderDica(); });
  window.addEventListener('scroll', esconderDica, { passive: true });

  // Tabelas abertas continuam abertas depois de recarregar os dados.
  document.addEventListener('toggle', (e) => {
    const id = e.target?.dataset?.detalhe;
    if (!id) return;
    if (e.target.open) detalhesAbertos.add(id); else detalhesAbertos.delete(id);
  }, true);

  document.addEventListener('click', async (e) => {
    const preset = e.target.closest('.ins-preset');
    if (preset) {
      atualizarFiltros({ preset: preset.dataset.preset, ...intervaloDoPreset(preset.dataset.preset) });
      return;
    }
    if (e.target.closest('#btn-insights-load-demo')) {
      store.setState({ insightsModoDemo: true });
      carregarInsights({ demo: true });
      return;
    }
    if (e.target.closest('#btn-insights-refresh')) {
      carregarInsights();
      return;
    }
    const abrir = e.target.closest('.btn-abrir-lote');
    if (abrir) {
      abrir.disabled = true;
      try {
        await abrirLoteSalvo(abrir.dataset.lote, 'visao');
      } catch (err) {
        abrir.disabled = false;
        store.setState({ insightsErro: `Não foi possível abrir o lote: ${err.message}` });
      }
    }
  });

  document.addEventListener('change', (e) => {
    const id = e.target?.id;
    if (id === 'ins-inicio') atualizarFiltros({ inicio: e.target.value, preset: '' });
    else if (id === 'ins-fim') atualizarFiltros({ fim: e.target.value, preset: '' });
    else if (id === 'ins-comunidade') atualizarFiltros({ comunidade: e.target.value });
    else if (id === 'ins-canal') atualizarFiltros({ canal: e.target.value });
    else if (id === 'ins-modo') atualizarFiltros({ modo: e.target.value });
  });

  // Depois de cada render: reabre as tabelas e, ao entrar na aba, carrega os dados.
  store.subscribe((s) => {
    esconderDica();
    document.querySelectorAll('details[data-detalhe]').forEach(d => {
      if (detalhesAbertos.has(d.dataset.detalhe)) d.open = true;
    });
    const entrouNaAba = s.activeTab === 'insights' && ultimaAba !== 'insights';
    ultimaAba = s.activeTab;
    if (!s.logado || s.activeTab !== 'insights' || s.insightsCarregando) return;
    // Primeira abertura, ou volta para a aba: os números podem ter mudado (novos lotes, curadoria).
    if ((!s.insightsData && !s.insightsErro) || (entrouNaAba && s.insightsData)) carregarInsights();
  });
}
