// web/js/views/curation-view.js
// Tela 3: Curadoria Editorial Human-in-the-Loop em Fila (< 85 linhas)
import { renderKicker } from '../atoms/kicker.js';
import { renderButton } from '../atoms/button.js';
import { renderCurationQueue } from '../organisms/curation-queue.js';
import { renderAssetEditor } from '../organisms/asset-editor.js';
import { store } from '../store.js';
import { esc } from '../atoms/escape.js';
import { renderBadge } from '../atoms/badge.js';
import { periodoCurto } from '../organisms/pending-batches.js';
import { totaisDaFila } from '../fila.js';

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

function cartao(titulo, texto, botoes = '') {
  return `
    <div class="card" style="padding:48px; text-align:center; max-width:600px; margin:40px auto;">
      <h2 style="margin-bottom:8px;">${esc(titulo)}</h2>
      <p style="color:var(--muted); margin-bottom:20px;">${esc(texto)}</p>
      <div style="display:flex; gap:8px; justify-content:center; flex-wrap:wrap;">${botoes}</div>
    </div>
  `;
}

export function renderCurationView() {
  const s = store.getState();
  const { resultado, activeItem, origem, periodo, fila } = s;

  if (fila.carregando && !resultado) {
    return cartao('Carregando a fila…', 'Buscando no banco todos os lotes com conteúdos pendentes.');
  }
  const avisoErro = fila.erro ? `<div class="card cl-visao-erro" role="alert">${esc(fila.erro)}</div>` : '';
  if (!resultado) {
    const titulo = fila.carregada ? 'Nada pendente' : 'Nenhum lote aberto';
    const texto = fila.carregada
      ? 'Todos os conteúdos já foram revisados. Importe interações novas para gerar mais.'
      : 'Carregue a fila com todos os lotes pendentes ou importe interações novas.';
    return avisoErro + cartao(titulo, texto, `
      ${renderButton({ id: 'btn-atualizar-fila', text: 'Carregar fila', variant: 'primary' })}
      ${renderButton({ id: 'btn-go-importar', text: 'Ir para Importar', variant: 'secondary' })}
    `);
  }

  const { pendentes } = totaisDaFila(s);
  const nLotes = fila.ordem.length;
  const cabecalhoFila = fila.avulso
    ? `<div class="cl-fila-aviso" role="status">
         <span>Lote aberto do histórico.</span>
         ${renderButton({ id: 'btn-ver-todos-pendentes', text: 'Ver todos os pendentes', variant: 'secondary' })}
       </div>`
    : `<div style="display:flex; gap:8px; flex-wrap:wrap; align-items:center; margin-bottom:10px;">
         ${renderBadge(`${nLotes} ${nLotes === 1 ? 'lote' : 'lotes'} · ${pendentes} ${pendentes === 1 ? 'pendente' : 'pendentes'}`, 'success')}
         ${renderButton({ id: 'btn-atualizar-fila', text: fila.carregando ? 'Atualizando…' : 'Atualizar fila', variant: 'secondary', disabled: fila.carregando })}
       </div>`;

  const items = extrairItensCuradoria(resultado);
  const currentActive = activeItem || (items[0] ? items[0].id : null);

  return `
    <div class="view-curadoria">
      ${avisoErro}
      <div class="page-header">
        ${renderKicker('03', 'GOVERNANÇA HUMAN-IN-THE-LOOP')}
        <h1 class="page-title">Curadoria editorial</h1>
        ${cabecalhoFila}
        <p class="page-subtitle">Rascunhos gerados pela IA. Confira se o texto condiz com a mensagem original. Nada é publicado sem sua aprovação.</p>
      </div>

      <div class="cl-curadoria-grid">
        <div>
          ${renderCurationQueue()}
        </div>
        <div>
          <div style="margin-bottom:8px;">
            <span class="cl-badge cl-origem-badge" style="background:var(--bg-surface-2); color:var(--text); border:1px solid var(--line); font-size:12px; font-weight:500;">
              📡 ${esc((origem || '').replace(/_/g, ' '))} · ${esc(periodoCurto(periodo))}
            </span>
          </div>
          ${renderAssetEditor(resultado, currentActive)}
        </div>
      </div>
    </div>
  `.trim();
}
