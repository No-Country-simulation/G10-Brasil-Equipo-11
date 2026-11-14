// web/js/organisms/curation-queue.js
// Organismo: Fila vertical de curadoria com contadores, progresso e exportação (< 90 linhas)
import { renderProgressBar } from '../molecules/progress-bar.js';
import { renderQueueItem } from '../molecules/queue-item.js';
import { renderButton } from '../atoms/button.js';
import { esc } from '../atoms/escape.js';
import { store } from '../store.js';
import { chaveEmFoco, lotesSincronizados, totaisDaFila } from '../fila.js';
import { extrairItensCuradoria } from '../views/curation-view.js';
import { periodoCurto } from './pending-batches.js';

function renderExportStatus(exportResult, exportErro) {
  if (exportErro) {
    return `
      <div role="alert" style="margin-top:8px; font-size:12px; line-height:1.45; color:var(--text); border:1px solid var(--accent-coral); background:var(--accent-coral-bg); border-radius:var(--radius-md); padding:8px 10px;">
        <strong>✕ Não exportado.</strong> ${esc(exportErro)}
      </div>`;
  }
  const lotes = exportResult?.lotes;
  if (!lotes || !lotes.length) return '';
  const novos = lotes.filter(l => l.ok && !l.ja_exportado).length;
  const repetidos = lotes.filter(l => l.ok && l.ja_exportado).length;
  const falhas = lotes.filter(l => !l.ok);
  const cor = falhas.length ? 'var(--accent-coral)' : 'var(--accent-lime-text)';
  const fundo = falhas.length ? 'var(--accent-coral-bg)' : 'var(--accent-lime-bg)';
  return `
    <div role="${falhas.length ? 'alert' : 'status'}" style="margin-top:8px; font-size:12px; line-height:1.45; color:var(--text); border:1px solid ${cor}; background:${fundo}; border-radius:var(--radius-md); padding:8px 10px;">
      <strong>${novos} ${novos === 1 ? 'lote exportado' : 'lotes exportados'} · ${repetidos} já ${repetidos === 1 ? 'exportado' : 'exportados'} · ${falhas.length} ${falhas.length === 1 ? 'falha' : 'falhas'}</strong>
      ${falhas.map(f => `<div style="margin-top:4px;">✕ ${esc(f.rotulo)}: ${esc(f.erro || 'falha ao exportar')}</div>`).join('')}
      ${novos ? '<div style="margin-top:4px;">Guardado no servidor. Para ter o arquivo no computador, use <strong>Baixar</strong>.</div>' : ''}
    </div>`;
}

// Botões de download: o arquivo vai para a pasta de downloads do navegador de quem está usando.
function renderBaixar(aprovados, baixando) {
  const formatos = [['pdf', 'PDF'], ['csv', 'CSV'], ['json', 'JSON']];
  const desligado = aprovados === 0 || Boolean(baixando);
  return `
    <div style="margin-top:10px;">
      <div style="font-size:11px; color:var(--muted); text-transform:uppercase; margin-bottom:6px;">Baixar aprovados</div>
      <div style="display:flex; gap:6px;">
        ${formatos.map(([formato, rotulo]) => `
          <button class="cl-btn cl-btn-secondary btn-baixar-aprovados" data-formato="${formato}" ${desligado ? 'disabled' : ''}
            title="Baixar os conteúdos aprovados em ${rotulo}"
            style="flex:1; padding:8px 6px; border-radius:var(--radius-md); font-size:13px; font-weight:600;
              background:var(--bg-surface-2); color:var(--text); border:1px solid var(--line);
              cursor:${desligado ? 'not-allowed' : 'pointer'}; opacity:${desligado ? '0.45' : '1'};">
            ${baixando === formato ? 'Gerando…' : `↓ ${rotulo}`}
          </button>`).join('')}
      </div>
      ${aprovados === 0 ? '<div style="font-size:11px; color:var(--dim); margin-top:6px;">Aprove ao menos um conteúdo para baixar.</div>' : ''}
    </div>`;
}

function dataHoraCurta(iso) {
  const d = iso ? new Date(iso) : null;
  return d && !Number.isNaN(d.getTime())
    ? d.toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }).replace(',', '')
    : '';
}

function renderGrupo(loteId, estado, s) {
  const itens = extrairItensCuradoria(estado.resultado);
  const pendentes = itens.filter(it => (estado.decisoes[it.id] || 'p') === 'p').length;
  const quando = dataHoraCurta(estado.processadoEm);
  return `
    <div class="cl-fila-grupo">
      <div class="cl-fila-grupo-titulo">
        <span class="cl-fila-grupo-nome">${esc((estado.origem || '').replace(/_/g, ' '))} · ${esc(periodoCurto(estado.periodo))}</span>
        <span class="cl-fila-grupo-meta">${quando ? `${esc(quando)} · ` : ''}${pendentes} ${pendentes === 1 ? 'pendente' : 'pendentes'}</span>
      </div>
      ${itens.map(it => renderQueueItem(
        it.id, it.title, estado.decisoes[it.id] || 'p', loteId === chaveEmFoco(s) && it.id === s.activeItem, loteId,
      )).join('')}
    </div>`;
}

export function renderCurationQueue() {
  const s = store.getState();
  const { exportResult, exportErro, isExporting, baixando } = s;
  const lotes = lotesSincronizados(s);
  const { total, aprovados, descartados, pendentes } = totaisDaFila(s);
  const revisados = aprovados + descartados;

  return `
    <div class="card cl-queue-container" style="display:flex; flex-direction:column; gap:12px;">
      ${renderProgressBar(revisados, total)}

      <div class="grid-3" style="text-align:center; padding:8px 0; border-top:1px solid var(--line); border-bottom:1px solid var(--line); margin-bottom:4px;">
        <div>
          <div style="font-size:11px; color:var(--muted); text-transform:uppercase;">Aprovados</div>
          <div class="tabular-nums" style="font-size:18px; font-weight:700; color:var(--accent-lime-text);">${aprovados}</div>
        </div>
        <div>
          <div style="font-size:11px; color:var(--muted); text-transform:uppercase;">Descartados</div>
          <div class="tabular-nums" style="font-size:18px; font-weight:700; color:var(--dim);">${descartados}</div>
        </div>
        <div>
          <div style="font-size:11px; color:var(--muted); text-transform:uppercase;">Pendentes</div>
          <div class="tabular-nums" style="font-size:18px; font-weight:700; color:var(--accent-amber);">${pendentes}</div>
        </div>
      </div>

      <div class="cl-queue-list">
        ${s.fila.ordem.map(id => renderGrupo(id, lotes[id], s)).join('')}
      </div>

      <div style="margin-top:auto; padding-top:10px; border-top:1px solid var(--line);">
        ${renderButton({
          id: 'btn-exportar-aprovados',
          text: isExporting ? 'Exportando…' : 'Exportar aprovados',
          variant: 'primary',
          disabled: aprovados === 0 || isExporting,
          fullWidth: true,
        })}
        ${renderExportStatus(exportResult, exportErro)}
        ${renderBaixar(aprovados, baixando)}
      </div>
    </div>
  `.trim();
}
