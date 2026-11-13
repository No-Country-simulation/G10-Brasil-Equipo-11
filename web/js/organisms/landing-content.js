export function renderLandingContent() {
  return `
    <section class="lp-section lp-problem" id="solucao">
      <div class="lp-wrap">
        <div class="lp-section-head">
          <div>
            <div class="lp-kicker">01 // O Desafio</div>
            <h2>O valor está nas conversas. Encontrá-lo não deveria ser difícil.</h2>
          </div>
          <p>Comunidades geram conhecimento o tempo todo. Sem telemetria, sinais vitais de produto e engajamento se perdem no volume de mensagens.</p>
        </div>
        <div class="lp-cards">
          <article class="lp-card">
            <span class="num">01 / SOBRECARGA DE CANAL</span>
            <div class="lp-card-icon">▤</div>
            <h3>Informação dispersa</h3>
            <p>Mensagens, dúvidas técnicas e sugestões valiosas ficam fragmentadas em dezenas de threads e canais paralelos.</p>
          </article>
          <article class="lp-card">
            <span class="num">02 / BAIXA VISIBILIDADE</span>
            <div class="lp-card-icon">⌕</div>
            <h3>Sinais difíceis de perceber</h3>
            <p>Padrões recorrentes, gargalos de onboarding e oportunidades de conteúdo passam despercebidos no ruído diário.</p>
          </article>
          <article class="lp-card">
            <span class="num">03 / TRABALHO MANUAL</span>
            <div class="lp-card-icon">◷</div>
            <h3>Curadoria demorada</h3>
            <p>Classificar conversas manualmente consome horas de engenharia e suporte que deveriam ser dedicadas à comunidade.</p>
          </article>
        </div>
      </div>
    </section>

    <section class="lp-section" id="como-funciona">
      <div class="lp-wrap">
        <div class="lp-section-head">
          <div>
            <div class="lp-kicker">02 // Pipeline Inteligente</div>
            <h2>Da interação bruta à decisão, em quatro etapas.</h2>
          </div>
          <p>Arquitetura enxuta pronta para receber payloads JSON/CSV e processar via backend em Python.</p>
        </div>
        <div class="lp-steps">
          <div class="lp-step">
            <b>01 — INGESTÃO</b>
            <h3>Importe interações</h3>
            <p>Envie arquivos CSV, JSON ou conecte webhooks com o histórico das conversas da sua comunidade.</p>
          </div>
          <div class="lp-step">
            <b>02 — INFERÊNCIA IA</b>
            <h3>Classifique com precisão</h3>
            <p>O motor em Python extrai sentimento, cluster de tema, urgência e rota sugerida automaticamente.</p>
          </div>
          <div class="lp-step">
            <b>03 — DESCOBERTA</b>
            <h3>Mapeie oportunidades</h3>
            <p>Visualize picos de interesse, dúvidas frequentes e incidentes antes que virem chamados críticos.</p>
          </div>
          <div class="lp-step">
            <b>04 — GOVERNANÇA</b>
            <h3>Curadoria humana</h3>
            <p>Aprove, edite ou descarte sugestões da IA com rastreabilidade total antes de qualquer disparo.</p>
          </div>
        </div>
      </div>
    </section>
  `;
}
