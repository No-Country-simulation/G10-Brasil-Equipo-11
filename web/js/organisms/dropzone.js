// web/js/organisms/dropzone.js
// Organismo: Dropzone drag-and-drop com suporte a JSON, CSV e Lote de Exemplo (< 90 linhas)
import { esc } from '../atoms/escape.js';
import { renderButton } from '../atoms/button.js';
import { renderBadge } from '../atoms/badge.js';
import { store } from '../store.js';

export function renderDropzone() {
  const { leitura } = store.getState();

  return `
    <div class="cl-dropzone-container" style="display:flex; flex-direction:column; gap:16px;">
      <div id="dropzone-area" style="
        border: 2px dashed var(--line); border-radius: var(--radius-lg); padding: 32px 20px;
        text-align: center; background: var(--bg-surface); cursor: pointer;
        transition: border-color var(--transition-fast), background-color var(--transition-fast);
      ">
        <input type="file" id="file-input" accept=".json,.csv" style="display:none;" />
        <div style="font-size:28px; margin-bottom:8px;">📁</div>
        <div style="font-weight:600; font-size:15px; margin-bottom:4px;">
          Arraste e solte o arquivo JSON ou CSV
        </div>
        <div style="color:var(--muted); font-size:13px; margin-bottom:14px;">
          Colunas autor, canal, tipo e texto (até 200MB)
        </div>
        <div style="display:flex; justify-content:center; gap:10px;">
          ${renderButton({ id: 'btn-browse-file', text: 'Selecionar arquivo', variant: 'secondary' })}
          ${renderButton({ id: 'btn-load-example', text: 'Usar lote de exemplo', variant: 'primary' })}
        </div>
      </div>

      ${leitura ? `
        <div class="card cl-leitura-card" style="margin-top:4px;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
            <div>
              <div class="cl-mono" style="font-weight:600; font-size:14px;">${esc(leitura.nome)}</div>
              <div style="font-size:12px; color:var(--muted);">${esc(leitura.detalhe || '')}</div>
            </div>
            ${renderBadge('Pronto para processar', 'success')}
          </div>
          <div class="grid-3" style="margin-bottom:14px;">
            <div style="background:var(--bg-surface-2); padding:10px 12px; border-radius:var(--radius-sm);">
              <div style="font-size:12px; color:var(--muted);">Linhas lidas</div>
              <div class="tabular-nums" style="font-size:18px; font-weight:700;">${esc(leitura.total || 0)}</div>
            </div>
            <div style="background:var(--bg-surface-2); padding:10px 12px; border-radius:var(--radius-sm);">
              <div style="font-size:12px; color:var(--muted);">Com erro</div>
              <div class="tabular-nums" style="font-size:18px; font-weight:700;">0</div>
            </div>
            <div style="background:var(--bg-surface-2); padding:10px 12px; border-radius:var(--radius-sm);">
              <div style="font-size:12px; color:var(--muted);">Anônimas</div>
              <div class="tabular-nums" style="font-size:18px; font-weight:700;">${esc(leitura.anonimas || 0)}</div>
            </div>
          </div>
          <div style="font-size:12px; color:var(--dim);">Mostrando prévia das primeiras 5 linhas.</div>
        </div>
      ` : ''}
    </div>
  `.trim();
}
