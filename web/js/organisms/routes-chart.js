// web/js/organisms/routes-chart.js
// Organismo: Distribuição de rotas do pipeline em barras proporcionais (< 75 linhas)
import { esc } from '../atoms/escape.js';

export function renderRoutesChart(contagem = {}) {
  const rotas = [
    { label: 'FAQ', key: 'faq', color: 'var(--dado-cyan)' },
    { label: 'Case de sucesso', key: 'case_sucesso', color: 'var(--dado-lime)' },
    { label: 'Alerta', key: 'alerta', color: 'var(--dado-laranja)' },
    { label: 'Sem ação', key: 'nenhuma', color: 'var(--dado-neutro)' },
  ];

  const total = Object.values(contagem).reduce((a, b) => a + b, 0) || 1;

  const rows = rotas
    .map(r => {
      const count = contagem[r.key] || 0;
      const percent = Math.round((count / total) * 100);
      return `
        <div style="display:grid; grid-template-columns: 130px 1fr 32px; align-items:center; gap:12px; margin-bottom:10px; font-size:13.5px;">
          <span style="color:var(--text);">${esc(r.label)}</span>
          <div style="height:12px; background:var(--bg-surface-2); border-radius:var(--radius-full); overflow:hidden;">
            <div style="height:100%; width:${percent}%; background:${r.color}; border-radius:var(--radius-full);"></div>
          </div>
          <strong class="tabular-nums" style="text-align:right; color:var(--text);">${count}</strong>
        </div>
      `;
    })
    .join('');

  return `
    <div class="cl-routes-chart">
      ${rows}
    </div>
  `.trim();
}
