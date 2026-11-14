// web/js/atoms/button.js
// Átomo: Botão com física de compressão mecânica (:active scale 0.97) (< 50 linhas)
import { esc } from './escape.js';

export function renderButton({
  id = '',
  text = '',
  variant = 'primary', // primary | secondary | danger | ghost
  disabled = false,
  extraClass = '',
  icon = '',
  fullWidth = false,
  data = {}, // atributos data-* ({ loteId: 'x' } vira data-lote-id="x")
}) {
  const baseStyle = `
    display: inline-flex; align-items: center; justify-content: center; gap: 8px;
    padding: 10px 18px; border-radius: var(--radius-md); font-size: 14px; font-weight: 600;
    cursor: ${disabled ? 'not-allowed' : 'pointer'}; opacity: ${disabled ? '0.45' : '1'};
    transition: transform var(--transition-fast), background-color var(--transition-fast), border-color var(--transition-fast);
    ${fullWidth ? 'width: 100%;' : ''}
  `;

  const variantStyles = {
    primary: `background: var(--accent-lime); color: var(--accent-lime-ink); border: 1px solid transparent;`,
    secondary: `background: var(--bg-surface-2); color: var(--text); border: 1px solid var(--line);`,
    danger: `background: var(--accent-coral-bg); color: var(--accent-coral); border: 1px solid var(--accent-coral);`,
    ghost: `background: transparent; color: var(--muted); border: 1px solid transparent;`,
  };

  const style = variantStyles[variant] || variantStyles.secondary;
  const idAttr = id ? `id="${esc(id)}"` : '';
  const disabledAttr = disabled ? 'disabled' : '';
  const dataAttrs = Object.entries(data)
    .map(([k, v]) => `data-${k.replace(/[A-Z]/g, c => '-' + c.toLowerCase())}="${esc(v)}"`)
    .join(' ');

  return `
    <button ${idAttr} class="cl-btn cl-btn-${esc(variant)} ${esc(extraClass)}" ${dataAttrs} ${disabledAttr} style="${baseStyle} ${style}">
      ${icon ? `<span class="cl-btn-icon">${icon}</span>` : ''}
      <span>${esc(text)}</span>
    </button>
  `.trim();
}
