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
            <p>Transforme o ruído das conversas em inteligência prática. Conecte sua comunidade agora e tome decisões orientadas a dados e pessoas.</p>
          </div>
          <button type="button" class="lp-btn lime btn-ir-login" id="btn-landing-entrar-cta">Iniciar Triagem Agora ↗</button>
        </div>
      </div>
    </section>

    <footer class="lp-footer">
      <div class="lp-wrap lp-foot" style="justify-content:center;text-align:center;">
        <span>© 2026 Sender AI · Telemetria e Curadoria para Comunidades</span>
      </div>
    </footer>
    <div class="lp-toast" id="lpToast">Sistema inicializado.</div>
  `;
}
