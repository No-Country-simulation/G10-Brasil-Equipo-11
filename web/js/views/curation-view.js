// web/js/views/curation-view.js
// Tela 3: Curadoria Editorial Human-in-the-Loop em Fila (< 85 linhas)
import { renderKicker } from '../atoms/kicker.js';
import { renderButton } from '../atoms/button.js';
import { renderCurationQueue } from '../organisms/curation-queue.js';
import { renderAssetEditor } from '../organisms/asset-editor.js';
import { store } from '../store.js';

export function extrairItensCuradoria(resultado) {
  if (!resultado || !resultado.ativos_distribuicao_gerados) return [];
  const ativos = resultado.ativos_distribuicao_gerados;
  const items = [];

  if (ativos.post_linkedin) {
    items.push({ id: 'post', title: `Post: ${ativos.post_linkedin.titulo}` });
  }
  if (ativos.destaque_newsletter_semanal) {
    items.push({ id: 'newsletter', title: `Newsletter: ${ativos.destaque_newsletter_semanal.secao}` });
  }
  (ativos.sugestao_conteudo_faq || []).forEach((faq, idx) => {
    items.push({ id: `faq_${idx}`, title: faq.tema.replace('Dica Rápida:', '').trim() });
  });

  return items;
}

export function renderCurationView() {
  const { resultado, activeItem } = store.getState();

  if (!resultado) {
    return `
      <div class="card" style="padding:48px; text-align:center; max-width:600px; margin:40px auto;">
        <h2 style="margin-bottom:8px;">Nenhum lote para curadoria</h2>
        <p style="color:var(--muted); margin-bottom:20px;">Processe as mensagens no Console de Ingestão primeiro.</p>
        ${renderButton({ id: 'btn-go-importar', text: 'Ir para Importar', variant: 'primary' })}
      </div>
    `;
  }

  const items = extrairItensCuradoria(resultado);
  const currentActive = activeItem || (items[0] ? items[0].id : null);

  return `
    <div class="view-curadoria">
      <div class="page-header">
        ${renderKicker('03', 'GOVERNANÇA HUMAN-IN-THE-LOOP')}
        <h1 class="page-title">Curadoria editorial</h1>
        <p class="page-subtitle">Rascunhos gerados pela IA. Confira se o texto condiz com a mensagem original. Nada é publicado sem sua aprovação.</p>
      </div>

      <div style="display:grid; grid-template-columns: 320px 1fr; gap:20px; align-items:start;">
        <div>
          ${renderCurationQueue(items)}
        </div>
        <div>
          ${renderAssetEditor(resultado, currentActive)}
        </div>
      </div>
    </div>
  `.trim();
}
