import { initAppDemo } from '../demo/app-demo.js';

export function initLandingEvents() {
  // O painel da seção 03 é o app real em modo demonstração: ver js/demo/app-demo.js.
  initAppDemo();

  document.addEventListener('pointermove', (e) => {
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
}
