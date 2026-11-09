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
          <svg class="lp-hero-bird" width="370" height="256" viewBox="0 0 520 360" role="img" aria-label="Ilustração do pássaro Sender AI em pleno voo">
            <path fill="var(--text)" d="M28 242C104 182 158 117 192 35c-2 73 28 116 78 128 47 11 98-13 211-102-51 83-103 141-171 166-55 20-102 12-146-9L28 242Z"/>
            <path fill="var(--accent)" d="M211 218C146 250 89 293 25 337c99-27 172-51 239-92l-53-27Z"/>
            <path fill="var(--text)" d="M243 163c41-36 72-54 108-50 34 3 66 25 105 7-27 35-65 54-111 52-38-1-69-5-102-9Z"/>
            <path fill="var(--bg)" d="M270 163c24-16 46-22 69-19-16 12-32 19-54 22Z"/>
          </svg>
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
