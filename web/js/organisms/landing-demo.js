// web/js/organisms/landing-demo.js
// Seção 03 da landing: o painel real do sistema, navegável, com dados fictícios (ver js/demo/).
import { renderAppDemo } from '../demo/app-demo.js';

export function renderLandingDemo() {
  return `
    <section class="lp-section" id="demonstracao">
      <div class="lp-wrap">
        <div class="lp-section-head">
          <div>
            <div class="lp-kicker">03 // Console Operacional</div>
            <h2>Telemetria da sua comunidade, pronta para agir.</h2>
          </div>
          <p>Este é o painel do Sender AI com dados de exemplo. Navegue pela Visão geral, abra a Curadoria, aprove um conteúdo e trate um alerta.</p>
        </div>

        ${renderAppDemo()}

        <div class="lp-demo-rodape">
          <span>Dados de exemplo. Nada do que você faz aqui é gravado.</span>
          <button type="button" class="lp-btn lime btn-ir-login" id="btn-landing-entrar-demo">Entrar no sistema ↗</button>
        </div>
      </div>
    </section>
  `;
}
