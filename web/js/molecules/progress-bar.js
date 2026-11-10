// web/js/molecules/progress-bar.js
// Molécula: Barra de progresso da curadoria com porcentagem (< 45 linhas)
import { esc } from '../atoms/escape.js';

export function renderProgressBar(revisados, total) {
  const percent = total > 0 ? Math.round((revisados / total) * 100) : 0;

  return `
    <div class="cl-progress-wrapper" style="margin-bottom: 12px;">
      <div style="display:flex; justify-content:space-between; align-items:center; font-size:12px; color:var(--muted); margin-bottom:6px;">
        <span>${esc(revisados)} de ${esc(total)} revisados</span>
        <span class="tabular-nums" style="font-weight:600; color:var(--accent-lime);">${percent}%</span>
      </div>
      <div style="height:6px; background:var(--bg-surface-2); border-radius:var(--radius-full); overflow:hidden; border:1px solid var(--line);">
        <div style="height:100%; width:${percent}%; background:var(--accent-lime); transition:width var(--transition-fast);"></div>
      </div>
    </div>
  `.trim();
}
