// web/js/organisms/insights-charts.js
// Componentes gráficos e estatísticos de Insights (< 115 linhas)
import { esc } from '../atoms/escape.js';
import { renderKpiCard } from '../molecules/kpi-card.js';

export function renderInsightsKpis(numeros = {}) {
  const total = numeros.total ?? 0;
  const pos = numeros.pct_positivas !== undefined ? `${numeros.pct_positivas}%` : '0%';
  const neg = numeros.pct_negativas !== undefined ? `${numeros.pct_negativas}%` : '0%';
  const alertas = numeros.alertas ?? 0;

  return `
    <div class="grid-4" style="margin-bottom: 1.5rem;">
      ${renderKpiCard('Interações', total, 'Mensagens no período')}
      ${renderKpiCard('Positivas', pos, 'Sentimento positivo', 'success')}
      ${renderKpiCard('Negativas', neg, 'Sentimento crítico', 'danger')}
      ${renderKpiCard('Alertas', alertas, 'Atenção imediata', alertas > 0 ? 'warning' : 'neutral')}
    </div>
  `.trim();
}

export function renderTopicosChart(topicos = []) {
  if (!topicos.length) {
    return `<p style="color:var(--muted); font-size:13px;">Nenhum tópico identificado no período.</p>`;
  }
  const maxQtd = Math.max(...topicos.map(t => t.quantidade || 0), 1);

  return `
    <div style="display:flex; flex-direction:column; gap:8px;">
      ${topicos.slice(0, 8).map(t => {
        const pct = Math.round(((t.quantidade || 0) / maxQtd) * 100);
        return `
          <div style="font-size:13px;">
            <div style="display:flex; justify-content:space-between; margin-bottom:3px; color:var(--text);">
              <span style="font-weight:500;">${esc(t.topico)}</span>
              <span class="cl-mono" style="color:var(--muted); font-size:12px;">${t.quantidade} msgs</span>
            </div>
            <div style="height:6px; background:var(--bg-surface-2); border-radius:3px; overflow:hidden;">
              <div style="width:${pct}%; height:100%; background:var(--accent-cyan); border-radius:3px; transition:width var(--transition-fast);"></div>
            </div>
          </div>
        `;
      }).join('')}
    </div>
  `.trim();
}

export function renderRotasDonut(rotas = []) {
  if (!rotas.length) {
    return `<p style="color:var(--muted); font-size:13px;">Nenhuma rota gerada no período.</p>`;
  }
  const cores = {
    case_sucesso: 'var(--accent-lime)',
    faq: 'var(--accent-cyan)',
    alerta: 'var(--accent-coral)',
    nenhuma: 'var(--muted)',
  };

  const total = rotas.reduce((acc, r) => acc + (r.quantidade || 0), 0) || 1;

  return `
    <div style="display:flex; flex-direction:column; gap:10px;">
      <div style="display:flex; height:12px; border-radius:6px; overflow:hidden; background:var(--bg-surface-2); margin-bottom:6px;">
        ${rotas.map(r => {
          const w = ((r.quantidade || 0) / total) * 100;
          if (w === 0) return '';
          return `<div style="width:${w}%; background:${cores[r.rota] || 'var(--dim)'};" title="${esc(r.nome)}: ${r.quantidade}"></div>`;
        }).join('')}
      </div>
      <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px; font-size:12px;">
        ${rotas.map(r => {
          const pct = Math.round(((r.quantidade || 0) / total) * 100);
          return `
            <div style="display:flex; align-items:center; gap:6px; color:var(--text);">
              <span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:${cores[r.rota] || 'var(--dim)'};"></span>
              <span style="flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${esc(r.nome)}</span>
              <strong class="cl-mono" style="color:var(--muted);">${r.quantidade} (${pct}%)</strong>
            </div>
          `;
        }).join('')}
      </div>
    </div>
  `.trim();
}

export function renderAproveitamentoBox(aproveitamento = {}) {
  const { gerados = 0, aprovados = 0, descartados = 0, pendentes = 0 } = aproveitamento;
  return `
    <div style="display:grid; grid-template-columns:repeat(3, 1fr); gap:10px; text-align:center;">
      <div style="background:var(--bg-surface-2); border:1px solid var(--line); border-radius:var(--radius-md); padding:10px;">
        <span style="font-size:11px; text-transform:uppercase; color:var(--accent-lime); font-weight:600;">Aprovados</span>
        <div class="cl-mono" style="font-size:1.4rem; font-weight:700; color:var(--text); margin-top:2px;">${aprovados}</div>
      </div>
      <div style="background:var(--bg-surface-2); border:1px solid var(--line); border-radius:var(--radius-md); padding:10px;">
        <span style="font-size:11px; text-transform:uppercase; color:var(--muted); font-weight:600;">Pendentes</span>
        <div class="cl-mono" style="font-size:1.4rem; font-weight:700; color:var(--text); margin-top:2px;">${pendentes}</div>
      </div>
      <div style="background:var(--bg-surface-2); border:1px solid var(--line); border-radius:var(--radius-md); padding:10px;">
        <span style="font-size:11px; text-transform:uppercase; color:var(--accent-coral); font-weight:600;">Descartados</span>
        <div class="cl-mono" style="font-size:1.4rem; font-weight:700; color:var(--text); margin-top:2px;">${descartados}</div>
      </div>
    </div>
    <div style="margin-top:10px; font-size:12px; color:var(--dim); text-align:center;">
      Total de conteúdos gerados pela IA no período: <strong class="cl-mono" style="color:var(--text);">${gerados}</strong>
    </div>
  `.trim();
}
