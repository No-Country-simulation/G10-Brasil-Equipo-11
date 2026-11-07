// web/js/molecules/kpi-card.js
// Molécula: Cartão de métrica com números tabulares estáveis (< 55 linhas)
import { esc } from '../atoms/escape.js';

export function renderKpiCard({ label, value, caption, accentColor = 'var(--text)' }) {
  return `
    <div class="card cl-kpi-card" style="display:flex; flex-direction:column; justify-content:space-between;">
      <div style="font-size:13px; font-weight:500; color:var(--muted);">${esc(label)}</div>
      <div class="cl-kpi-val tabular-nums" style="font-size:26px; font-weight:700; color:${accentColor}; margin:8px 0 4px; letter-spacing:-0.02em;">
        ${esc(value)}
      </div>
      <div style="font-size:12px; color:var(--dim);">${esc(caption)}</div>
    </div>
  `.trim();
}
