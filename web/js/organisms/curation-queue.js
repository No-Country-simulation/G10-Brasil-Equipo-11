// web/js/organisms/curation-queue.js
// Organismo: Fila vertical de curadoria com contadores, progresso e exportação (< 90 linhas)
import { renderProgressBar } from '../molecules/progress-bar.js';
import { renderQueueItem } from '../molecules/queue-item.js';
import { renderButton } from '../atoms/button.js';
import { store } from '../store.js';

export function renderCurationQueue(items = []) {
  const { decisoes, activeItem, exportResult } = store.getState();
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
          text: 'Exportar aprovados',
          variant: 'primary',
          disabled: aprovados === 0,
          fullWidth: true,
        })}
        ${exportResult ? `
          <div style="margin-top:8px; font-size:12px; color:var(--accent-lime); text-align:center;">
            ✓ Salvo em <code>${exportResult.caminho}</code>
          </div>
        ` : ''}
      </div>
    </div>
  `.trim();
}
