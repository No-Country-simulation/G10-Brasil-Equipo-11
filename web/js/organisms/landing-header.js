export function renderLandingHeader() {
  return `
    <header class="lp-header">
      <div class="lp-wrap lp-nav">
        <a class="lp-brand" href="#inicio" aria-label="Sender AI início">
          <span class="lp-bird" aria-hidden="true"><i></i></span>
          Sender AI
        </a>

        <nav class="lp-navlinks" aria-label="Seções da página inicial">
          <a href="#solucao">01.Desafio</a>
          <a href="#como-funciona">02.Pipeline</a>
          <a href="#demonstracao">03.Telemetria</a>
          <a href="#recursos">04.Governança</a>
        </nav>

        <div class="lp-navright">
          <button type="button" class="lp-btn lime btn-ir-login" id="btn-landing-entrar-topo">
            Entrar
          </button>
        </div>
      </div>
    </header>
  `;
}
