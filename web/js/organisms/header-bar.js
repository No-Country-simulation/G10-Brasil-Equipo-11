// web/js/organisms/header-bar.js
// Organismo: Barra de navegação superior com logo, abas, badge amigável e tema (< 85 linhas)
import { esc } from '../atoms/escape.js';
import { renderBadge } from '../atoms/badge.js';
import { renderThemeToggle } from '../atoms/theme-toggle.js';
import { store } from '../store.js';

export function renderHeaderBar() {
  const { activeTab, resultado, origem, periodo, decisoes, logado } = store.getState();
  const tabs = [
    { id: 'importar', label: 'Importar' },
    { id: 'visao', label: 'Visão geral' },
    { id: 'curadoria', label: 'Curadoria' },
    { id: 'insights', label: 'Insights' },
  ];

  const pendentesCount = Object.values(decisoes).filter(d => d === 'p').length;
  const origemLimpa = (origem || 'Discord_Grupo_ONE_G10').replace(/_/g, ' ');

  return `
    <header class="cl-header" style="border-bottom: 1px solid var(--line); background: var(--bg-surface); position: sticky; top: 0; z-index: 100;">
      <div class="container" style="display:flex; align-items:center; justify-content:space-between; padding-top:0.75rem; padding-bottom:0.75rem;">
        
        <!-- Marca / Logo com Máscara Responsiva Dark/Light -->
        <div style="display:flex; align-items:center; gap:10px;">
          <div role="img" aria-label="Sender AI" style="width:30px; height:30px; background:var(--text); -webkit-mask:url('assets/logo_sender_ai.png') center / contain no-repeat; mask:url('assets/logo_sender_ai.png') center / contain no-repeat;"></div>
          <span style="font-weight:700; font-size:18px; letter-spacing:-0.02em; color:var(--text);">Sender AI</span>
        </div>

        <!-- Navegação Principal -->
        <nav style="display:flex; align-items:center; gap:6px;">
          ${tabs.map(t => {
            const isActive = activeTab === t.id;
            const activeStyle = isActive
              ? 'background: var(--accent-lime-bg); color: var(--accent-lime); font-weight: 600;'
              : 'background: transparent; color: var(--muted); font-weight: 500;';
            return `
              <button class="nav-tab-btn" data-tab="${t.id}" style="
                padding: 7px 14px; border-radius: var(--radius-md); font-size: 14px;
                transition: all var(--transition-fast); border: 1px solid ${isActive ? 'var(--accent-lime)' : 'transparent'};
                ${activeStyle}
              ">
                ${t.label}
              </button>
            `;
          }).join('')}
        </nav>

        <!-- Status e Ações -->
        <div style="display:flex; align-items:center; gap:10px;">
          ${resultado ? `
            <span class="cl-badge cl-origem-badge" style="background:var(--bg-surface-2); color:var(--text); border:1px solid var(--line); font-size:12px; font-weight:500;">
              📡 ${esc(origemLimpa)} · ${esc(periodo)}
            </span>
            ${pendentesCount > 0 ? renderBadge(`${pendentesCount} pendentes`, 'success') : ''}
          ` : ''}
          ${renderBadge('Modo simulado', 'warning')}
          ${renderThemeToggle()}
          ${logado ? `
            <button id="btn-logout" title="Encerrar sessão de admin" style="
              display: inline-flex; align-items: center; gap: 5px;
              padding: 6px 12px; border-radius: var(--radius-md); font-size: 13px; font-weight: 500;
              background: var(--bg-surface-2); color: var(--muted); border: 1px solid var(--line);
              transition: all var(--transition-fast);
            ">
              <span>🚪</span> Sair
            </button>
          ` : ''}
        </div>

      </div>
    </header>
  `.trim();
}

export function initHeaderEvents() {
  document.addEventListener('click', (e) => {
    const btn = e.target.closest('.nav-tab-btn');
    if (!btn) return;
    const tab = btn.dataset.tab;
    if (tab) {
      store.setState({ activeTab: tab });
    }
  });
}
