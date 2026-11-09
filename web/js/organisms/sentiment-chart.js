// web/js/organisms/sentiment-chart.js
// Organismo: Gráfico de distribuição de sentimentos em SVG/CSS puro (< 80 linhas)
import { esc } from '../atoms/escape.js';

export function renderSentimentChart(contagem = {}) {
  const sentimentos = [
    { label: 'Altamente Positivo', key: 'Altamente Positivo', color: 'var(--dado-cyan)' },
    { label: 'Positivo', key: 'Positivo', color: 'var(--dado-positivo)' },
    { label: 'Neutro', key: 'Neutro', color: 'var(--dado-neutro)' },
    { label: 'Negativo', key: 'Negativo', color: 'var(--dado-laranja)' },
    { label: 'Altamente Negativo', key: 'Altamente Negativo', color: 'var(--dado-rosa)' },
  ];

  const total = Object.values(contagem).reduce((a, b) => a + b, 0) || 1;

  const barSegments = sentimentos
    .map(s => {
      const count = contagem[s.key] || 0;
      if (count === 0) return '';
      const percent = (count / total) * 100;
      return `<div style="flex:${count}; background:${s.color}; height:100%;" title="${s.label}: ${count} (${Math.round(percent)}%)"></div>`;
    })
    .join('');

  const legend = sentimentos
    .map(s => {
      const count = contagem[s.key] || 0;
      return `
        <div style="display:flex; align-items:center; gap:8px; font-size:13px;">
          <span style="display:inline-block; width:10px; height:10px; border-radius:2px; background:${s.color}; flex:none;"></span>
          <span style="color:var(--text);">${esc(s.label)}</span>
          <strong class="tabular-nums" style="margin-left:auto; color:var(--text);">${count}</strong>
        </div>
      `;
    })
    .join('');

  return `
    <div class="cl-sentiment-card">
      <div style="display:flex; height:24px; border-radius:var(--radius-sm); overflow:hidden; gap:2px; margin-bottom:14px; background:var(--bg-surface-2);">
        ${barSegments || '<div style="flex:1; background:var(--dim); opacity:0.3;"></div>'}
      </div>
      <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(160px, 1fr)); gap:8px 16px;">
        ${legend}
      </div>
    </div>
  `.trim();
}
