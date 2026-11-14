// web/js/demo/app-demo.js
// Demonstração da landing: o menu lateral, a Visão geral e a Curadoria reais, com dados fictícios.
// Tudo o que acontece dentro de #lp-app-demo é tratado aqui e não chega ao app (nem à API).
import { store } from '../store.js';
import { esc } from '../atoms/escape.js';
import { renderSidebar } from '../organisms/sidebar.js';
import { renderOverviewView } from '../views/overview-view.js';
import { renderCurationView, extrairItensCuradoria } from '../views/curation-view.js';
import { focar, proximoPendente, primeiroPendente, salvarTextosAtivos, lotesSincronizados } from '../fila.js';
import { LOTES_DEMO, VISAO_DEMO } from './dados-demo.js';
import { renderizarComEstado, executarComEstado } from './estado-demo.js';

let estado = null;

function estadoInicial() {
  const lotes = {};
  const ordem = [];
  LOTES_DEMO.forEach(lote => {
    const decisoes = {};
    extrairItensCuradoria(lote.resultado).forEach(it => { decisoes[it.id] = 'p'; });
    lotes[lote.lote_id] = {
      resultado: lote.resultado, decisoes, textosEditados: {}, autorizado: false, alertas: {},
      origem: lote.origem, periodo: lote.periodo, processadoEm: lote.processado_em,
    };
    ordem.push(lote.lote_id);
  });
  const base = {
    activeTab: 'visao',
    visaoGeral: { dados: JSON.parse(JSON.stringify(VISAO_DEMO)), carregando: false, erro: null },
    fila: { carregada: true, carregando: false, erro: null, avulso: false, ordem, lotes },
    loteId: null, activeItem: null,
    menuRecolhido: false, menuAberto: false,
    saudeInfo: { modo_llm: 'gemini' },
    filtroRota: 'Todas',
    exportResult: null, exportErro: null, isExporting: false, baixando: null,
  };
  return executarComEstado(base, () => focar(ordem[0], primeiroPendente(lotes[ordem[0]])));
}

function conteudo() {
  return renderizarComEstado(estado, () => {
    const tela = estado.activeTab === 'curadoria' ? renderCurationView() : renderOverviewView();
    return `<div class="app-shell com-sidebar">${renderSidebar()}<main class="container">${tela}</main></div>`;
  });
}

export function renderAppDemo() {
  if (!estado) estado = estadoInicial();
  return `<div id="lp-app-demo" class="lp-app-demo" aria-label="Demonstração do Sender AI com dados fictícios">${conteudo()}</div>`;
}

function redesenhar({ manterRolagem = true } = {}) {
  const raiz = document.getElementById('lp-app-demo');
  if (!raiz) return;
  const rolagem = raiz.querySelector('main')?.scrollTop || 0;
  raiz.innerHTML = conteudo();
  if (manterRolagem) {
    const main = raiz.querySelector('main');
    if (main) main.scrollTop = rolagem;
  }
}

function aviso(msg) {
  const t = document.getElementById('lpToast');
  if (!t) return;
  t.innerHTML = `${esc(msg)} <button type="button" class="lp-toast-entrar btn-ir-login">Entrar</button>`;
  t.classList.add('show');
  clearTimeout(window._lpToastTimer);
  window._lpToastTimer = setTimeout(() => t.classList.remove('show'), 3600);
}

function rodar(fn) {
  estado = executarComEstado(estado, fn);
}

// Visão geral da demo acompanha as decisões tomadas na Curadoria da demo.
function sincronizarVisao() {
  const lotes = renderizarComEstado(estado, () => lotesSincronizados());
  const dados = estado.visaoGeral.dados;
  dados.lotes_pendentes = dados.lotes_pendentes
    .map(l => {
      const f = lotes[l.lote_id];
      if (!f) return l;
      const porTipo = { post: 0, newsletter: 0, faq: 0 };
      Object.entries(f.decisoes).forEach(([id, d]) => {
        if (d !== 'p') return;
        if (id === 'post') porTipo.post += 1;
        else if (id === 'newsletter') porTipo.newsletter += 1;
        else porTipo.faq += 1;
      });
      return { ...l, ativos_por_tipo: porTipo, ativos_pendentes: porTipo.post + porTipo.newsletter + porTipo.faq };
    })
    .filter(l => l.ativos_pendentes > 0 || l.alertas_pendentes > 0);
}

function abrirLoteNaDemo(loteId) {
  const lotes = renderizarComEstado(estado, () => lotesSincronizados());
  const alvo = lotes[loteId] ? loteId : estado.fila.ordem[0];
  rodar(() => focar(alvo, primeiroPendente(lotes[alvo])));
  estado.activeTab = 'curadoria';
}

function decidir(decisao) {
  rodar(() => {
    salvarTextosAtivos();
    const s = store.getState();
    if (!s.activeItem) return;
    store.setState({ decisoes: { ...s.decisoes, [s.activeItem]: decisao } });
    if (decisao !== 'p') {
      const proximo = proximoPendente();
      if (proximo) focar(proximo.loteId, proximo.itemId);
    }
  });
  sincronizarVisao();
}

function tratarAlerta(loteId, ordem) {
  const dados = estado.visaoGeral.dados;
  dados.alertas_pendentes = dados.alertas_pendentes.filter(x => !(x.lote_id === loteId && x.ordem === ordem));
  dados.lotes_pendentes = dados.lotes_pendentes
    .map(l => (l.lote_id === loteId ? { ...l, alertas_pendentes: Math.max(0, l.alertas_pendentes - 1) } : l))
    .filter(l => l.ativos_pendentes > 0 || l.alertas_pendentes > 0);
  dados.alertas_tratados_janela += 1;
}

function aoClicar(e) {
  const alvo = (sel) => e.target.closest(sel);
  const aba = alvo('.nav-tab-btn');
  if (aba) {
    const tab = aba.dataset.tab;
    if (tab === 'visao' || tab === 'curadoria') {
      rodar(() => salvarTextosAtivos());
      estado.activeTab = tab;
      return redesenhar({ manterRolagem: false });
    }
    return aviso(`${tab === 'importar' ? 'Importar' : 'Insights'} fica disponível depois de entrar.`);
  }
  if (alvo('#btn-ir-curadoria')) {
    const lote = estado.visaoGeral.dados.lotes_pendentes.find(l => l.ativos_pendentes > 0);
    abrirLoteNaDemo(lote ? lote.lote_id : null);
    return redesenhar({ manterRolagem: false });
  }
  const revisar = alvo('.btn-revisar-lote');
  if (revisar) {
    if (revisar.dataset.destino === 'alertas') {
      return document.getElementById('bloco-alertas')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
    abrirLoteNaDemo(revisar.dataset.loteId);
    return redesenhar({ manterRolagem: false });
  }
  if (alvo('#btn-ir-visao')) {
    estado.activeTab = 'visao';
    return redesenhar({ manterRolagem: false });
  }
  const btnAlerta = alvo('.btn-tratar-alerta, .btn-resolver-alerta');
  if (btnAlerta) {
    const card = btnAlerta.closest('.cl-alert-card');
    tratarAlerta(card?.dataset.loteId, parseInt(card?.dataset.ordem, 10));
    aviso('Alerta tratado na demonstração. No sistema, isso fica registrado para o time.');
    return redesenhar();
  }
  const filtro = alvo('.btn-filter-route');
  if (filtro) {
    estado.filtroRota = filtro.dataset.filter;
    return redesenhar();
  }
  const item = alvo('.btn-queue-item');
  if (item) {
    rodar(() => {
      salvarTextosAtivos();
      focar(item.dataset.loteId, item.dataset.id);
    });
    return redesenhar();
  }
  if (alvo('#btn-aprovar-ativo')) { decidir('a'); return redesenhar(); }
  if (alvo('#btn-descartar-ativo')) { decidir('d'); return redesenhar(); }
  if (alvo('#btn-desfazer-decisao')) { decidir('p'); return redesenhar(); }
  if (alvo('#btn-exportar-aprovados, .btn-baixar-aprovados')) {
    return aviso('Entre para exportar e baixar os aprovados de verdade.');
  }
  if (alvo('#btn-atualizar-visao, #btn-atualizar-fila')) {
    return aviso('Na demonstração os dados são fixos. No sistema, chegam das suas comunidades.');
  }
  if (alvo('#btn-go-importar')) return aviso('Importar fica disponível depois de entrar.');
  return undefined;
}

function aoDigitar(e) {
  if (e.target.id === 'chk_autorizado') {
    const marcado = e.target.checked;
    rodar(() => {
      salvarTextosAtivos();
      store.setState({ autorizado: marcado });
    });
    redesenhar();
  }
}

export function initAppDemo() {
  if (window.__senderDemoIniciada) return;
  window.__senderDemoIniciada = true;
  // Em captura no document: roda antes dos ouvintes do app e impede que o evento chegue a eles.
  ['click', 'input', 'change'].forEach(tipo => {
    document.addEventListener(tipo, (e) => {
      if (!e.target.closest || !e.target.closest('#lp-app-demo')) return;
      e.stopPropagation();
      if (tipo === 'click') aoClicar(e);
      else if (tipo === 'input') aoDigitar(e);
    }, true);
  });
}
