export function renderLandingFooter() {
  return `
    <section class="lp-section" id="recursos">
      <div class="lp-wrap">
        <div class="lp-section-head">
          <div>
            <div class="lp-kicker">04 // Governança & Valor</div>
            <h2>Inteligência que organiza. Pessoas que decidem.</h2>
          </div>
          <p>A IA acelera a triagem das conversas, mas a sua equipe mantém o controle editorial e estratégico.</p>
        </div>
        <div class="lp-features-grid">
          <article class="lp-feature">
            <span class="tag">01 / CLASSIFICAÇÃO SEMÂNTICA</span>
            <h3>Contexto em cada interação</h3>
            <p>Organize mensagens por sentimento, categoria técnica, urgência e rota sugerida para zerar o tempo de triagem bruta.</p>
          </article>
          <article class="lp-feature">
            <span class="tag">02 / RADAR DE COMUNIDADE</span>
            <h3>Oportunidades e sinais de atenção</h3>
            <p>Identifique tópicos emergentes, ideias de funcionalidades e gargalos de experiência em tempo real.</p>
          </article>
          <article class="lp-feature">
            <span class="tag">03 / SÍNTESE ASSISTIDA</span>
            <h3>Conteúdo pronto para revisão</h3>
            <p>Transforme dúvidas recorrentes da comunidade em rascunhos de documentação, FAQs e comunicados oficiais.</p>
          </article>
          <article class="lp-feature">
            <span class="tag">04 / HUMAN-IN-THE-LOOP</span>
            <h3>Revisão humana e rastreabilidade</h3>
            <p>Nenhuma decisão crítica ocorre no escuro: aprove, ajuste ou descarte sugestões com log completo de auditoria.</p>
          </article>
        </div>
      </div>
    </section>

    <section class="lp-quote">
      <div class="lp-wrap">
        <div class="lp-kicker" style="justify-content:center">PROPÓSITO SENDER AI</div>
        <blockquote>“Enxergar com clareza <span>cada sinal importante</span> que a sua comunidade compartilha todos os dias.”</blockquote>
      </div>
    </section>

    <section class="lp-section">
      <div class="lp-wrap">
        <div class="lp-cta-box">
          <div>
            <h2>Escute sua comunidade.<br>Ative a telemetria hoje.</h2>
            <p>Sender AI — arquitetura leve em HTML/CSS/JS puro conectada ao backend Python, SQLite e Supabase.</p>
          </div>
          <button type="button" class="lp-btn lime btn-ir-login" id="btn-landing-entrar-cta">Entrar no Console ↗</button>
        </div>
      </div>
    </section>

    <footer class="lp-footer">
      <div class="lp-wrap lp-foot">
        <a class="lp-brand" href="#inicio">
          <svg class="lp-bird" width="36" height="30" viewBox="0 0 120 80" aria-hidden="true">
            <path fill="currentColor" d="M5 55C28 34 42 20 53 5c-2 19 7 28 21 30 12 2 23-4 41-18-10 18-22 31-39 38-15 6-28 4-40-2L5 55Z"/>
            <path fill="currentColor" d="M46 53c-13 7-25 14-39 23 22-7 39-12 54-20l-15-3Z"/>
          </svg>
          Sender AI
        </a>
        <span>© 2026 SENDER AI · TELEMETRIA E CURADORIA HUMANA · ZERO-DEPENDENCY STACK</span>
        <div class="lp-footlinks">
          <a href="#solucao">Desafio</a>
          <a href="#como-funciona">Pipeline</a>
          <a href="#demonstracao">Console</a>
        </div>
      </div>
    </footer>
    <div class="lp-toast" id="lpToast">Sistema inicializado.</div>
  `;
}
