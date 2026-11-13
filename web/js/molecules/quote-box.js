// web/js/molecules/quote-box.js
// Molécula: Mensagem original do membro em destaque contextual (< 45 linhas)
import { esc } from '../atoms/escape.js';

export function renderQuoteBox(autor, canal, texto) {
  return `
    <div class="cl-quote-container" style="margin: 8px 0 16px;">
      <div style="font-size:13px; color:var(--muted); margin-bottom:6px;">
        <strong style="color:var(--text); font-weight:600;">${esc(autor)}</strong>
        <span class="cl-mono" style="font-size:12px; margin-left:6px; color:var(--dim);">${esc(canal)}</span>
      </div>
      <div class="cl-quote-bubble" style="
        background: var(--bg-surface-2); border-left: 3px solid var(--accent-cyan);
        padding: 12px 16px; border-radius: 4px var(--radius-md) var(--radius-md) var(--radius-md);
        font-size: 15px; color: var(--text); line-height: 1.5; font-style: italic;
      ">
        “${esc(texto)}”
      </div>
    </div>
  `.trim();
}
