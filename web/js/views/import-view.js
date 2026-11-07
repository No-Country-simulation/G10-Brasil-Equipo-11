// web/js/views/import-view.js
// Tela 1: Ingestão de Lotes JSON/CSV com metadados (< 75 linhas)
import { esc } from '../atoms/escape.js';
import { renderKicker } from '../atoms/kicker.js';
import { renderButton } from '../atoms/button.js';
import { renderDropzone } from '../organisms/dropzone.js';
import { store } from '../store.js';

export function renderImportView() {
  const { leitura, origem, periodo, isProcessing } = store.getState();
  const pronto = Boolean(leitura);
  const total = leitura ? leitura.total : 0;
  const rotulo = isProcessing
    ? 'Processando com IA...'
    : (pronto ? `Processar ${total} interações` : 'Envie um arquivo válido para processar');

  return `
    <div class="view-importar">
      <div class="page-header">
        ${renderKicker('01', 'CONSOLE DE INGESTÃO')}
        <h1 class="page-title">Importar interações</h1>
        <p class="page-subtitle">Envie as mensagens da semana. O pipeline classifica cada uma e gera os ativos para você revisar.</p>
      </div>

      <div class="grid-2" style="align-items:start;">
        <div>
          ${renderDropzone()}
        </div>

        <div style="display:flex; flex-direction:column; gap:16px;">
          <div class="card">
            <h3 class="card-title">Dados do lote</h3>
            <div style="margin-bottom:12px;">
              <label style="display:block; font-size:12px; font-weight:600; color:var(--muted); margin-bottom:6px;">Comunidade de origem</label>
              <input type="text" id="input-origem" value="${esc(origem)}" placeholder="Ex.: Discord_Grupo_ONE_G10" style="
                width:100%; padding:10px 12px; border-radius:var(--radius-md); border:1px solid var(--line);
                background:var(--bg-surface-2); color:var(--text); font-size:14px;
              " />
            </div>

            <div style="margin-bottom:14px;">
              <label style="display:block; font-size:12px; font-weight:600; color:var(--muted); margin-bottom:6px;">Período de referência</label>
              <input type="text" id="input-periodo" value="${esc(periodo)}" placeholder="Ex.: Semana_04" style="
                width:100%; padding:10px 12px; border-radius:var(--radius-md); border:1px solid var(--line);
                background:var(--bg-surface-2); color:var(--text); font-size:14px;
              " />
            </div>

            <div style="font-size:12px; color:var(--dim); margin-bottom:16px;">
              O pacote será salvo em <code>ativos/${new Date().getFullYear()}-${esc(periodo.toLowerCase().replace(/_/g, '-'))}/</code>
            </div>

            ${renderButton({
              id: 'btn-processar-lote',
              text: rotulo,
              variant: 'primary',
              disabled: !pronto || isProcessing,
              fullWidth: true,
            })}
          </div>

          <div class="card" style="font-size:13px; color:var(--muted); line-height:1.5;">
            <strong style="color:var(--text); display:block; margin-bottom:4px;">Antes de enviar</strong>
            Use nomes reais só de quem autorizou. Depoimentos podem virar posts públicos. Mensagens sem autor entram como anônimas.
          </div>
        </div>
      </div>
    </div>
  `.trim();
}
