// web/js/views/insights-view.js
// Tela 4: Histórico & Séries Temporais (< 115 linhas)
import { renderKicker } from '../atoms/kicker.js';
import { renderBadge } from '../atoms/badge.js';
import { esc } from '../atoms/escape.js';
import { store } from '../store.js';
import {
  renderInsightsKpis,
  renderTopicosChart,
  renderRotasDonut,
  renderAproveitamentoBox,
} from '../organisms/insights-charts.js';

export function renderInsightsView() {
  const { insightsData, insightsCarregando, insightsModoDemo } = store.getState();

  return `
    <div class="view-insights">
      <div class="page-header" style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:12px;">
        <div>
          ${renderKicker('04', 'HISTÓRICO & SÉRIES TEMPORAIS')}
          <h1 class="page-title">Insights da comunidade</h1>
          <p class="page-subtitle">Acompanhamento longitudinal de sentimento, rotas e tópicos da comunidade.</p>
        </div>
        <div style="display:flex; align-items:center; gap:8px;">
          ${insightsData ? `
            ${insightsData.banco_configurado && !insightsModoDemo
              ? renderBadge('Supabase Ativo', 'success')
              : renderBadge('Demonstração', 'warning')
            }
            <button id="btn-insights-refresh" style="padding:6px 12px; border-radius:var(--radius-md); font-size:13px; font-weight:500; background:var(--bg-surface-2); border:1px solid var(--line); color:var(--text);">
              🔄 Atualizar
            </button>
          ` : ''}
        </div>
      </div>

      ${insightsCarregando ? `
        <div class="card" style="padding:48px; text-align:center; color:var(--muted);">
          <p style="font-size:15px;">Carregando métricas e histórico da comunidade...</p>
        </div>
      ` : !insightsData ? `
        <div class="card" style="padding:32px; border-left:3px solid var(--accent-cyan); margin-bottom:1.5rem;">
          <h3 class="card-title">Base de dados histórica</h3>
          <p style="color:var(--muted); font-size:14px; line-height:1.5; margin-bottom:14px;">
            O histórico completo conecta-se ao banco Supabase via 
            <code style="background:var(--bg-surface-2); padding:2px 6px; border-radius:4px; font-family:var(--font-mono); color:var(--accent-lime);">DATABASE_URL</code> 
            no arquivo <code>.env</code>.
          </p>
          <div style="display:flex; gap:10px; flex-wrap:wrap;">
            <button id="btn-insights-load-demo" class="btn btn-primary" style="padding:8px 16px; border-radius:var(--radius-md); background:var(--accent-lime); color:var(--accent-lime-ink); font-weight:600; font-size:13px;">
              📊 Carregar Demonstração do Histórico
            </button>
          </div>
        </div>
      ` : `
        ${renderInsightsKpis(insightsData.numeros)}

        <div class="grid-2" style="margin-bottom:1.25rem;">
          <div class="card">
            <h3 class="card-title" style="font-size:15px; margin-bottom:4px;">Tópicos Mais Falados</h3>
            <p class="card-caption">Assuntos com maior volume de discussões no período analisado.</p>
            ${renderTopicosChart(insightsData.topicos)}
          </div>

          <div class="card">
            <h3 class="card-title" style="font-size:15px; margin-bottom:4px;">Rotas de Distribuição</h3>
            <p class="card-caption">Destino editorial atribuído pela IA para cada interação.</p>
            ${renderRotasDonut(insightsData.rotas)}
          </div>
        </div>

        <div class="card" style="margin-bottom:1.25rem;">
          <h3 class="card-title" style="font-size:15px; margin-bottom:4px;">Aproveitamento Editorial dos Conteúdos</h3>
          <p class="card-caption">Decisões tomadas na curadoria sobre os rascunhos gerados pela IA.</p>
          ${renderAproveitamentoBox(insightsData.aproveitamento)}
        </div>
      `}
    </div>
  `.trim();
}
