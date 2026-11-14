// web/js/molecules/queue-item.js
// Molécula: Item da fila de curadoria com indicador visual de status (< 55 linhas)
import { esc } from '../atoms/escape.js';

export function renderQueueItem(id, title, status = 'p', isActive = false, loteId = '') {
  const icons = {
    p: '<span style="color:var(--muted); font-size:14px;">○</span>',
    a: '<span style="color:var(--accent-lime); font-size:14px; font-weight:bold;">✓</span>',
    d: '<span style="color:var(--dim); font-size:14px;">✕</span>',
  };

  const activeStyle = isActive
    ? 'background: var(--accent-lime-bg); border-color: var(--accent-lime); color: var(--accent-lime); font-weight:600;'
    : 'background: var(--bg-surface); border-color: var(--line); color: var(--text);';

  return `
    <button class="cl-queue-item btn-queue-item" data-id="${esc(id)}" data-lote-id="${esc(loteId)}" style="
      width: 100%; display: flex; align-items: center; gap: 10px; padding: 10px 14px;
      border-radius: var(--radius-md); border: 1px solid var(--line); text-align: left;
      font-size: 13.5px; transition: all var(--transition-fast); margin-bottom: 6px; ${activeStyle}
    ">
      <span class="cl-queue-icon" style="flex:none;">${icons[status] || icons.p}</span>
      <span class="cl-queue-text" style="flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">
        ${esc(title)}
      </span>
    </button>
  `.trim();
}
