export function renderLandingHero() {
  return `
    <section class="lp-hero" id="inicio">
      <div class="lp-matrix-bg"></div>
      <div class="lp-flashlight-mask"></div>
      <div class="lp-cursor-glow"></div>

      <div class="lp-wrap lp-hero-grid">
        <div>
          <div class="lp-telemetry-bar">
            <div class="lp-eyebrow"><span class="lp-dot"></span> Radar de Comunidades Digitais</div>
            <span class="lp-coords-readout" id="coordsReadout">X: 0420 · Y: 0210</span>
          </div>
          <h1>
            <strong>Sinais ocultos no ruído</strong>
            Conversas que viram <em>oportunidades.</em>
          </h1>
          <p class="lp-lead">
            O Sender AI ilumina interações dispersas em comunidades digitais e transforma mensagens brutas em insights estruturados, alertas críticos e oportunidades acionáveis com revisão humana.
          </p>
          <div class="lp-hero-actions">
            <a class="lp-btn lime" href="#demonstracao">Explorar Telemetria <span>↓</span></a>
          </div>
        </div>

        <div class="lp-hero-art">
          <div class="lp-orbit"><i class="lp-orbit-dot"></i></div>
          <div class="lp-orbit-scanner"></div>
          <div class="lp-hero-bird" role="img" aria-label="Logo do Sender AI"><i></i></div>
          <div class="lp-floating-card fc1">
            <span class="lp-hud-tag">STREAM // INGESTÃO</span>
            <span class="lp-fc-label">Interações processadas</span>
            <strong id="heroCounter1">1.284</strong>
          </div>
          <div class="lp-floating-card fc2">
            <span class="lp-hud-tag">SINAL // DETECTADO</span>
            <span class="lp-fc-label">Oportunidades mapeadas</span>
            <strong id="heroCounter2">+ 36 <span style="font-size:12px;color:var(--accent)">↗</span></strong>
          </div>
        </div>
      </div>
    </section>
  `;
}
