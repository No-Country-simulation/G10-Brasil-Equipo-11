// web/js/organisms/pending-batches.js
// Organismo: Lotes com ativos ou alertas pendentes, do mais antigo para o mais novo (< 60 linhas)
import { esc } from '../atoms/escape.js';
import { renderButton } from '../atoms/button.js';

const MESES = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'];

export function periodoCurto(periodo) {
  const m = /^(\d{4})-(\d{2})$/.exec(periodo || '');
  return m ? `${MESES[parseInt(m[2], 10) - 1] || m[2]}/${m[1]}` : (periodo || '');
}

export function primeiroLoteComAtivos(lotes = []) {
  return lotes.find(l => l.ativos_pendentes > 0) || null;
}

function plural(n, um, varios) {
  return `${n} ${n === 1 ? um : varios}`;
}

export function renderPendingBatches(lotes = []) {
  if (!lotes.length) return '';
  return `
    <div class="card" style="margin-bottom:20px;">
      <h3 class="card-title">Lotes com pendências</h3>
      <p class="card-caption">Do mais antigo para o mais novo.</p>
      <div class="cl-lotes-pendentes">
        ${lotes.map(l => {
          const partes = [];
          if (l.ativos_pendentes > 0) partes.push(plural(l.ativos_pendentes, 'ativo', 'ativos'));
          if (l.alertas_pendentes > 0) partes.push(plural(l.alertas_pendentes, 'alerta', 'alertas'));
          const temAtivos = l.ativos_pendentes > 0;
          return `
            <div class="cl-lote-linha">
              <div class="cl-lote-origem">
                <strong>${esc((l.origem || '').replace(/_/g, ' '))}</strong>
                <span class="cl-mono">${esc(periodoCurto(l.periodo))}</span>
              </div>
              <span class="cl-lote-contagem">${esc(partes.join(' · '))}</span>
              ${renderButton({
                text: temAtivos ? 'Revisar' : 'Ver alerta',
                variant: temAtivos ? 'primary' : 'secondary',
                extraClass: 'btn-revisar-lote',
                data: { loteId: l.lote_id, destino: temAtivos ? 'curadoria' : 'alertas' },
              })}
            </div>
          `;
        }).join('')}
      </div>
    </div>
  `.trim();
}
