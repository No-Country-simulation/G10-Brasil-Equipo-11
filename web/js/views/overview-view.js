// web/js/views/overview-view.js
// Tela 2: Visão Geral e Telemetria da Comunidade (< 95 linhas)
import { esc } from '../atoms/escape.js';
import { renderKicker } from '../atoms/kicker.js';
import { renderButton } from '../atoms/button.js';
import { renderKpiCard } from '../molecules/kpi-card.js';
import { renderAlertCard } from '../molecules/alert-card.js';
import { renderSentimentChart } from '../organisms/sentiment-chart.js';
import { renderRoutesChart } from '../organisms/routes-chart.js';
import { renderTelemetryTable } from '../organisms/telemetry-table.js';
import { store } from '../store.js';

export function renderOverviewView() {
  const { resultado, processadoEm, decisoes, alertas } = store.getState();

  if (!resultado) {
    return `
      <div class="card" style="padding:48px; text-align:center; max-width:600px; margin:40px auto;">
        <h2 style="margin-bottom:8px;">Nenhum lote processado ainda</h2>
        <p style="color:var(--muted); margin-bottom:20px;">Comece importando as interações da semana no Console de Ingestão.</p>
        ${renderButton({ id: 'btn-go-importar', text: 'Ir para Importar', variant: 'primary' })}
      </div>
    `;
  }

  const { analises, ativos_distribuicao_gerados, armazenamento_oci, resumo_comunidade } = resultado;
  const pendentesCount = Object.values(decisoes).filter(d => d === 'p').length;
  const autoresUnicos = new Set(analises.map(a => a.autor)).size;
  const canaisUnicos = new Set(analises.map(a => a.canal)).size;

  const alertasItens = analises.map((a, idx) => ({ ordem: idx, analise: a })).filter(x => x.analise.rota === 'alerta');
  const alertasAbertos = alertasItens.filter(x => !alertas[x.ordem]);

  const contagemSentimentos = analises.reduce((acc, a) => {
    acc[a.sentimento] = (acc[a.sentimento] || 0) + 1;
    return acc;
  }, {});

  const contagemRotas = analises.reduce((acc, a) => {
    acc[a.rota] = (acc[a.rota] || 0) + 1;
    return acc;
  }, {});

  const dataFmt = processadoEm ? new Date(processadoEm).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '';

  return `
    <div class="view-visao">
      <div class="page-header" style="display:flex; justify-content:space-between; align-items:flex-end; flex-wrap:wrap; gap:12px;">
        <div>
          ${renderKicker('02', 'TELEMETRIA DA COMUNIDADE')}
          <h1 class="page-title">Saúde da comunidade</h1>
          <p class="page-subtitle">${analises.length} interações processadas ${dataFmt ? `às ${dataFmt}` : ''}</p>
        </div>
        ${pendentesCount > 0 ? renderButton({ id: 'btn-ir-curadoria', text: `Revisar ${pendentesCount} ativos`, variant: 'primary' }) : ''}
      </div>

      <!-- KPIs -->
      <div class="grid-4" style="margin-bottom:20px;">
        ${renderKpiCard({ label: 'Interações processadas', value: analises.length, caption: `de ${autoresUnicos} pessoas · ${canaisUnicos} canais` })}
        ${renderKpiCard({ label: 'Ativos para aprovar', value: pendentesCount, caption: 'Post, Newsletter e FAQs', accentColor: 'var(--accent-lime)' })}
        ${renderKpiCard({ label: 'Membros que precisam de apoio', value: alertasAbertos.length, caption: `${alertasItens.length - alertasAbertos.length} já tratados`, accentColor: 'var(--accent-amber)' })}
        ${renderKpiCard({ label: 'Pacote de distribuição', value: 'Salvo localmente', caption: armazenamento_oci?.caminho_objeto || 'ativos/', accentColor: 'var(--accent-cyan)' })}
      </div>

      <!-- Gráficos -->
      <div class="grid-2" style="margin-bottom:20px;">
        <div class="card">
          <h3 class="card-title">Sentimento</h3>
          <p class="card-caption">Predominante: ${esc(resumo_comunidade?.sentimento_predominante || 'neutro').toLowerCase()}</p>
          ${renderSentimentChart(contagemSentimentos)}
        </div>
        <div class="card">
          <h3 class="card-title">Para onde foi cada mensagem</h3>
          <p class="card-caption">Rota decidida pelo pipeline de IA.</p>
          ${renderRoutesChart(contagemRotas)}
        </div>
      </div>

      <!-- Alertas Humanos -->
      ${alertasItens.length > 0 ? `
        <div class="card" style="margin-bottom:20px;">
          <h3 class="card-title">Membros que precisam de apoio</h3>
          <p class="card-caption">Não viram conteúdo. Vão para o time de comunidade decidir o contato.</p>
          <div class="grid-2">
            ${alertasItens.map(item => renderAlertCard(item.ordem, item.analise, alertas[item.ordem])).join('')}
          </div>
        </div>
      ` : ''}

      <!-- Tabela -->
      ${renderTelemetryTable(analises)}
    </div>
  `.trim();
}
