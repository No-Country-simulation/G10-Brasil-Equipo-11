// web/js/views/landing-view.js
// View Pública: Landing Page Oficial do Sender AI (< 35 linhas)
import { renderLandingHeader } from '../organisms/landing-header.js';
import { renderLandingHero } from '../organisms/landing-hero.js';
import { renderLandingContent } from '../organisms/landing-content.js';

export function renderLandingView() {
  return `
    <div class="view-landing">
      ${renderLandingHeader()}
      <main>
        ${renderLandingHero()}
        ${renderLandingContent()}
      </main>
    </div>
  `.trim();
}
