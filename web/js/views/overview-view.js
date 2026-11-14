// web/js/views/overview-view.js
// Tela 1: Visão geral — pendências de todos os lotes (Oracle) e os últimos 7 dias
import { esc } from '../atoms/escape.js';
import { renderKicker } from '../atoms/kicker.js';
import { renderButton } from '../atoms/button.js';
import { renderKpiCard } from '../molecules/kpi-card.js';
import { renderAlertCard } from '../molecules/alert-card.js';
import { renderSentimentChart } from '../organisms/sentiment-chart.js';
import { renderRoutesChart } from '../organisms/routes-chart.js';
import { renderTelemetryTable } from '../organisms/telemetry-table.js';
import { renderPendingBatches, periodoCurto } from '../organisms/pending-batches.js';
import { store } from '../store.js';

function contar(lista, campo, padrao) {
  return lista.reduce((acc, item) => {
    const chave = item[campo] || padrao;
    acc[chave] = (acc[chave] || 0) + 1;
    return acc;
  }, {});
}

function cartaoAviso(titulo, texto, botao = '') {
  return `
    <div class="card" style="padding:48px; text-align:center; max-width:600px; margin:40px auto;">
      <h2 style="margin-bottom:8px;">${esc(titulo)}</h2>
      <p style="color:var(--muted); margin-bottom:20px;">${esc(texto)}</p>
      ${botao}
    </div>
  `;
}

const botaoAtualizar = (carregando) =>
  renderButton({ id: 'btn-atualizar-visao', text: carregando ? 'Atualizando…' : 'Atualizar', variant: 'secondary', disabled: carregando });

export function renderOverviewView() {
  const { visaoGeral } = store.getState();
  const { dados, carregando, erro } = visaoGeral;

  if (!dados && carregando) return cartaoAviso('Carregando a Visão geral…', 'Buscando as pendências no banco.');
  if (!dados && erro) return cartaoAviso('Não foi possível carregar a Visão geral', erro, botaoAtualizar(false));
  if (!dados) return cartaoAviso('Visão geral', 'Ainda não carregada.', botaoAtualizar(false));
  if (dados.oracle_configurado === false) return cartaoAviso('Visão geral indisponível', dados.mensagem || '');

  const lotes = dados.lotes_pendentes || [];
  const alertas = dados.alertas_pendentes || [];
  const interacoes = dados.interacoes || [];

  if (!lotes.length && !interacoes.length) {
    return cartaoAviso('Tudo em dia', 'Nada pendente e nenhuma interação nos últimos 7 dias.',
      renderButton({ id: 'btn-go-importar', text: 'Importar interações', variant: 'primary' }));
  }

  const ativosTotal = lotes.reduce((s, l) => s + l.ativos_pendentes, 0);
  const porTipo = lotes.reduce((acc, l) => {
    Object.entries(l.ativos_por_tipo || {}).forEach(([k, v]) => { acc[k] = (acc[k] || 0) + v; });
    return acc;
  }, {});
  const rotulosTipo = { post: 'post', newsletter: 'newsletter', faq: 'FAQ' };
  const legendaAtivos = Object.entries(porTipo).filter(([, v]) => v > 0)
    .map(([k, v]) => `${v} ${rotulosTipo[k] || k}`).join(' · ') || 'nada pendente';

  const sentimentos = contar(interacoes, 'sentimento', 'Neutro');
  const predominante = Object.entries(sentimentos).sort((a, b) => b[1] - a[1])[0]?.[0];
  const quando = dados.atualizado_em ? new Date(dados.atualizado_em) : null;
  const quandoFmt = quando
    ? `${quando.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })} às ${quando.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}`
    : '';
  const lotesTxt = `${lotes.length} ${lotes.length === 1 ? 'lote' : 'lotes'} com pendências`;
  const tratados = dados.alertas_tratados_janela || 0;

  return `
    <div class="view-visao">
      <div class="page-header" style="display:flex; justify-content:space-between; align-items:flex-end; flex-wrap:wrap; gap:12px;">
        <div>
          ${renderKicker('01', 'TELEMETRIA DA COMUNIDADE')}
          <h1 class="page-title">Saúde da comunidade</h1>
          <p class="page-subtitle">Última atualização: ${esc(quandoFmt)} · ${esc(lotesTxt)}</p>
        </div>
        <div style="display:flex; gap:8px; flex-wrap:wrap;">
          ${botaoAtualizar(carregando)}
          ${ativosTotal > 0 ? renderButton({ id: 'btn-ir-curadoria', text: `Revisar ${ativosTotal} ativos`, variant: 'primary' }) : ''}
        </div>
      </div>

      <div class="grid-3" style="margin-bottom:20px;">
        ${renderKpiCard({ label: 'Interações (7 dias)', value: interacoes.length,
          caption: `de ${new Set(interacoes.map(i => i.autor)).size} pessoas · ${new Set(interacoes.map(i => i.canal)).size} canais` })}
        ${renderKpiCard({ label: 'Ativos para aprovar', value: ativosTotal, caption: legendaAtivos, accentColor: 'var(--accent-lime)' })}
        ${renderKpiCard({ label: 'Membros que precisam de apoio', value: alertas.length,
          caption: `${tratados} já tratados nos últimos 7 dias`, accentColor: 'var(--accent-amber)' })}
      </div>

      ${renderPendingBatches(lotes)}

      <div class="grid-2" style="margin-bottom:20px;">
        <div class="card">
          <h3 class="card-title">Sentimento</h3>
          <p class="card-caption">Últimos 7 dias${predominante ? ` · predominante: ${esc(predominante.toLowerCase())}` : ''}</p>
          ${renderSentimentChart(sentimentos)}
        </div>
        <div class="card">
          <h3 class="card-title">Para onde foi cada mensagem</h3>
          <p class="card-caption">Últimos 7 dias · rota decidida pelo pipeline de IA.</p>
          ${renderRoutesChart(contar(interacoes, 'rota', 'nenhuma'))}
        </div>
      </div>

      ${alertas.length > 0 ? `
        <div class="card" id="bloco-alertas" style="margin-bottom:20px;">
          <h3 class="card-title">Membros que precisam de apoio</h3>
          <p class="card-caption">Não viram conteúdo. Vão para o time de comunidade decidir o contato.</p>
          <div class="grid-2">
            ${alertas.map(a => renderAlertCard(a.ordem, a, null, {
              loteId: a.lote_id,
              rotulo: `${(a.origem || '').replace(/_/g, ' ')} · ${periodoCurto(a.periodo)}`,
            })).join('')}
          </div>
        </div>
      ` : ''}

      ${renderTelemetryTable(interacoes, 'Interações dos últimos 7 dias')}
    </div>
  `.trim();
}
