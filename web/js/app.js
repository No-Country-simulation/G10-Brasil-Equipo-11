// web/js/app.js
// Ponto de entrada, orquestrador reativo e controle de eventos
import { store } from './store.js';
import { api } from './api.js';
import { renderHeaderBar, initHeaderEvents } from './organisms/header-bar.js';
import { initThemeToggle } from './atoms/theme-toggle.js';
import { renderLandingView } from './views/landing-view.js';
import { initLandingEvents } from './organisms/landing-events.js';
import { renderLoginView } from './views/login-view.js';
import { renderImportView } from './views/import-view.js';
import { renderOverviewView } from './views/overview-view.js';
import { renderCurationView, extrairItensCuradoria } from './views/curation-view.js';
import { renderInsightsView } from './views/insights-view.js';

function renderApp() {
  const root = document.getElementById('app-root');
  if (!root) return;
  const { activeTab, logado, publicView, theme } = store.getState();

  if (!logado) {
    document.documentElement.setAttribute('data-theme', 'dark');
    const isLogin = publicView === 'login';
    root.innerHTML = `
      <div class="landing-host ${isLogin ? 'landing-host-dimmed' : ''}">
        ${renderLandingView()}
      </div>
      ${isLogin ? `
        <div class="login-overlay" id="loginOverlayBackdrop">
          ${renderLoginView()}
        </div>
      ` : ''}
    `;
    return;
  }

  document.documentElement.setAttribute('data-theme', theme || 'dark');

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
  initLandingEvents();

  document.addEventListener('click', async (e) => {
    // 0. Navegação Landing <-> Login
    if (e.target.closest('.btn-ir-login')) {
      store.setState({ publicView: 'login', authErro: null });
      return;
    }
    if (e.target.closest('#btn-voltar-landing') || e.target.id === 'loginOverlayBackdrop') {
      store.setState({ publicView: 'landing', authErro: null });
      return;
    }

    // 0.1 Autenticação e Login
    if (e.target.closest('#btn-login-submit')) {
      const usuarioInput = document.getElementById('login_usuario');
      const senhaInput = document.getElementById('login_senha');
      const usuario = usuarioInput ? usuarioInput.value.trim() : '';
      const senha = senhaInput ? senhaInput.value : '';
      if (!usuario || !senha) {
        store.setState({ authErro: 'Por favor preencha usuário e senha.' });
        return;
      }
      try {
        const res = await api.login(usuario, senha);
        store.setState({ logado: true, usuario: res.usuario, authErro: null });
      } catch (err) {
        store.setState({ authErro: err.message || 'Usuário ou senha inválidos.' });
      }
      return;
    }

    if (e.target.closest('#btn-logout')) {
      try {
        await api.logout();
      } catch (err) {
        console.warn('Erro ao sair:', err);
      }
      store.resetSession();
      return;
    }

    // 0.1 Insights / Histórico
    if (e.target.closest('#btn-insights-load-demo') || e.target.closest('#btn-insights-refresh')) {
      store.setState({ insightsCarregando: true });
      try {
        const dados = await api.obterInsights({ demo: true });
        store.setState({ insightsData: dados, insightsCarregando: false, insightsModoDemo: true });
      } catch (err) {
        alert('Erro ao carregar insights: ' + err.message);
        store.setState({ insightsCarregando: false });
      }
      return;
    }

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
        const dados = await api.carregarExemplo('padrao');
        store.setState({
          arquivo: null,
          leitura: {
            nome: 'interacoes_exemplo.json',
            detalhe: '3 KB · JSON (12 msgs)',
            total: dados.interacoes.length,
            anonimas: dados.interacoes.filter(i => !i.autor).length,
            lote: dados,
          },
          fonte: 'Discord',
          canal: 'Grupo ONE G10',
          mes: 11,
          ano: 2026,
          origem: 'Discord · Grupo ONE G10',
          periodo: '2026-11',
        });
      } catch (err) {
        alert('Erro ao carregar exemplo: ' + err.message);
      }
      return;
    }

    if (e.target.closest('#btn-load-demo')) {
      try {
        const dados = await api.carregarExemplo('demo');
        store.setState({
          arquivo: null,
          leitura: {
            nome: 'interacoes_30out_02nov_2026.json',
            detalhe: '5 KB · JSON (20 msgs)',
            total: dados.interacoes.length,
            anonimas: dados.interacoes.filter(i => !i.autor).length,
            lote: dados,
          },
          fonte: 'Discord',
          canal: 'Grupo ONE G10',
          mes: 11,
          ano: 2026,
          origem: 'Discord · Grupo ONE G10',
          periodo: '2026-11',
        });
      } catch (err) {
        alert('Erro ao carregar lote de demonstração: ' + err.message);
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
          loteId: resultado.lote_id || null,
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
        resultado,
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
        const { resultado, loteId } = store.getState();
        const analise = resultado?.analises?.[parseInt(ordem, 10)];
        const novoStatus = analise?.tipo === 'reclamacao' ? 'encaminhado' : 'mentoria_oferecida';
        store.setState(s => ({ alertas: { ...s.alertas, [ordem]: novoStatus } }));
        if (loteId) {
          api.tratarAlerta(loteId, parseInt(ordem, 10), novoStatus);
        }
      }
      return;
    }
    const btnAlertaOk = e.target.closest('.btn-resolver-alerta');
    if (btnAlertaOk) {
      const card = btnAlertaOk.closest('.cl-alert-card');
      const ordem = card?.dataset.ordem;
      if (ordem !== undefined) {
        store.setState(s => ({ alertas: { ...s.alertas, [ordem]: 'resolvido' } }));
        const { loteId } = store.getState();
        if (loteId) {
          api.tratarAlerta(loteId, parseInt(ordem, 10), 'resolvido');
        }
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

  // Change events para selects e input de arquivo
  document.addEventListener('change', (e) => {
    if (e.target.id === 'select-fonte') {
      const novaFonte = e.target.value;
      const { fontesData, mes, ano } = store.getState();
      const canais = fontesData?.canais?.[novaFonte] || [];
      const novoCanal = canais[0] || '';
      store.setState({
        fonte: novaFonte,
        canal: novoCanal,
        origem: `${novaFonte} · ${novoCanal}`,
        periodo: `${ano}-${String(mes).padStart(2, '0')}`,
      });
      return;
    }
    if (e.target.id === 'select-canal') {
      const novoCanal = e.target.value;
      const { fonte, mes, ano } = store.getState();
      store.setState({
        canal: novoCanal,
        origem: `${fonte} · ${novoCanal}`,
        periodo: `${ano}-${String(mes).padStart(2, '0')}`,
      });
      return;
    }
    if (e.target.id === 'select-mes') {
      const novoMes = parseInt(e.target.value, 10);
      const { ano } = store.getState();
      store.setState({
        mes: novoMes,
        periodo: `${ano}-${String(novoMes).padStart(2, '0')}`,
      });
      return;
    }
    if (e.target.id === 'select-ano') {
      const novoAno = parseInt(e.target.value, 10);
      const { mes } = store.getState();
      store.setState({
        ano: novoAno,
        periodo: `${novoAno}-${String(mes).padStart(2, '0')}`,
      });
      return;
    }
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

  // Envio de formulário (ex: Enter no Login)
  document.addEventListener('submit', async (e) => {
    if (e.target.id === 'form-login') {
      e.preventDefault();
      const usuarioInput = document.getElementById('login_usuario');
      const senhaInput = document.getElementById('login_senha');
      const usuario = usuarioInput ? usuarioInput.value.trim() : '';
      const senha = senhaInput ? senhaInput.value : '';
      if (!usuario || !senha) {
        store.setState({ authErro: 'Por favor preencha usuário e senha.' });
        return;
      }
      try {
        const res = await api.login(usuario, senha);
        store.setState({ logado: true, usuario: res.usuario, authErro: null });
      } catch (err) {
        store.setState({ authErro: err.message || 'Usuário ou senha inválidos.' });
      }
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
  const { activeItem, decisoes, resultado, loteId, textosEditados, autorizado } = store.getState();
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

  if (loteId) {
    api.salvarDecisao(loteId, activeItem, decisao, textosEditados, autorizado);
  }
}

// Inicialização
document.addEventListener('DOMContentLoaded', async () => {
  document.documentElement.setAttribute('data-theme', store.getState().theme);
  store.subscribe(renderApp);
  initEventHandlers();

  // 1. Verifica saúde da API e autenticação de admin
  try {
    const saude = await api.verificarSaude();
    store.setState({ saudeInfo: saude });
  } catch (err) {
    console.warn('[Sender AI] /saude indisponível:', err);
  }
  try {
    const auth = await api.obterStatusAuth();
    store.setState({
      logado: Boolean(auth.logado),
      authConfigurado: Boolean(auth.configurado),
      authCarregando: false,
    });
  } catch (err) {
    console.warn('[Sender AI] Status de autenticação indisponível:', err);
    store.setState({ authCarregando: false });
  }

  // 2. Carrega fontes dinâmicas
  try {
    const dadosFontes = await api.obterFontes();
    if (dadosFontes && dadosFontes.canais) {
      store.setState({ fontesData: dadosFontes });
    }
  } catch (err) {
    console.warn('[Sender AI] Fontes dinâmicas não disponíveis:', err);
  }
  renderApp();
});
