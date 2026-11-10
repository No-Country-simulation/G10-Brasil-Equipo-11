// web/js/organisms/asset-editor.js
// Organismo: Editor contextual do ativo ativo (Post, Newsletter ou FAQ) (< 120 linhas)
import { esc } from '../atoms/escape.js';
import { renderBadge } from '../atoms/badge.js';
import { renderButton } from '../atoms/button.js';
import { renderQuoteBox } from '../molecules/quote-box.js';
import { store } from '../store.js';

export function renderAssetEditor(resultado, activeId) {
  const { decisoes, textosEditados, autorizado } = store.getState();
  const ativos = resultado.ativos_distribuicao_gerados;
  const status = decisoes[activeId] || 'p';

  if (!activeId) {
    return `<div class="card" style="padding:40px; text-align:center; color:var(--muted);">Nenhum ativo selecionado.</div>`;
  }

  // 1. POST LINKEDIN
  if (activeId === 'post' && ativos.post_linkedin) {
    const post = ativos.post_linkedin;
    const cases = resultado.analises.filter(a => a.rota === 'case_sucesso');
    const membro = cases.length > 0 ? cases.reduce((max, c) => c.relevancia > max.relevancia ? c : max, cases[0]) : null;
    const copyVal = textosEditados.post_copy !== undefined ? textosEditados.post_copy : post.copy;
    const nomeMembro = membro ? membro.autor.split(' ')[0] : 'O membro';

    return `
      <div class="card cl-editor-card">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
          ${renderBadge('Post do LinkedIn', 'info')}
          <span style="font-size:12px; color:var(--muted);">Engajamento previsto: <strong style="color:var(--text);">${esc(post.potencial_engajamento).toLowerCase()}</strong></span>
        </div>

        ${membro ? renderQuoteBox(membro.autor, membro.canal, membro.texto) : ''}

        <h3 class="card-title" style="margin: 12px 0 8px;">${esc(post.titulo)}</h3>

        <div style="margin-bottom:14px;">
          <label style="display:block; font-size:12px; font-weight:600; color:var(--muted); margin-bottom:6px;">Texto do post (editável)</label>
          <textarea id="txt_post_copy" class="cl-textarea" rows="8" style="
            width:100%; padding:12px; border-radius:var(--radius-md); border:1px solid var(--line);
            background:var(--bg-surface-2); color:var(--text); font-family:var(--font-sans); font-size:14px; line-height:1.45;
          ">${esc(copyVal)}</textarea>
        </div>

        <div style="margin-bottom:16px;">
          <label style="display:inline-flex; align-items:center; gap:8px; font-size:13.5px; cursor:pointer;">
            <input type="checkbox" id="chk_autorizado" ${autorizado ? 'checked' : ''} style="width:16px; height:16px; accent-color:var(--accent-lime);" />
            <span>${esc(nomeMembro)} autorizou o uso do nome e do depoimento</span>
          </label>
        </div>

        ${renderDecisionBar(activeId, status, 'Aprovar post', !autorizado)}
      </div>
    `.trim();
  }

  // 2. NEWSLETTER
  if (activeId === 'newsletter' && ativos.destaque_newsletter_semanal) {
    const news = ativos.destaque_newsletter_semanal;
    const chamadaVal = textosEditados.news_chamada !== undefined ? textosEditados.news_chamada : news.chamada;
    const resumoVal = textosEditados.news_resumo !== undefined ? textosEditados.news_resumo : news.resumo;

    return `
      <div class="card cl-editor-card">
        <div style="margin-bottom:12px;">${renderBadge('Newsletter Semanal', 'neutral')}</div>
        <h3 class="card-title" style="margin-bottom:12px;">${esc(news.secao)}</h3>

        <div style="margin-bottom:12px;">
          <label style="display:block; font-size:12px; font-weight:600; color:var(--muted); margin-bottom:6px;">Chamada</label>
          <input type="text" id="txt_news_chamada" value="${esc(chamadaVal)}" style="
            width:100%; padding:10px 12px; border-radius:var(--radius-md); border:1px solid var(--line);
            background:var(--bg-surface-2); color:var(--text); font-size:14px;
          " />
        </div>

        <div style="margin-bottom:16px;">
          <label style="display:block; font-size:12px; font-weight:600; color:var(--muted); margin-bottom:6px;">Resumo</label>
          <textarea id="txt_news_resumo" rows="6" style="
            width:100%; padding:12px; border-radius:var(--radius-md); border:1px solid var(--line);
            background:var(--bg-surface-2); color:var(--text); font-size:14px; line-height:1.45;
          ">${esc(resumoVal)}</textarea>
        </div>

        ${renderDecisionBar(activeId, status, 'Aprovar destaque', false)}
      </div>
    `.trim();
  }

  // 3. FAQ
  if (activeId.startsWith('faq_')) {
    const idx = parseInt(activeId.replace('faq_', ''), 10);
    const faqs = ativos.sugestao_conteudo_faq || [];
    const item = faqs[idx];
    if (!item) return `<div class="card">Item não encontrado.</div>`;

    const duvidas = resultado.analises.filter(a => a.rota === 'faq');
    const duvida = duvidas[idx] || null;
    const conteudoVal = textosEditados[`faq_${idx}_conteudo`] !== undefined ? textosEditados[`faq_${idx}_conteudo`] : item.conteudo;

    return `
      <div class="card cl-editor-card">
        <div style="margin-bottom:12px;">${renderBadge('Dica para a mentoria', 'neutral')}</div>
        ${duvida ? renderQuoteBox(duvida.autor, duvida.canal, duvida.texto) : ''}
        <h3 class="card-title" style="margin: 12px 0 8px;">${esc(item.tema)}</h3>

        <div style="margin-bottom:16px;">
          <label style="display:block; font-size:12px; font-weight:600; color:var(--muted); margin-bottom:6px;">Resposta sugerida (editável)</label>
          <textarea id="txt_faq_${idx}_conteudo" rows="7" style="
            width:100%; padding:12px; border-radius:var(--radius-md); border:1px solid var(--line);
            background:var(--bg-surface-2); color:var(--text); font-size:14px; line-height:1.45;
          ">${esc(conteudoVal)}</textarea>
        </div>

        ${renderDecisionBar(activeId, status, 'Enviar à mentoria', false)}
      </div>
    `.trim();
  }

  return `<div class="card">Item desconhecido.</div>`;
}

function renderDecisionBar(id, status, labelAprovar, bloqueado = false) {
  if (status === 'p') {
    return `
      <div style="display:flex; justify-content:flex-end; gap:10px; align-items:center; border-top:1px solid var(--line); padding-top:14px;">
        ${renderButton({ id: 'btn-descartar-ativo', text: 'Descartar', variant: 'secondary' })}
        ${renderButton({ id: 'btn-aprovar-ativo', text: labelAprovar, variant: 'primary', disabled: bloqueado })}
      </div>
    `;
  }
  return `
    <div style="display:flex; justify-content:space-between; align-items:center; border-top:1px solid var(--line); padding-top:14px;">
      <div>${renderBadge(status === 'a' ? 'Aprovado' : 'Descartado', status === 'a' ? 'success' : 'neutral')}</div>
      ${renderButton({ id: 'btn-desfazer-decisao', text: 'Desfazer decisão', variant: 'secondary' })}
    </div>
  `;
}
