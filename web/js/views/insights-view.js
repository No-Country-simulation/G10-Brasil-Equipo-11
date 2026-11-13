// web/js/views/insights-view.js
// Tela 4: Insights da comunidade. Filtros numa linha só, acima de tudo; todos os gráficos
// respondem ao mesmo recorte. Os dados vêm do Oracle (ou da demonstração, sem banco).
import { renderKicker } from '../atoms/kicker.js';
import { renderBadge } from '../atoms/badge.js';
import { esc } from '../atoms/escape.js';
import { store } from '../store.js';
import {
  renderResumo,
  renderSentimentoTempo,
  renderCanais,
  renderTopicos,
  renderAtividade,
  renderRotas,
  renderAproveitamento,
  renderAlertas,
  renderMembros,
} from '../organisms/insights-charts.js';

export const PRESETS = [
  { id: '7', nome: '7 dias', dias: 7 },
  { id: '30', nome: '30 dias', dias: 30 },
  { id: '90', nome: '90 dias', dias: 90 },
  { id: 'tudo', nome: 'Tudo', dias: null },
];

function renderFiltros(filtros, opcoes, modoDemo) {
  const opt = (valor, nome, atual) => `<option value="${esc(valor)}" ${valor === atual ? 'selected' : ''}>${esc(nome)}</option>`;
  return `
    <form class="ins-filtros" id="ins-filtros" onsubmit="return false" aria-label="Filtros do período">
      <div class="ins-filtro">
        <span>Período</span>
        <div class="ins-presets" role="group" aria-label="Período rápido">
          ${PRESETS.map(p => `<button type="button" class="ins-preset" data-preset="${p.id}" aria-pressed="${filtros.preset === p.id}">${p.nome}</button>`).join('')}
        </div>
      </div>
      <label class="ins-filtro"><span>De</span><input type="date" id="ins-inicio" value="${esc(filtros.inicio || '')}"></label>
      <label class="ins-filtro"><span>Até</span><input type="date" id="ins-fim" value="${esc(filtros.fim || '')}"></label>
      <label class="ins-filtro"><span>Comunidade</span>
        <select id="ins-comunidade" ${modoDemo ? 'disabled' : ''}>
          ${opt('', 'Todas', filtros.comunidade || '')}
          ${(opcoes.comunidades || []).map(c => opt(c, c, filtros.comunidade)).join('')}
        </select>
      </label>
      <label class="ins-filtro"><span>Canal</span>
        <select id="ins-canal">
          ${opt('', 'Todos', filtros.canal || '')}
          ${(opcoes.canais || []).map(c => opt(c, c, filtros.canal)).join('')}
        </select>
      </label>
    </form>`;
}

export function renderInsightsView() {
  const { insightsData: dados, insightsCarregando, insightsModoDemo, insightsErro, insightsFiltros } = store.getState();
  const filtros = insightsFiltros || {};

  const cabecalho = `
    <div class="page-header" style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:12px;">
      <div>
        ${renderKicker('04', 'HISTÓRICO & SÉRIES TEMPORAIS')}
        <h1 class="page-title">Insights da comunidade</h1>
        <p class="page-subtitle">Clima, temas, pontos de atrito e o que vira conteúdo, a partir de tudo o que já foi processado.</p>
      </div>
      <div style="display:flex; align-items:center; gap:8px;">
        ${dados ? (insightsModoDemo
          ? renderBadge('Demonstração', 'warning')
          : renderBadge('Oracle', 'success')) : ''}
      </div>
    </div>`;

  if (insightsErro && !dados) {
    return `<div class="view-insights">${cabecalho}
      <div class="card" role="alert" style="border-left:3px solid var(--accent-coral);">
        <h3 class="card-title">Não foi possível carregar os Insights</h3>
        <p class="card-caption">${esc(insightsErro)}</p>
        <button id="btn-insights-refresh" class="cl-btn" style="padding:8px 14px; border-radius:var(--radius-md); border:1px solid var(--line); background:var(--bg-surface-2); color:var(--text);">Tentar de novo</button>
      </div></div>`;
  }

  if (!dados) {
    return `<div class="view-insights">${cabecalho}
      <div class="card" style="padding:48px; text-align:center; color:var(--muted);">
        ${insightsCarregando ? 'Carregando o histórico da comunidade…' : 'Abrindo os Insights…'}
      </div></div>`;
  }

  if (dados.banco_configurado === false) {
    return `<div class="view-insights">${cabecalho}
      <div class="card" style="border-left:3px solid var(--accent-cyan);">
        <h3 class="card-title">Sem banco de histórico</h3>
        <p class="card-caption">${esc(dados.mensagem || 'Configure o Oracle para ver o histórico.')}</p>
        <button id="btn-insights-load-demo" class="cl-btn" style="padding:8px 16px; border-radius:var(--radius-md); background:var(--accent-lime); color:var(--accent-lime-ink); font-weight:600; font-size:13px; border:0;">
          Ver com dados de demonstração
        </button>
      </div></div>`;
  }

  const periodo = dados.periodo && dados.periodo.inicio
    ? `${dados.periodo.inicio.split('-').reverse().join('/')} a ${dados.periodo.fim.split('-').reverse().join('/')}`
    : '';

  return `
    <div class="view-insights">
      ${cabecalho}
      ${renderFiltros(filtros, dados.opcoes || {}, insightsModoDemo)}
      <div class="ins-wrap ${insightsCarregando ? 'is-loading' : ''}" aria-busy="${insightsCarregando ? 'true' : 'false'}">
        ${insightsErro ? `<p role="alert" class="ins-kpi-nota" style="margin-bottom:12px; color:var(--text);">⚠ ${esc(insightsErro)} Mostrando o último resultado carregado.</p>` : ''}
        ${periodo ? `<p class="ins-kpi-nota" style="margin:-4px 0 12px;">Mensagens escritas de ${esc(periodo)}.</p>` : ''}
        ${!dados.resumo || !dados.resumo.interacoes ? `
          <div class="card" style="padding:32px; text-align:center; color:var(--muted);">
            Nenhuma mensagem processada neste recorte. Amplie o período.
          </div>` : `
          ${renderResumo(dados.resumo)}
          ${renderSentimentoTempo(dados.sentimento_no_tempo)}
          <div class="grid-2" style="gap:1.25rem;">
            <div>${renderCanais(dados.canais_sentimento)}</div>
            <div>${renderTopicos(dados.topicos_tom)}</div>
          </div>
          ${renderAlertas(dados.alertas_triagem)}
          <div class="grid-2" style="gap:1.25rem;">
            <div>${renderRotas(dados.rotas)}</div>
            <div>${renderAproveitamento(dados.aproveitamento_por_tipo)}</div>
          </div>
          ${renderAtividade(dados.atividade_canal_tempo)}
          ${renderMembros(dados.membros)}
        `}
      </div>
    </div>`.trim();
}
