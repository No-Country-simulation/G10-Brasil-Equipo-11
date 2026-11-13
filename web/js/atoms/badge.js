// web/js/atoms/badge.js
// Átomo: Selo semântico de status e rotas (< 40 linhas)
import { esc } from './escape.js';

export function renderBadge(text, variant = 'neutral', extraClass = '') {
  const styles = {
    info: 'background: var(--accent-cyan-bg); color: var(--accent-cyan); border: 1px solid var(--accent-cyan);',
    success: 'background: var(--accent-lime-bg); color: var(--accent-lime); border: 1px solid var(--accent-lime);',
    warning: 'background: var(--accent-amber-bg); color: var(--accent-amber); border: 1px solid var(--accent-amber);',
    danger: 'background: var(--accent-coral-bg); color: var(--accent-coral); border: 1px solid var(--accent-coral);',
    neutral: 'background: var(--bg-surface-2); color: var(--muted); border: 1px solid var(--line);',
  };

  const style = styles[variant] || styles.neutral;
  return `
    <span class="cl-badge ${esc(extraClass)}" style="display:inline-flex; align-items:center; gap:6px; padding:3px 10px; border-radius:var(--radius-full); font-size:12px; font-weight:600; line-height:1; ${style}">
      ${esc(text)}
    </span>
  `.trim();
}
