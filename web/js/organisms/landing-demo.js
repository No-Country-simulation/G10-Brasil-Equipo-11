export function renderLandingDemo() {
  return `
    <section class="lp-section" id="demonstracao">
      <div class="lp-wrap">
        <div class="lp-section-head">
          <div>
            <div class="lp-kicker">03 // Console Operacional</div>
            <h2>Telemetria em tempo real da sua comunidade.</h2>
          </div>
          <p>Interaja com os filtros de período, explore os sinais semanais ou entre no console operacional conectado ao backend Python.</p>
        </div>

        <div class="lp-dashboard">
          <div class="lp-dash-top">
            <div class="lp-dash-brand">
              <span style="color:var(--accent)">◈</span> SENDER_AI // <span id="activeTabTitle" style="color:var(--muted)">TELEMETRIA_GERAL</span>
            </div>
            <div class="lp-dash-controls">
              <button type="button" class="lp-btn-upload btn-ir-login" id="btn-landing-entrar-demo">Entrar ↗</button>
              <span class="lp-live">● ENGINE ONLINE</span>
            </div>
          </div>

          <div class="lp-dash-body">
            <aside class="lp-sidebar">
              <div>
                <button type="button" class="lp-side-item active" data-view="geral"><span>▦ &nbsp; Visão geral</span><span class="lp-side-badge">LIVE</span></button>
                <button type="button" class="lp-side-item" data-view="interacoes"><span>⌁ &nbsp; Interações</span><span class="lp-side-badge" id="sideCountInteractions">1.284</span></button>
                <button type="button" class="lp-side-item" data-view="oportunidades"><span>✧ &nbsp; Oportunidades</span><span class="lp-side-badge" id="sideCountOpps">36</span></button>
                <button type="button" class="lp-side-item" data-view="curadoria"><span>✓ &nbsp; Curadoria</span><span class="lp-side-badge" id="sideCountPending">12</span></button>
              </div>
              <div class="lp-api-box"><strong>ENDPOINT PYTHON</strong>POST /api/processar-lote<br><span id="apiStatusText">Status: 200 OK (18ms)</span></div>
            </aside>

            <div class="lp-dash-main">
              <div class="lp-dash-title">
                <h3 id="dashHeading">Resumo Analítico da Comunidade</h3>
                <div class="lp-period-filters">
                  <button type="button" class="lp-period-btn" data-period="7d">7 DIAS</button>
                  <button type="button" class="lp-period-btn active" data-period="30d">30 DIAS</button>
                  <button type="button" class="lp-period-btn" data-period="90d">90 DIAS</button>
                </div>
              </div>

              <div class="lp-metrics">
                <div class="lp-metric"><small>Interações analisadas</small><strong id="mInteractions">1.284</strong><span class="trend" id="tInteractions">↑ 12,8% no período</span></div>
                <div class="lp-metric"><small>Sentimento positivo</small><strong id="mSentiment">68%</strong><span class="trend" id="tSentiment">↑ 4,2% no período</span></div>
                <div class="lp-metric"><small>Oportunidades</small><strong id="mOpps">36</strong><span class="trend" id="tOpps">↑ 8 identificadas</span></div>
                <div class="lp-metric"><small>Fila de Curadoria</small><strong id="mPending">12</strong><span class="trend" style="color:var(--warning)">Aguardando revisão</span></div>
              </div>

              <div class="lp-dash-lower">
                <div class="lp-panel">
                  <h4><span>Volume Semanal de Sinais</span><span style="color:var(--accent-cyan)">CLIQUE NAS BARRAS</span></h4>
                  <div class="lp-bars" id="barsContainer">
                    <div class="lp-bar-col" data-day="Segunda" data-val="142"><div class="lp-bar" style="height:42%"></div><span>Seg</span></div>
                    <div class="lp-bar-col" data-day="Terça" data-val="218"><div class="lp-bar" style="height:65%"></div><span>Ter</span></div>
                    <div class="lp-bar-col" data-day="Quarta" data-val="176"><div class="lp-bar" style="height:52%"></div><span>Qua</span></div>
                    <div class="lp-bar-col" data-day="Quinta" data-val="312"><div class="lp-bar peak" style="height:88%"></div><span>Qui</span></div>
                    <div class="lp-bar-col" data-day="Sexta" data-val="245"><div class="lp-bar" style="height:72%"></div><span>Sex</span></div>
                    <div class="lp-bar-col" data-day="Sábado" data-val="114"><div class="lp-bar" style="height:57%"></div><span>Sáb</span></div>
                    <div class="lp-bar-col" data-day="Domingo" data-val="77"><div class="lp-bar" style="height:35%"></div><span>Dom</span></div>
                  </div>
                </div>

                <div class="lp-panel">
                  <h4><span>Polaridade & Sentimento</span><span>NLP MODEL</span></h4>
                  <div class="lp-sentiment-row"><span>Positivo</span><div class="lp-track"><div class="lp-fill" id="barPos" style="width:68%"></div></div><b id="lblPos">68%</b></div>
                  <div class="lp-sentiment-row"><span>Neutro</span><div class="lp-track"><div class="lp-fill neutral" id="barNeu" style="width:22%"></div></div><b id="lblNeu">22%</b></div>
                  <div class="lp-sentiment-row"><span>Crítico</span><div class="lp-track"><div class="lp-fill negative" id="barNeg" style="width:10%"></div></div><b id="lblNeg">10%</b></div>
                </div>
              </div>

              <div class="lp-curation-list" id="curationList">
                <div class="lp-alert">
                  <div class="lp-alert-left"><span class="lp-alert-icon">!</span><div><strong>Alerta de Acesso & Autenticação</strong>Relatos de lentidão no login OAuth cresceram 18% nas últimas 24h.</div></div>
                  <div class="lp-alert-actions"><button type="button" class="lp-mini-btn approve" data-action="Alerta escalado para Engenharia">Escalar</button><button type="button" class="lp-mini-btn dismiss" data-action="Alerta arquivado">✕</button></div>
                </div>
                <div class="lp-alert">
                  <div class="lp-alert-left"><span class="lp-alert-icon">✧</span><div><strong>Oportunidade de Conteúdo Técnico</strong>14 membros pediram exemplos de integração com Python + Webhooks.</div></div>
                  <div class="lp-alert-actions"><button type="button" class="lp-mini-btn approve" data-action="Pauta aprovada para Newsletter">Gerar Pauta</button><button type="button" class="lp-mini-btn dismiss" data-action="Sugestão descartada">✕</button></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  `;
}
