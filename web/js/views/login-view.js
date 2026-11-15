// web/js/views/login-view.js
// Tela de Login Administrativo Minimalista (< 75 linhas)
import { esc } from '../atoms/escape.js';
import { store } from '../store.js';

export function renderLoginView() {
  const { authConfigurado, authCarregando, authErro } = store.getState();

  return `
    <div class="view-login" style="min-height: 85vh; display: flex; flex-direction: column; justify-content: center; align-items: center; padding: 2rem 1rem;">

      <div style="width: 100%; max-width: 420px; margin-bottom: 0.75rem;">
        <button id="btn-voltar-landing" type="button" style="font-size: 13px; color: var(--muted); display: inline-flex; align-items: center; gap: 6px; padding: 4px 0;">
          ← Voltar ao início
        </button>
      </div>

      <div class="card" style="width: 100%; max-width: 420px; padding: 2.25rem 2rem; border-top: 3px solid var(--accent-lime-text); box-shadow: var(--shadow-card);">
        
        <!-- Logo e Título Limpos -->
        <div style="text-align: center; margin-bottom: 1.5rem;">
          <div role="img" aria-label="Sender AI" style="width: 42px; height: 42px; margin: 0 auto 0.75rem; background: var(--text); -webkit-mask: url('assets/logo_sender_ai.png') center / contain no-repeat; mask: url('assets/logo_sender_ai.png') center / contain no-repeat;"></div>
          <h1 class="page-title" style="font-size: 1.65rem; margin: 0;">Entrar</h1>
        </div>

        ${authCarregando ? `
          <div style="text-align: center; padding: 2rem; color: var(--muted); font-size: 14px;">
            <p>Verificando credenciais...</p>
          </div>
        ` : `
          ${!authConfigurado ? `
            <div style="background: var(--accent-amber-bg); border: 1px solid var(--accent-amber); border-radius: var(--radius-md); padding: 1rem; margin-bottom: 1.25rem; font-size: 13px; color: var(--text); line-height: 1.4;">
              <strong>⚠️ Login não configurado:</strong> defina <code style="font-family: var(--font-mono); color: var(--accent-lime-text);">ADMIN_USUARIO</code> e <code style="font-family: var(--font-mono); color: var(--accent-lime-text);">ADMIN_SENHA</code> no <code>.env</code> e reinicie o app.
            </div>
          ` : ''}

          ${authErro ? `
            <div id="login-error-box" style="background: var(--accent-coral-bg); border: 1px solid var(--accent-coral); border-radius: var(--radius-md); padding: 0.85rem 1rem; margin-bottom: 1.25rem; font-size: 13px; color: var(--text); display: flex; align-items: center; gap: 8px;">
              <span>⛔</span>
              <span>${esc(authErro)}</span>
            </div>
          ` : ''}

          <form id="form-login" onsubmit="return false;" style="display: flex; flex-direction: column; gap: 1rem;">
            <div>
              <label for="login_usuario" style="display: block; font-size: 13px; font-weight: 600; margin-bottom: 0.35rem; color: var(--text);">Usuário</label>
              <input 
                type="text" 
                id="login_usuario" 
                name="usuario" 
                autocomplete="username" 
                placeholder="Ex: admin"
                ${!authConfigurado ? 'disabled' : ''}
                style="width: 100%; padding: 0.65rem 0.85rem; border-radius: var(--radius-md); border: 1px solid var(--line); background: var(--bg-surface-2); color: var(--text); font-size: 14px;" 
              />
            </div>

            <div>
              <label for="login_senha" style="display: block; font-size: 13px; font-weight: 600; margin-bottom: 0.35rem; color: var(--text);">Senha</label>
              <input 
                type="password" 
                id="login_senha" 
                name="senha" 
                autocomplete="current-password" 
                placeholder="••••••••"
                ${!authConfigurado ? 'disabled' : ''}
                style="width: 100%; padding: 0.65rem 0.85rem; border-radius: var(--radius-md); border: 1px solid var(--line); background: var(--bg-surface-2); color: var(--text); font-size: 14px;" 
              />
            </div>

            <button 
              type="submit" 
              id="btn-login-submit" 
              ${!authConfigurado ? 'disabled style="opacity: 0.5; cursor: not-allowed;' : 'style="'}
              width: 100%; margin-top: 0.5rem; padding: 0.75rem 1rem; border-radius: var(--radius-md); font-size: 14px; font-weight: 600; background: var(--accent-lime); color: var(--accent-lime-ink); border: none; transition: filter var(--transition-fast);"
            >
              Entrar
            </button>
          </form>
        `}

      </div>
    </div>
  `.trim();
}
