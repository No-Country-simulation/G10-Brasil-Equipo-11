export function renderLandingHeader() {
  return `
    <header class="lp-header">
      <div class="lp-wrap lp-nav">
        <a class="lp-brand" href="#inicio" aria-label="Sender AI início">
          <svg class="lp-bird" width="36" height="30" viewBox="0 0 120 80" aria-hidden="true">
            <path fill="currentColor" d="M5 55C28 34 42 20 53 5c-2 19 7 28 21 30 12 2 23-4 41-18-10 18-22 31-39 38-15 6-28 4-40-2L5 55Z"/>
            <path fill="currentColor" d="M46 53c-13 7-25 14-39 23 22-7 39-12 54-20l-15-3Z"/>
          </svg>
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
