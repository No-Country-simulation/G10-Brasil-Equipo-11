import { renderLandingHeader } from '../organisms/landing-header.js';
import { renderLandingHero } from '../organisms/landing-hero.js';
import { renderLandingContent } from '../organisms/landing-content.js';
import { renderLandingDemo } from '../organisms/landing-demo.js';
import { renderLandingFooter } from '../organisms/landing-footer.js';

function assegurarEstilos() {
  const fontes = 'https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&family=Outfit:wght@200;300;400;600;700;800&display=swap';
  if (!document.querySelector('link[href*="Outfit"]')) {
    const l = document.createElement('link'); l.rel = 'stylesheet'; l.href = fontes;
    document.head.appendChild(l);
  }
  const folhas = ['/css/00-tokens.css', '/css/01-reset.css', '/css/02-layout.css', '/css/03-landing.css', '/css/04-landing-sections.css'];
  folhas.forEach(f => {
    const nome = f.split('/').pop().replace('.css', '');
    if (!document.querySelector(`link[href*="${nome}"]`)) {
      const l = document.createElement('link'); l.rel = 'stylesheet'; l.href = `${f}?v=${Date.now()}`;
      document.head.appendChild(l);
    }
  });
}

export function renderLandingView() {
  assegurarEstilos();
  return `
    <div class="view-landing">
      ${renderLandingHeader()}
      <main>
        ${renderLandingHero()}
        ${renderLandingContent()}
        ${renderLandingDemo()}
        ${renderLandingFooter()}
      </main>
    </div>
  `;
}
