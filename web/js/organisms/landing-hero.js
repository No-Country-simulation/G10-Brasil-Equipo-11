// web/js/organisms/landing-hero.js
// Organismo: Seção Hero com ilustração vetorial da marca e proposta de valor (< 75 linhas)
import { renderButton } from '../atoms/button.js';

export function renderLandingHero() {
  return `
    <section class="lp-hero" id="inicio">
      <div class="lp-wrap lp-hero-grid">
        <div>
          <p class="cl-mono" style="font-size:12px; color:var(--accent-cyan); margin-bottom:12px;">
            Telemetria e curadoria para comunidades
          </p>
          <h1 class="lp-headline">
            Transforme as conversas da comunidade em pautas, FAQs e apoio aos membros.
          </h1>
          <p class="lp-lead">
            O Sender AI lê os lotes semanais do Discord, Telegram e WhatsApp, classifica o sentimento de cada mensagem e prepara rascunhos de conteúdo e alertas de mentoria para sua equipe revisar.
          </p>
          <div style="display:flex; align-items:center; gap:12px; flex-wrap:wrap;">
            ${renderButton({
              id: 'btn-hero-entrar',
              text: 'Entrar no painel',
              variant: 'primary',
              extraClass: 'btn-ir-login',
            })}
            <a href="#como-funciona" style="
              display:inline-flex; align-items:center; padding:9px 16px;
              border-radius:var(--radius-md); border:1px solid var(--line);
              background:var(--bg-surface); color:var(--text); font-size:14px; font-weight:500;
            ">Ver como funciona</a>
          </div>
        </div>

        <div class="lp-bird-stage">
          <div class="lp-orbit"></div>
          <svg class="lp-bird-svg" viewBox="0 0 520 360" role="img" aria-label="Pássaro símbolo do Sender AI">
            <path fill="var(--text)" d="M28 242C104 182 158 117 192 35c-2 73 28 116 78 128 47 11 98-13 211-102-51 83-103 141-171 166-55 20-102 12-146-9L28 242Z"/>
            <path fill="var(--accent-lime)" d="M211 218C146 250 89 293 25 337c99-27 172-51 239-92l-53-27Z"/>
            <path fill="var(--text)" d="M243 163c41-36 72-54 108-50 34 3 66 25 105 7-27 35-65 54-111 52-38-1-69-5-102-9Z"/>
            <path fill="var(--bg)" d="M270 163c24-16 46-22 69-19-16 12-32 19-54 22Z"/>
          </svg>

          <div class="lp-stat-pill" style="top:18px; left:0;">
            <span style="display:block; font-size:11px; color:var(--muted);">Lote de demonstração</span>
            <strong class="cl-mono tabular-nums" style="font-size:18px; color:var(--text);">20 interações</strong>
          </div>

          <div class="lp-stat-pill" style="bottom:18px; right:0;">
            <span style="display:block; font-size:11px; color:var(--muted);">Rotas de saída</span>
            <strong class="cl-mono" style="font-size:14px; color:var(--accent-lime);">FAQ · Case · Alerta</strong>
          </div>
        </div>
      </div>
    </section>
  `.trim();
}
