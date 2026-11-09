// web/js/atoms/theme-toggle.js
// Átomo: Alternador de tema Dark / Light com persistência (< 45 linhas)
import { store } from '../store.js';

export function renderThemeToggle() {
  const currentTheme = store.getState().theme;
  const isDark = currentTheme === 'dark';
  const icon = isDark ? '☀' : '☾';
  const label = isDark ? 'Mudar para tema Claro' : 'Mudar para tema Escuro';

  return `
    <button id="btn-theme-toggle" class="cl-theme-toggle" title="${label}" aria-label="${label}" style="
      display: inline-flex; align-items: center; justify-content: center; width: 38px; height: 38px;
      border-radius: var(--radius-md); background: var(--bg-surface-2); border: 1px solid var(--line);
      color: var(--text); font-size: 16px; cursor: pointer; transition: transform var(--transition-fast), background-color var(--transition-fast);
    ">
      ${icon}
    </button>
  `.trim();
}

export function initThemeToggle() {
  document.addEventListener('click', (e) => {
    const btn = e.target.closest('#btn-theme-toggle');
    if (!btn) return;
    const currentTheme = store.getState().theme;
    const nextTheme = currentTheme === 'dark' ? 'light' : 'dark';
    store.setState({ theme: nextTheme });
  });
}
