// web/js/molecules/alert-card.js
// Molécula: Membro que precisa de apoio com ações humanas (< 65 linhas)
import { esc } from '../atoms/escape.js';
import { renderBadge } from '../atoms/badge.js';
import { renderButton } from '../atoms/button.js';

// origem = { loteId, rotulo }: de qual lote o alerta veio (a Visão geral junta vários lotes)
export function renderAlertCard(ordem, analise, statusAlerta = null, origem = null) {
  const dataOrigem = origem
    ? `data-lote-id="${esc(origem.loteId)}" data-tipo="${esc(analise.tipo || '')}"`
    : '';
  const acaoNome = analise.tipo === 'reclamacao' ? 'Encaminhar ao time de conteúdo' : 'Oferecer mentoria';
  const statusLabels = {
    encaminhado: 'Encaminhado',
    mentoria_oferecida: 'Mentoria oferecida',
    resolvido: 'Resolvido',
  };

  return `
    <div class="card cl-alert-card" data-ordem="${ordem}" ${dataOrigem} style="display:flex; flex-direction:column; justify-content:space-between; gap:12px; border-left: 3px solid var(--accent-amber);">
      <div>
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
          <div>
            <strong style="font-size:14px;">${esc(analise.autor)}</strong>
            <span class="cl-mono" style="font-size:12px; color:var(--muted); margin-left:6px;">${esc(analise.canal)}</span>
          </div>
          ${renderBadge('Alerta', 'warning')}
        </div>
        ${origem ? `<div class="cl-mono" style="font-size:11px; color:var(--dim); margin-bottom:6px;">📡 ${esc(origem.rotulo)}</div>` : ''}
        <div style="background:var(--accent-amber-bg); color:var(--text); padding:10px 14px; border-radius:var(--radius-sm); font-size:14px; line-height:1.45;">
          “${esc(analise.texto)}”
        </div>
      </div>

      <div class="cl-alert-actions" style="display:flex; gap:8px; align-items:center; justify-content:flex-end;">
        ${statusAlerta ? `
          <div style="margin-left:auto;">
            ${renderBadge(statusLabels[statusAlerta] || statusAlerta, 'info')}
          </div>
        ` : `
          ${renderButton({
            id: `btn-alerta-acao-${ordem}`,
            text: acaoNome,
            variant: 'secondary',
            extraClass: 'btn-tratar-alerta',
          })}
          ${renderButton({
            id: `btn-alerta-ok-${ordem}`,
            text: 'Marcar como resolvido',
            variant: 'primary',
            extraClass: 'btn-resolver-alerta',
          })}
        `}
      </div>
    </div>
  `.trim();
}
