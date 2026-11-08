import { renderLandingHeader } from '../organisms/landing-header.js';
import { renderLandingHero } from '../organisms/landing-hero.js';
import { renderLandingContent } from '../organisms/landing-content.js';
import { renderLandingDemo } from '../organisms/landing-demo.js';
import { renderLandingFooter } from '../organisms/landing-footer.js';

export function renderLandingView() {
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
