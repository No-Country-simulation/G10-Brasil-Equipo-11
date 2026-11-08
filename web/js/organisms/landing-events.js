const PERIOD_DATA = {
  '7d': { int: '342', tInt: '↑ 19,4% nos 7 dias', sent: '74%', tSent: '↑ 6,1% nos 7 dias', opps: '11', tOpps: '↑ 4 novas hoje', pend: '4', pos: 74, neu: 19, neg: 7, bars: [55, 78, 64, 92, 80, 48, 30] },
  '30d': { int: '1.284', tInt: '↑ 12,8% no período', sent: '68%', tSent: '↑ 4,2% no período', opps: '36', tOpps: '↑ 8 identificadas', pend: '12', pos: 68, neu: 22, neg: 10, bars: [42, 65, 52, 88, 72, 57, 35] },
  '90d': { int: '4.890', tInt: '↑ 31,0% no trimestre', sent: '71%', tSent: '↑ 8,5% no trimestre', opps: '104', tOpps: '↑ 29 convertidas', pend: '19', pos: 71, neu: 20, neg: 9, bars: [60, 70, 68, 95, 84, 62, 49] }
};

export function initLandingEvents() {
  let flashlightActive = true;
  const showToast = (msg) => {
    const t = document.getElementById('lpToast');
    if (!t) return;
    t.textContent = msg;
    t.classList.add('show');
    clearTimeout(window._lpToastTimer);
    window._lpToastTimer = setTimeout(() => t.classList.remove('show'), 3200);
  };

  document.addEventListener('pointermove', (e) => {
    if (!flashlightActive) return;
    const hero = document.getElementById('inicio');
    if (!hero) return;
    const rect = hero.getBoundingClientRect();
    const x = Math.round(e.clientX - rect.left);
    const y = Math.round(e.clientY - rect.top);
    hero.style.setProperty('--mouse-x', `${x}px`);
    hero.style.setProperty('--mouse-y', `${y}px`);
    const coords = document.getElementById('coordsReadout');
    if (coords && y >= 0 && y <= rect.height) {
      coords.textContent = `X: ${String(Math.max(0, x)).padStart(4, '0')} · Y: ${String(Math.max(0, y)).padStart(4, '0')}`;
    }
  });

  document.addEventListener('click', (e) => {
    const toggle = e.target.closest('#flashlightToggle');
    if (toggle) {
      flashlightActive = !flashlightActive;
      document.querySelector('.view-landing')?.classList.toggle('flashlight-off', !flashlightActive);
      toggle.classList.toggle('active', flashlightActive);
      const lbl = document.getElementById('flashlightLabel');
      if (lbl) lbl.textContent = flashlightActive ? 'FEIXE: ON' : 'FEIXE: OFF';
      showToast(flashlightActive ? 'Feixe de inspeção ativado (60 FPS)' : 'Feixe de inspeção desativado');
    }

    const pBtn = e.target.closest('.lp-period-btn');
    if (pBtn && PERIOD_DATA[pBtn.dataset.period]) {
      document.querySelectorAll('.lp-period-btn').forEach(b => b.classList.remove('active'));
      pBtn.classList.add('active');
      const d = PERIOD_DATA[pBtn.dataset.period];
      const setTxt = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v; };
      setTxt('mInteractions', d.int);
      setTxt('tInteractions', d.tInt);
      setTxt('mSentiment', d.sent);
      setTxt('tSentiment', d.tSent);
      setTxt('mOpps', d.opps);
      setTxt('tOpps', d.tOpps);
      setTxt('mPending', d.pend);
      setTxt('lblPos', `${d.pos}%`);
      setTxt('lblNeu', `${d.neu}%`);
      setTxt('lblNeg', `${d.neg}%`);
      document.getElementById('barPos')?.style.setProperty('width', `${d.pos}%`);
      document.getElementById('barNeu')?.style.setProperty('width', `${d.neu}%`);
      document.getElementById('barNeg')?.style.setProperty('width', `${d.neg}%`);
      document.querySelectorAll('#barsContainer .lp-bar').forEach((b, i) => { b.style.height = `${d.bars[i]}%`; });
      showToast(`Janela de telemetria ajustada: ${pBtn.textContent}`);
    }

    const barCol = e.target.closest('.lp-bar-col');
    if (barCol) showToast(`${barCol.dataset.day}: ${barCol.dataset.val} mensagens processadas pelo motor NLP.`);

    const sideItem = e.target.closest('.lp-side-item');
    if (sideItem) {
      document.querySelectorAll('.lp-side-item').forEach(i => i.classList.remove('active'));
      sideItem.classList.add('active');
      const title = document.getElementById('activeTabTitle');
      if (title) title.textContent = `MODO_${sideItem.dataset.view.toUpperCase()}`;
      showToast(`Alternado para visualização: ${sideItem.dataset.view.toUpperCase()}`);
    }

    const miniBtn = e.target.closest('.lp-mini-btn');
    if (miniBtn) {
      const card = miniBtn.closest('.lp-alert');
      if (card) { card.style.opacity = '0.35'; setTimeout(() => card.remove(), 300); }
      const pendingEl = document.getElementById('mPending');
      const sidePending = document.getElementById('sideCountPending');
      if (pendingEl) {
        const next = Math.max(0, parseInt(pendingEl.textContent, 10) - 1);
        pendingEl.textContent = next;
        if (sidePending) sidePending.textContent = next;
      }
      showToast(`✓ ${miniBtn.dataset.action}`);
    }
  });
}
