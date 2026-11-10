// web/js/atoms/kicker.js
// Átomo: Separador editorial com dot indicador (< 35 linhas)
import { esc } from './escape.js';

export function renderKicker(step = '01', title = 'TELEMETRIA', dotColor = 'var(--accent-lime)') {
  return `
    <div class="cl-kicker" style="display:inline-flex; align-items:center; gap:8px; font-family:var(--font-mono); font-size:11px; font-weight:600; text-transform:uppercase; letter-spacing:0.08em; color:var(--muted); margin-bottom:8px;">
      <span style="display:inline-block; width:6px; height:6px; border-radius:50%; background:${dotColor}; box-shadow: 0 0 6px ${dotColor};"></span>
      <span>${esc(step)} · ${esc(title)}</span>
    </div>
  `.trim();
}
