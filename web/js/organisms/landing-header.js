// web/js/organisms/landing-header.js
// Organismo: Cabeçalho público da Landing Page (< 55 linhas)
import { renderBadge } from '../atoms/badge.js';
import { renderButton } from '../atoms/button.js';
import { store } from '../store.js';

export function renderLandingHeader() {
  const { saudeInfo } = store.getState();
  const modoTexto = saudeInfo?.modo_llm === 'gemini' ? 'Gemini ativo' : 'Modo simulado';
  const modoCor = saudeInfo?.modo_llm === 'gemini' ? 'info' : 'warning';

  return `
    <header class="lp-header">
      <div class="lp-nav">
        <a href="#inicio" style="display:flex; align-items:center; gap:10px;" aria-label="Sender AI início">
          <div role="img" aria-label="Sender AI" style="width:30px; height:30px; background:var(--text); -webkit-mask:url('assets/logo_sender_ai.png') center / contain no-repeat; mask:url('assets/logo_sender_ai.png') center / contain no-repeat;"></div>
          <span style="font-weight:700; font-size:18px; letter-spacing:-0.02em; color:var(--text);">Sender AI</span>
        </a>

        <nav class="lp-links" aria-label="Seções da página">
          <a href="#problema">O problema</a>
          <a href="#como-funciona">Como funciona</a>
          <a href="#governanca">Curadoria humana</a>
        </nav>

        <div style="display:flex; align-items:center; gap:12px;">
          ${renderBadge(modoTexto, modoCor)}
          ${renderButton({
            id: 'btn-landing-entrar',
            text: 'Entrar',
            variant: 'primary',
            extraClass: 'btn-ir-login',
          })}
        </div>
      </div>
    </header>
  `.trim();
}
