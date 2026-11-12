// web/js/views/import-view.js
// Tela 1: Ingestão de Lotes JSON/CSV com metadados (< 75 linhas)
import { esc } from '../atoms/escape.js';
import { renderKicker } from '../atoms/kicker.js';
import { renderButton } from '../atoms/button.js';
import { renderDropzone } from '../organisms/dropzone.js';
import { store } from '../store.js';

export function renderImportView() {
  const { leitura, fonte, canal, mes, ano, fontesData, isProcessing, duplicado } = store.getState();
  // O aviso só vale para o arquivo em que foi dado.
  const repetido = duplicado && leitura && duplicado.lote === leitura.lote ? duplicado : null;
  const quando = repetido && repetido.processado_em
    ? new Date(repetido.processado_em).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
    : null;
  const pronto = Boolean(leitura && fonte && canal);
  const total = leitura ? leitura.total : 0;
  const rotulo = isProcessing
    ? 'Processando com IA...'
    : (!leitura ? 'Envie um arquivo válido para processar' : (!pronto ? 'Escolha a fonte e o canal' : `Processar ${total} interações`));

  const listaFontes = fontesData?.canais ? Object.keys(fontesData.canais) : ['Discord', 'Telegram', 'WhatsApp', 'Arquivo manual'];
  const canaisDaFonte = (fontesData?.canais && fontesData.canais[fonte]) ? fontesData.canais[fonte] : ['Grupo ONE G10', 'Dev Brasil'];
  const meses = fontesData?.meses || ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'];
  const anos = fontesData?.anos || [2024, 2025, 2026];
  const periodoFmt = `${ano}-${String(mes).padStart(2, '0')}`;

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
              <label for="select-fonte" style="display:block; font-size:12px; font-weight:600; color:var(--muted); margin-bottom:6px;">Fonte dos dados</label>
              <select id="select-fonte" style="
                width:100%; padding:10px 12px; border-radius:var(--radius-md); border:1px solid var(--line);
                background:var(--bg-surface-2); color:var(--text); font-size:14px;
              ">
                ${listaFontes.map(f => `<option value="${esc(f)}" ${f === fonte ? 'selected' : ''}>${esc(f)}</option>`).join('')}
              </select>
            </div>

            <div style="margin-bottom:12px;">
              <label for="select-canal" style="display:block; font-size:12px; font-weight:600; color:var(--muted); margin-bottom:6px;">Canal</label>
              <select id="select-canal" style="
                width:100%; padding:10px 12px; border-radius:var(--radius-md); border:1px solid var(--line);
                background:var(--bg-surface-2); color:var(--text); font-size:14px;
              ">
                ${canaisDaFonte.map(c => `<option value="${esc(c)}" ${c === canal ? 'selected' : ''}>${esc(c)}</option>`).join('')}
              </select>
            </div>

            <div class="grid-2" style="gap:10px; margin-bottom:14px;">
              <div>
                <label for="select-mes" style="display:block; font-size:12px; font-weight:600; color:var(--muted); margin-bottom:6px;">Mês de referência</label>
                <select id="select-mes" style="
                  width:100%; padding:10px 12px; border-radius:var(--radius-md); border:1px solid var(--line);
                  background:var(--bg-surface-2); color:var(--text); font-size:14px;
                ">
                  ${meses.map((m, idx) => `<option value="${idx + 1}" ${(idx + 1) === Number(mes) ? 'selected' : ''}>${esc(m)}</option>`).join('')}
                </select>
              </div>
              <div>
                <label for="select-ano" style="display:block; font-size:12px; font-weight:600; color:var(--muted); margin-bottom:6px;">Ano</label>
                <select id="select-ano" style="
                  width:100%; padding:10px 12px; border-radius:var(--radius-md); border:1px solid var(--line);
                  background:var(--bg-surface-2); color:var(--text); font-size:14px;
                ">
                  ${anos.map(a => `<option value="${a}" ${Number(a) === Number(ano) ? 'selected' : ''}>${a}</option>`).join('')}
                </select>
              </div>
            </div>

            <div style="font-size:12px; color:var(--dim); margin-bottom:16px;">
              O pacote será salvo em <code>ativos/${periodoFmt}/</code>
            </div>

            ${repetido ? `
              <div id="aviso-duplicado" style="border:1px solid var(--accent-amber); background:var(--accent-amber-bg); border-radius:var(--radius-md); padding:12px 14px; margin-bottom:12px; font-size:13px; line-height:1.5; color:var(--text);">
                <strong>Este conteúdo já foi processado${quando ? ` em ${esc(quando)}` : ''}.</strong><br>
                ${esc(String(repetido.total))} interações · ${esc(repetido.origem || '')} · ${esc(repetido.periodo || '')}
                <div style="display:flex; gap:8px; margin-top:10px; flex-wrap:wrap;">
                  ${renderButton({ id: 'btn-abrir-existente', text: 'Abrir resultado existente', variant: 'primary', disabled: isProcessing })}
                  ${renderButton({ id: 'btn-processar-de-novo', text: isProcessing ? 'Processando com IA...' : 'Processar de novo', variant: 'secondary', disabled: isProcessing })}
                </div>
              </div>
            ` : renderButton({
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
