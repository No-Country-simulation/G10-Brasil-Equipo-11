// web/js/store.js
// Gerenciador de estado reativo unificado em Vanilla JS (< 80 linhas)

export class Store {
  constructor(initialState = {}) {
    this.state = {
      theme: localStorage.getItem('sender_ai_theme') || (window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark'),
      activeTab: 'importar',
      arquivo: null,
      leitura: null,
      resultado: null,
      processadoEm: null,
      fonte: 'Discord',
      canal: 'Grupo ONE G10',
      mes: 11,
      ano: 2026,
      fontesData: {
        canais: {
          'Discord': ['Grupo ONE G10', 'Dev Brasil'],
          'Telegram': ['Comunidade Python BR', 'Vagas Tech'],
          'WhatsApp': ['Mentoria G10', 'Alunos ONE'],
          'Arquivo manual': ['Pesquisa de satisfação', 'Formulário de eventos'],
        },
        meses: ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'],
        anos: [2024, 2025, 2026],
      },
      origem: 'Discord · Grupo ONE G10',
      periodo: '2026-11',
      decisoes: {},
      activeItem: null,
      textosEditados: {},
      autorizado: false,
      alertas: {},
      filtroRota: 'Todas',
      isProcessing: false,
      aviso: null,
      ...initialState,
    };
    this.listeners = new Set();
  }

  getState() {
    return this.state;
  }

  setState(patch) {
    const next = typeof patch === 'function' ? patch(this.state) : patch;
    this.state = { ...this.state, ...next };
    if (patch.theme) {
      localStorage.setItem('sender_ai_theme', this.state.theme);
      document.documentElement.setAttribute('data-theme', this.state.theme);
    }
    this.notify();
  }

  subscribe(listener) {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  notify() {
    this.listeners.forEach((fn) => {
      try {
        fn(this.state);
      } catch (err) {
        console.error('[Store] Erro ao notificar listener:', err);
      }
    });
  }
}

export const store = new Store();
