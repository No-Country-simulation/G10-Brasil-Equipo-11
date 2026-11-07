// web/js/app.js
// Ponto de entrada, orquestrador reativo e controle de eventos (< 160 linhas)
import { store } from './store.js';
import { api } from './api.js';
import { renderHeaderBar, initHeaderEvents } from './organisms/header-bar.js';
import { initThemeToggle } from './atoms/theme-toggle.js';
import { renderImportView } from './views/import-view.js';
import { renderOverviewView } from './views/overview-view.js';
import { renderCurationView, extrairItensCuradoria } from './views/curation-view.js';
import { renderInsightsView } from './views/insights-view.js';

function renderApp() {
  const root = document.getElementById('app-root');
  if (!root) return;
  const { activeTab } = store.getState();

  const views = {
    importar: renderImportView,
    visao: renderOverviewView,
    curadoria: renderCurationView,
    insights: renderInsightsView,
  };

  const currentView = views[activeTab] || renderImportView;

  root.innerHTML = `
    <div class="app-shell">
      ${renderHeaderBar()}
      <main class="container">
        ${currentView()}
      </main>
    </div>
  `;
}

function initEventHandlers() {
  initHeaderEvents();
  initThemeToggle();

  document.addEventListener('click', async (e) => {
    // 1. Navegação rápida
    if (e.target.closest('#btn-go-importar')) {
      store.setState({ activeTab: 'importar' });
      return;
    }
    if (e.target.closest('#btn-ir-curadoria')) {
      store.setState({ activeTab: 'curadoria' });
      return;
    }

    // 2. Arquivo e Exemplo
    if (e.target.closest('#btn-browse-file')) {
      document.getElementById('file-input')?.click();
      return;
    }
    if (e.target.closest('#btn-load-example')) {
      try {
        const dados = await api.carregarExemplo();
        store.setState({
          arquivo: null,
          leitura: {
            nome: 'interacoes_exemplo.json',
            detalhe: '3 KB · JSON',
            total: dados.interacoes.length,
            anonimas: dados.interacoes.filter(i => !i.autor).length,
            lote: dados,
          },
          origem: dados.origem_comunidade || 'Discord_Grupo_ONE_G10',
          periodo: dados.periodo_referencia || 'Semana_04',
        });
      } catch (err) {
        alert('Erro ao carregar exemplo: ' + err.message);
      }
      return;
    }

    // 3. Processar Lote
    if (e.target.closest('#btn-processar-lote')) {
      const { leitura, origem, periodo } = store.getState();
      if (!leitura || !leitura.lote) return;
      store.setState({ isProcessing: true });
      try {
        const payload = {
          ...leitura.lote,
          origem_comunidade: origem.trim() || leitura.lote.origem_comunidade,
          periodo_referencia: periodo.trim() || leitura.lote.periodo_referencia,
        };
        const resultado = await api.processarLote(payload);
        const itens = extrairItensCuradoria(resultado);
        const defaultDecisoes = {};
        itens.forEach(it => { defaultDecisoes[it.id] = 'p'; });

        store.setState({
          resultado,
          processadoEm: new Date().toISOString(),
          decisoes: defaultDecisoes,
          activeItem: itens[0] ? itens[0].id : null,
          activeTab: 'visao',
          isProcessing: false,
          exportResult: null,
        });
      } catch (err) {
        alert('Falha ao processar: ' + err.message);
        store.setState({ isProcessing: false });
      }
      return;
    }

    // 4. Seleção de Item na Fila de Curadoria
    const queueBtn = e.target.closest('.btn-queue-item');
    if (queueBtn) {
      salvarTextosAtivos();
      store.setState({ activeItem: queueBtn.dataset.id });
      return;
    }

    // 5. Decisões de Curadoria (Aprovar / Descartar / Desfazer)
    if (e.target.closest('#btn-aprovar-ativo')) {
      salvarTextosAtivos();
      decidirAtivo('a');
      return;
    }
    if (e.target.closest('#btn-descartar-ativo')) {
      salvarTextosAtivos();
      decidirAtivo('d');
      return;
    }
    if (e.target.closest('#btn-desfazer-decisao')) {
      decidirAtivo('p');
      return;
    }

    // 6. Exportar Aprovados
    if (e.target.closest('#btn-exportar-aprovados')) {
      const { resultado, decisoes, textosEditados, origem, periodo, autorizado } = store.getState();
      const payload = {
        origem_comunidade: origem,
        periodo_referencia: periodo,
        aprovado_em: new Date().toISOString(),
        decisoes,
        textos: textosEditados,
        autorizado,
      };
      try {
        const res = await api.exportarAprovados(payload);
        store.setState({ exportResult: res });
      } catch (err) {
        alert('Erro ao exportar: ' + err.message);
      }
      return;
    }

    // 7. Filtro de Rotas na Tabela
    const filterBtn = e.target.closest('.btn-filter-route');
    if (filterBtn) {
      store.setState({ filtroRota: filterBtn.dataset.filter });
      return;
    }

    // 8. Tratar Alerta Humano
    const btnAlertaAcao = e.target.closest('.btn-tratar-alerta');
    if (btnAlertaAcao) {
      const card = btnAlertaAcao.closest('.cl-alert-card');
      const ordem = card?.dataset.ordem;
      if (ordem !== undefined) {
        store.setState(s => ({ alertas: { ...s.alertas, [ordem]: 'mentoria_oferecida' } }));
      }
      return;
    }
    const btnAlertaOk = e.target.closest('.btn-resolver-alerta');
    if (btnAlertaOk) {
      const card = btnAlertaOk.closest('.cl-alert-card');
      const ordem = card?.dataset.ordem;
      if (ordem !== undefined) {
        store.setState(s => ({ alertas: { ...s.alertas, [ordem]: 'resolvido' } }));
      }
      return;
    }
  });

  // Inputs de formulário
  document.addEventListener('input', (e) => {
    if (e.target.id === 'input-origem') {
      store.setState({ origem: e.target.value });
    }
    if (e.target.id === 'input-periodo') {
      store.setState({ periodo: e.target.value });
    }
    if (e.target.id === 'chk_autorizado') {
      store.setState({ autorizado: e.target.checked });
    }
  });

  // Input de Arquivo
  document.addEventListener('change', (e) => {
    if (e.target.id === 'file-input' && e.target.files?.[0]) {
      const file = e.target.files[0];
      const reader = new FileReader();
      reader.onload = (evt) => {
        try {
          const json = JSON.parse(evt.target.result);
          store.setState({
            arquivo: file,
            leitura: {
              nome: file.name,
              detalhe: `${Math.round(file.size / 1024)} KB · JSON`,
              total: json.interacoes?.length || 0,
              anonimas: json.interacoes?.filter(i => !i.autor).length || 0,
              lote: json,
            },
            origem: json.origem_comunidade || store.getState().origem,
            periodo: json.periodo_referencia || store.getState().periodo,
          });
        } catch {
          alert('Por favor envie um arquivo JSON ou CSV válido.');
        }
      };
      reader.readAsText(file);
    }
  });
}

function salvarTextosAtivos() {
  const patch = {};
  const txtPost = document.getElementById('txt_post_copy');
  if (txtPost) patch.post_copy = txtPost.value;

  const txtNewsChamada = document.getElementById('txt_news_chamada');
  if (txtNewsChamada) patch.news_chamada = txtNewsChamada.value;

  const txtNewsResumo = document.getElementById('txt_news_resumo');
  if (txtNewsResumo) patch.news_resumo = txtNewsResumo.value;

  document.querySelectorAll('[id^="txt_faq_"]').forEach(el => {
    const key = el.id.replace('txt_', '');
    patch[key] = el.value;
  });

  if (Object.keys(patch).length > 0) {
    store.setState(s => ({ textosEditados: { ...s.textosEditados, ...patch } }));
  }
}

function decidirAtivo(decisao) {
  const { activeItem, decisoes, resultado } = store.getState();
  if (!activeItem) return;

  const nextDecisoes = { ...decisoes, [activeItem]: decisao };
  const itens = extrairItensCuradoria(resultado);
  const ids = itens.map(i => i.id);

  // Avança para o próximo pendente
  let proximo = null;
  const currIndex = ids.indexOf(activeItem);
  for (let offset = 1; offset <= ids.length; offset++) {
    const candidate = ids[(currIndex + offset) % ids.length];
    if (nextDecisoes[candidate] === 'p') {
      proximo = candidate;
      break;
    }
  }

  store.setState({
    decisoes: nextDecisoes,
    activeItem: proximo || activeItem,
  });
}

// Inicialização
document.addEventListener('DOMContentLoaded', () => {
  document.documentElement.setAttribute('data-theme', store.getState().theme);
  store.subscribe(renderApp);
  initEventHandlers();
  renderApp();
});
