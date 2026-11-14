// web/js/organisms/sidebar.js
// Organismo: Menu lateral recolhível (gaveta no celular) com marca, seções, modo, tema e sair
import { esc } from '../atoms/escape.js';
import { renderThemeToggle } from '../atoms/theme-toggle.js';
import { store } from '../store.js';
import { carregarVisaoGeral } from '../visao-geral.js';
import { abrirCuradoria, salvarTextosAtivos } from '../fila.js';

const svg = (d) => `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${d}</svg>`;

const ICONES = {
  visao: svg('<rect x="3" y="3" width="7" height="9" rx="1.5"/><rect x="14" y="3" width="7" height="5" rx="1.5"/><rect x="14" y="12" width="7" height="9" rx="1.5"/><rect x="3" y="16" width="7" height="5" rx="1.5"/>'),
  importar: svg('<path d="M12 15V3"/><path d="m7 8 5-5 5 5"/><path d="M4 15v4a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-4"/>'),
  curadoria: svg('<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z"/>'),
  insights: svg('<path d="M3 3v18h18"/><path d="m7 15 4-4 3 3 5-6"/>'),
  recolher: svg('<path d="m15 18-6-6 6-6"/>'),
  expandir: svg('<path d="m9 18 6-6-6-6"/>'),
  menu: svg('<path d="M4 6h16M4 12h16M4 18h16"/>'),
  sair: svg('<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="m16 17 5-5-5-5"/><path d="M21 12H9"/>'),
};

const SECOES = [
  { id: 'visao', label: 'Visão geral' },
  { id: 'importar', label: 'Importar' },
  { id: 'curadoria', label: 'Curadoria' },
  { id: 'insights', label: 'Insights' },
];

function totalPendencias(dados) {
  if (!dados || !dados.lotes_pendentes) return 0;
  return dados.lotes_pendentes.reduce((s, l) => s + l.ativos_pendentes + l.alertas_pendentes, 0);
}

function seloModo(saudeInfo) {
  const modo = saudeInfo?.modo_llm;
  if (modo === 'gemini') return '<span class="cl-sidebar-modo" title="IA real">Claude</span>';
  if (modo === 'mock') return '<span class="cl-sidebar-modo cl-sidebar-modo-mock" title="Modo simulado">Simulado</span>';
  return '';
}

export function renderSidebar() {
  const { activeTab, menuRecolhido, visaoGeral, saudeInfo } = store.getState();
  const pendencias = totalPendencias(visaoGeral.dados);

  return `
    <div class="cl-topbar">
      <button id="btn-abrir-menu" class="cl-icon-btn" aria-label="Abrir menu" title="Abrir menu">${ICONES.menu}</button>
      <span class="cl-topbar-marca">Sender AI</span>
    </div>
    <div class="sidebar-backdrop" aria-hidden="true"></div>
    <aside class="cl-sidebar" aria-label="Menu principal">
      <div class="cl-sidebar-marca">
        <div role="img" aria-label="Sender AI" class="cl-sidebar-logo"></div>
        <span class="cl-sidebar-rotulo cl-sidebar-nome">Sender AI</span>
      </div>

      <nav class="cl-sidebar-nav">
        ${SECOES.map(s => {
          const ativo = activeTab === s.id;
          const selo = s.id === 'visao' && pendencias > 0
            ? `<span class="cl-sidebar-selo" aria-label="${pendencias} pendências">${pendencias}</span>` : '';
          return `
            <button class="nav-tab-btn cl-sidebar-item${ativo ? ' ativo' : ''}" data-tab="${s.id}"
              title="${esc(s.label)}" aria-label="${esc(s.label)}"${ativo ? ' aria-current="page"' : ''}>
              ${ICONES[s.id]}
              <span class="cl-sidebar-rotulo">${esc(s.label)}</span>
              ${selo}
            </button>
          `;
        }).join('')}
      </nav>

      <div class="cl-sidebar-rodape">
        ${seloModo(saudeInfo)}
        <div class="cl-sidebar-acoes">
          ${renderThemeToggle()}
          <button id="btn-logout" class="cl-icon-btn" title="Sair" aria-label="Sair">${ICONES.sair}</button>
        </div>
        <button id="btn-recolher-menu" class="cl-sidebar-item cl-sidebar-recolher"
          title="${menuRecolhido ? 'Expandir menu' : 'Recolher menu'}" aria-label="${menuRecolhido ? 'Expandir menu' : 'Recolher menu'}">
          ${menuRecolhido ? ICONES.expandir : ICONES.recolher}
          <span class="cl-sidebar-rotulo">Recolher</span>
        </button>
      </div>
    </aside>
  `.trim();
}

export function initSidebarEvents() {
  document.addEventListener('click', (e) => {
    const item = e.target.closest('.nav-tab-btn');
    if (item && item.dataset.tab) {
      salvarTextosAtivos(); // sair da Curadoria não pode perder o texto digitado
      store.setState({ activeTab: item.dataset.tab, menuAberto: false });
      if (item.dataset.tab === 'visao') carregarVisaoGeral();
      if (item.dataset.tab === 'curadoria') abrirCuradoria();
      return;
    }
    if (e.target.closest('#btn-recolher-menu')) {
      const recolhido = !store.getState().menuRecolhido;
      try {
        localStorage.setItem('sender_ai_menu_recolhido', recolhido ? '1' : '0');
      } catch {
        // sem localStorage, vale só nesta aba
      }
      store.setState({ menuRecolhido: recolhido });
      return;
    }
    if (e.target.closest('#btn-abrir-menu')) {
      store.setState({ menuAberto: true });
      return;
    }
    if (e.target.closest('.sidebar-backdrop')) store.setState({ menuAberto: false });
  });
}
