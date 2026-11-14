// web/js/demo/estado-demo.js
// A demonstração da landing desenha os componentes reais do app, que leem o store global.
// Estas funções trocam o estado do store só durante uma chamada síncrona e devolvem o real logo depois.
import { store } from '../store.js';

// Desenha com o estado da demo por cima do real. Nada é notificado.
export function renderizarComEstado(estado, fn) {
  const real = store.state;
  store.state = { ...real, ...estado };
  try {
    return fn();
  } finally {
    store.state = real;
  }
}

// Roda lógica do app (ex.: fila.js) sobre o estado da demo, com os ouvintes do store desligados,
// e devolve o estado resultante. O estado e os ouvintes reais voltam no finally.
export function executarComEstado(estado, fn) {
  const real = store.state;
  const ouvintes = store.listeners;
  store.listeners = new Set();
  store.state = { ...real, ...estado };
  try {
    fn();
    return store.state;
  } finally {
    store.state = real;
    store.listeners = ouvintes;
  }
}
