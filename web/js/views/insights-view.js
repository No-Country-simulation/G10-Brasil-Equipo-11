// web/js/views/insights-view.js
// Tela 4: Insights e Histórico de Séries Temporais (< 70 linhas)
import { renderKicker } from '../atoms/kicker.js';

export function renderInsightsView() {
  return `
    <div class="view-insights">
      <div class="page-header">
        ${renderKicker('04', 'HISTÓRICO & SÉRIES TEMPORAIS')}
        <h1 class="page-title">Insights da comunidade</h1>
        <p class="page-subtitle">Acompanhamento longitudinal de saúde e engajamento da comunidade.</p>
      </div>

      <div class="card" style="padding: 32px; border-left: 3px solid var(--accent-cyan);">
        <h3 style="font-size:16px; font-weight:600; margin-bottom:8px;">Base de dados histórica</h3>
        <p style="color:var(--muted); font-size:14px; line-height:1.5; margin-bottom:12px;">
          O histórico completo requer o banco de dados Supabase configurado via variável 
          <code style="background:var(--bg-surface-2); padding:2px 6px; border-radius:4px; font-family:var(--font-mono); color:var(--accent-lime);">DATABASE_URL</code> 
          no arquivo <code>.env</code>.
        </p>
        <p style="color:var(--dim); font-size:13px;">
          Ao preencher a URL de conexão do PostgreSQL/Supabase, as métricas semanais consolidadas, volume por canal e taxas de resolução de alertas serão visualizadas automaticamente nesta aba.
        </p>
      </div>
    </div>
  `.trim();
}
