// web/js/organisms/telemetry-table.js
// Organismo: Tabela de telemetria com filtro de rotas e relevância (< 95 linhas)
import { esc } from '../atoms/escape.js';
import { renderBadge } from '../atoms/badge.js';
import { store } from '../store.js';

export function renderTelemetryTable(analises = [], titulo = 'Interações analisadas') {
  const { filtroRota } = store.getState();
  const rotasMap = {
    'FAQ': 'faq',
    'Case de sucesso': 'case_sucesso',
    'Alerta': 'alerta',
    'Sem ação': 'nenhuma',
  };

  const opcoes = ['Todas', 'FAQ', 'Case de sucesso', 'Alerta', 'Sem ação'];
  const linhasFiltradas = analises.filter(a => {
    if (filtroRota === 'Todas') return true;
    return a.rota === rotasMap[filtroRota];
  });

  return `
    <div class="card cl-telemetry-container">
      <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px; margin-bottom:16px;">
        <h3 class="card-title" style="margin:0;">${esc(titulo)} (${linhasFiltradas.length})</h3>
        <div class="cl-filter-group" style="display:flex; gap:6px; flex-wrap:wrap;">
          ${opcoes.map(opt => {
            const isSelected = filtroRota === opt;
            const style = isSelected
              ? 'background: var(--accent-lime-bg); color: var(--accent-lime); border-color: var(--accent-lime); font-weight:600;'
              : 'background: var(--bg-surface-2); color: var(--muted); border-color: var(--line);';
            return `
              <button class="btn-filter-route" data-filter="${opt}" style="
                padding: 4px 12px; border-radius: var(--radius-full); font-size: 12px;
                border: 1px solid transparent; transition: all var(--transition-fast); ${style}
              ">
                ${esc(opt)}
              </button>
            `;
          }).join('')}
        </div>
      </div>

      <div style="overflow-x:auto;">
        <table style="width:100%; font-size:13px; text-align:left;">
          <thead>
            <tr style="border-bottom:1px solid var(--line); color:var(--muted); font-size:12px; text-transform:uppercase;">
              <th style="padding:8px 10px;">Autor</th>
              <th style="padding:8px 10px;">Canal</th>
              <th style="padding:8px 10px; width:45%;">Mensagem</th>
              <th style="padding:8px 10px;">Sentimento</th>
              <th style="padding:8px 10px; text-align:right;">Relevância</th>
            </tr>
          </thead>
          <tbody>
            ${linhasFiltradas.map(a => {
              const sentimento = a.sentimento || 'Neutro';
              return `
                <tr style="border-bottom:1px solid var(--line); transition:background var(--transition-fast);" class="hover-row">
                  <td style="padding:10px; font-weight:600;">${esc(a.autor)}</td>
                  <td style="padding:10px;"><span class="cl-mono" style="color:var(--muted); font-size:12px;">${esc(a.canal)}</span></td>
                  <td style="padding:10px; color:var(--text); line-height:1.4;">${esc(a.texto)}</td>
                  <td style="padding:10px;">${renderBadge(sentimento, sentimento.includes('Positivo') ? 'info' : (sentimento.includes('Negativo') ? 'danger' : 'neutral'))}</td>
                  <td style="padding:10px; text-align:right;">
                    <span class="tabular-nums" style="font-weight:600; color:var(--text);">${a.relevancia ?? '—'}/10</span>
                  </td>
                </tr>
              `;
            }).join('')}
          </tbody>
        </table>
      </div>
    </div>
  `.trim();
}
