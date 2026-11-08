// web/js/organisms/landing-content.js
// Organismo: Seções de Problema, Pipeline em 4 Etapas, Governança e Rodapé (< 95 linhas)
import { renderButton } from '../atoms/button.js';

export function renderLandingContent() {
  return `
    <section class="lp-section lp-section-alt" id="problema">
      <div class="lp-wrap">
        <h2 style="font-size:1.75rem; font-weight:700; margin-bottom:0.5rem;">O que se perde no volume diário de mensagens</h2>
        <p style="color:var(--muted); max-width:62ch; margin-bottom:2rem;">
          Comunidades ativas geram centenas de conversas por semana. Sem triagem estruturada, o time gasta horas lendo tudo manualmente.
        </p>
        <div class="grid-3">
          <article class="card">
            <h3 class="card-title">Dúvidas repetidas nos canais</h3>
            <p style="color:var(--muted); font-size:0.9rem; margin-top:0.5rem;">
              Perguntas técnicas respondidas no chat somem no histórico antes de virar material de consulta para a mentoria.
            </p>
          </article>
          <article class="card">
            <h3 class="card-title">Conquistas que passam batido</h3>
            <p style="color:var(--muted); font-size:0.9rem; margin-top:0.5rem;">
              Depoimentos de alunos e projetos entregues ficam espalhados nas conversas sem virar destaque na newsletter ou post.
            </p>
          </article>
          <article class="card">
            <h3 class="card-title">Membros precisando de apoio</h3>
            <p style="color:var(--muted); font-size:0.9rem; margin-top:0.5rem;">
              Relatos de dificuldade ou bloqueio técnico demoram a ser notados por quem pode oferecer mentoria ou suporte direto.
            </p>
          </article>
        </div>
      </div>
    </section>

    <section class="lp-section" id="como-funciona">
      <div class="lp-wrap">
        <h2 style="font-size:1.75rem; font-weight:700; margin-bottom:0.5rem;">Do arquivo bruto ao pacote aprovado em quatro passos</h2>
        <p style="color:var(--muted); max-width:62ch; margin-bottom:2rem;">
          O pipeline combina classificação automatizada em Python com revisão humana obrigatória antes de qualquer publicação.
        </p>
        <div class="grid-4">
          <div class="lp-step">
            <span class="cl-mono" style="font-size:12px; color:var(--accent-cyan);">Passo 1</span>
            <h3 style="font-size:1.05rem; font-weight:600; margin:0.4rem 0;">Importar interações</h3>
            <p style="color:var(--muted); font-size:0.88rem;">Envie o arquivo JSON ou CSV com as mensagens da semana ou carregue o lote de demonstração.</p>
          </div>
          <div class="lp-step">
            <span class="cl-mono" style="font-size:12px; color:var(--accent-cyan);">Passo 2</span>
            <h3 style="font-size:1.05rem; font-weight:600; margin:0.4rem 0;">Analisar sentimento</h3>
            <p style="color:var(--muted); font-size:0.88rem;">Cada mensagem recebe classificação de sentimento, tópico principal e nota de relevância.</p>
          </div>
          <div class="lp-step">
            <span class="cl-mono" style="font-size:12px; color:var(--accent-cyan);">Passo 3</span>
            <h3 style="font-size:1.05rem; font-weight:600; margin:0.4rem 0;">Separar por rota</h3>
            <p style="color:var(--muted); font-size:0.88rem;">O motor direciona para FAQ da mentoria, Case de sucesso, Alerta humano ou Sem ação.</p>
          </div>
          <div class="lp-step">
            <span class="cl-mono" style="font-size:12px; color:var(--accent-cyan);">Passo 4</span>
            <h3 style="font-size:1.05rem; font-weight:600; margin:0.4rem 0;">Revisar e exportar</h3>
            <p style="color:var(--muted); font-size:0.88rem;">Edite os textos, marque a autorização do membro e exporte o pacote final validado.</p>
          </div>
        </div>
      </div>
    </section>

    <section class="lp-section lp-section-alt" id="governanca">
      <div class="lp-wrap">
        <div class="card" style="padding:2.25rem; display:flex; align-items:center; justify-content:space-between; gap:1.5rem; flex-wrap:wrap; border-left:3px solid var(--accent-lime);">
          <div style="max-width:60ch;">
            <h2 style="font-size:1.5rem; font-weight:700; margin-bottom:0.4rem;">Nada é publicado sem a palavra final da equipe</h2>
            <p style="color:var(--muted); font-size:0.95rem;">
              Posts com nome de membros exigem confirmação explícita de consentimento, alertas vão direto para o time de comunidade e todas as decisões ficam salvas no histórico.
            </p>
          </div>
          ${renderButton({ id: 'btn-cta-entrar', text: 'Entrar no painel', variant: 'primary', extraClass: 'btn-ir-login' })}
        </div>
      </div>
    </section>

    <footer style="padding:2rem 1.25rem; color:var(--dim); font-size:0.82rem;">
      <div class="lp-wrap" style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:1rem;">
        <span>Sender AI — Inteligência e Curadoria para Comunidades</span>
        <span class="cl-mono">FastAPI · Python · Supabase · Gemini</span>
      </div>
    </footer>
  `.trim();
}
