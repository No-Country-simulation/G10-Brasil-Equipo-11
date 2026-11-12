// web/js/organisms/curation-queue.js
// Organismo: Fila vertical de curadoria com contadores, progresso e exportação (< 90 linhas)
import { renderProgressBar } from '../molecules/progress-bar.js';
import { renderQueueItem } from '../molecules/queue-item.js';
import { renderButton } from '../atoms/button.js';
import { esc } from '../atoms/escape.js';
import { store } from '../store.js';

function dataHora(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  return Number.isNaN(d.getTime())
    ? ''
    : d.toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
}

function renderExportStatus(exportResult, exportErro) {
  if (exportErro) {
    return `
      <div role="alert" style="margin-top:8px; font-size:12px; line-height:1.45; color:var(--text); border:1px solid var(--accent-coral); background:var(--accent-coral-bg); border-radius:var(--radius-md); padding:8px 10px;">
        <strong>✕ Não exportado.</strong> ${esc(exportErro)}
      </div>`;
  }
  if (!exportResult) return '';
  const caminho = `<code style="word-break:break-all;">${esc(exportResult.caminho || '')}</code>`;
  if (exportResult.ja_exportado) {
    const quando = dataHora(exportResult.exportado_em);
    return `
      <div role="status" style="margin-top:8px; font-size:12px; line-height:1.45; color:var(--text); border:1px solid var(--accent-amber); background:var(--accent-amber-bg); border-radius:var(--radius-md); padding:8px 10px;">
        <strong>ⓘ Já exportado${quando ? ` em ${esc(quando)}` : ''}.</strong>
        Os aprovados não mudaram desde então, então nada foi enviado de novo.<br>${caminho}
      </div>`;
  }
  return `
    <div role="status" style="margin-top:8px; font-size:12px; line-height:1.45; color:var(--text); border:1px solid var(--accent-lime); background:var(--accent-lime-bg); border-radius:var(--radius-md); padding:8px 10px;">
      <strong>✓ Exportado.</strong> ${caminho}
    </div>`;
}

export function renderCurationQueue(items = []) {
  const { decisoes, activeItem, exportResult, exportErro, isExporting } = store.getState();
  const valores = Object.values(decisoes);
  const total = items.length;
  const aprovados = valores.filter(v => v === 'a').length;
  const descartados = valores.filter(v => v === 'd').length;
  const revisados = aprovados + descartados;
  const pendentes = total - revisados;

  return `
    <div class="card cl-queue-container" style="display:flex; flex-direction:column; gap:12px;">
      ${renderProgressBar(revisados, total)}

      <div class="grid-3" style="text-align:center; padding:8px 0; border-top:1px solid var(--line); border-bottom:1px solid var(--line); margin-bottom:4px;">
        <div>
          <div style="font-size:11px; color:var(--muted); text-transform:uppercase;">Aprovados</div>
          <div class="tabular-nums" style="font-size:18px; font-weight:700; color:var(--accent-lime);">${aprovados}</div>
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

      <div class="cl-queue-list" style="max-height:380px; overflow-y:auto; padding-right:4px;">
        ${items.map(it => {
          const status = decisoes[it.id] || 'p';
          const isActive = it.id === activeItem;
          return renderQueueItem(it.id, it.title, status, isActive);
        }).join('')}
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
      </div>
    </div>
  `.trim();
}
