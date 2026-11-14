// web/js/app.js
// Ponto de entrada, orquestrador reativo e controle de eventos
import { store } from './store.js';
import { api } from './api.js';
import { renderSidebar, initSidebarEvents } from './organisms/sidebar.js';
import { initThemeToggle } from './atoms/theme-toggle.js';
import { renderLandingView } from './views/landing-view.js';
import { initLandingEvents } from './organisms/landing-events.js';
import { renderLoginView } from './views/login-view.js';
import { renderImportView } from './views/import-view.js';
import { renderOverviewView } from './views/overview-view.js';
import { renderCurationView, extrairItensCuradoria } from './views/curation-view.js';
import { renderInsightsView } from './views/insights-view.js';
import { initInsightsEvents } from './insights-controller.js';
import { abrirLoteSalvo } from './lotes.js';
import { carregarVisaoGeral, tratarAlertaVisaoGeral } from './visao-geral.js';
import { primeiroLoteComAtivos } from './organisms/pending-batches.js';
import { abrirCuradoria, carregarFila, focar, proximoPendente, pacotesDosLotes } from './fila.js';

let lastRenderedView = null;

function executeRender(root, state) {
  const { activeTab, logado, publicView, theme, menuRecolhido, menuAberto } = state;

  if (!logado) {
    document.documentElement.setAttribute('data-theme', 'dark');
    root.innerHTML = publicView === 'login' ? renderLoginView() : renderLandingView();
    return;
  }

  document.documentElement.setAttribute('data-theme', theme || 'dark');

  const views = {
    importar: renderImportView,
    visao: renderOverviewView,
    curadoria: renderCurationView,
    insights: renderInsightsView,
  };

  const currentView = views[activeTab] || renderOverviewView;

  root.innerHTML = `
    <div class="app-shell com-sidebar${menuRecolhido ? ' recolhido' : ''}${menuAberto ? ' menu-aberto' : ''}">
      ${renderSidebar()}
      <main class="container">
        ${currentView()}
      </main>
    </div>
  `;
}

function renderApp() {
  const root = document.getElementById('app-root');
  if (!root) return;
  const state = store.getState();
  const currentViewKey = !state.logado ? state.publicView : `app-${state.activeTab}`;

  const viewChanged = lastRenderedView !== null && lastRenderedView !== currentViewKey;
  lastRenderedView = currentViewKey;

  if (viewChanged && document.startViewTransition && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    document.startViewTransition(() => {
      executeRender(root, state);
      window.scrollTo({ top: 0, behavior: 'instant' });
    });
  } else {
    executeRender(root, state);
    if (viewChanged) {
      window.scrollTo({ top: 0, behavior: 'instant' });
    }
  }
}

function initEventHandlers() {
  initSidebarEvents();
  initThemeToggle();
  initLandingEvents();

  document.addEventListener('click', async (e) => {
    // 0. Navegação Landing <-> Login
    if (e.target.closest('.btn-ir-login')) {
      store.setState({ publicView: 'login', authErro: null });
      return;
    }
    if (e.target.closest('#btn-voltar-landing')) {
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
        store.setState({ logado: true, usuario: res.usuario, authErro: null, activeTab: 'visao' });
        carregarVisaoGeral();
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

    // 0.1 Insights / Histórico: tratado em insights-controller.js

    // 1. Navegação rápida
    if (e.target.closest('#btn-go-importar')) {
      store.setState({ activeTab: 'importar' });
      return;
    }
    if (e.target.closest('#btn-ir-curadoria')) {
      // Revisar do topo: o lote mais antigo com ativo pendente (a lista já vem nessa ordem)
      const lote = primeiroLoteComAtivos(store.getState().visaoGeral.dados?.lotes_pendentes);
      await abrirCuradoria({ focoLoteId: lote ? lote.lote_id : null });
      return;
    }
    if (e.target.closest('#btn-ir-visao')) {
      store.setState({ activeTab: 'visao' });
      carregarVisaoGeral();
      return;
    }
    if (e.target.closest('#btn-atualizar-fila')) {
      carregarFila({ focoLoteId: store.getState().loteId });
      return;
    }
    if (e.target.closest('#btn-ver-todos-pendentes')) {
      carregarFila();
      return;
    }
    const btnRevisarLote = e.target.closest('.btn-revisar-lote');
    if (btnRevisarLote) {
      if (btnRevisarLote.dataset.destino === 'alertas') {
        document.getElementById('bloco-alertas')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      } else {
        await abrirCuradoria({ focoLoteId: btnRevisarLote.dataset.loteId });
      }
      return;
    }
    if (e.target.closest('#btn-atualizar-visao')) {
      carregarVisaoGeral();
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

    // 3a. Lote já processado: abrir o resultado guardado no banco
    if (e.target.closest('#btn-abrir-existente')) {
      const { duplicado } = store.getState();
      if (!duplicado) return;
      store.setState({ isProcessing: true });
      try {
        await abrirLoteSalvo(duplicado.lote_id);
      } catch (err) {
        alert('Falha ao abrir o resultado existente: ' + err.message);
        store.setState({ isProcessing: false });
      }
      return;
    }

    // 3. Processar Lote (o botão "processar de novo" pula o aviso de duplicado)
    const processarDeNovo = Boolean(e.target.closest('#btn-processar-de-novo'));
    if (processarDeNovo || e.target.closest('#btn-processar-lote')) {
      const { leitura, origem, periodo } = store.getState();
      if (!leitura || !leitura.lote) return;
      store.setState({ isProcessing: true });
      try {
        if (!processarDeNovo) {
          const existente = await api.verificarLote(leitura.lote.interacoes || []);
          if (existente) {
            // Guarda para qual arquivo o aviso vale: trocar o arquivo descarta o aviso.
            store.setState({ duplicado: { ...existente, lote: leitura.lote }, isProcessing: false });
            return;
          }
        }
        const payload = {
          ...leitura.lote,
          origem_comunidade: origem.trim() || leitura.lote.origem_comunidade,
          periodo_referencia: periodo.trim() || leitura.lote.periodo_referencia,
        };
        const resultado = await api.processarLote(payload, false, processarDeNovo);
        const itens = extrairItensCuradoria(resultado);
        const defaultDecisoes = {};
        itens.forEach(it => { defaultDecisoes[it.id] = 'p'; });

        store.setState({
          resultado,
          loteId: resultado.lote_id || null,
          processadoEm: new Date().toISOString(),
          decisoes: defaultDecisoes,
          activeItem: itens[0] ? itens[0].id : null,
          textosEditados: {},
          autorizado: false,
          alertas: {},
          activeTab: 'visao',
          isProcessing: false,
          duplicado: null,
          exportResult: null,
          exportErro: null,
        });
        carregarVisaoGeral();
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
      focar(queueBtn.dataset.loteId || store.getState().loteId, queueBtn.dataset.id);
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

    // 6. Exportar Aprovados: um lote por vez (cada lote tem o seu pacote no bucket)
    if (e.target.closest('#btn-exportar-aprovados')) {
      // Um clique por vez: o envio ao bucket leva alguns segundos.
      if (store.getState().isExporting) return;
      salvarTextosAtivos();
      const pacotes = pacotesDosLotes().filter(p => Object.values(p.decisoes).includes('a'));
      store.setState({ isExporting: true, exportResult: null, exportErro: null });
      const lotes = [];
      for (const pacote of pacotes) {
        const rotulo = `${(pacote.origem_comunidade || '').replace(/_/g, ' ')} · ${pacote.periodo_referencia || ''}`;
        try {
          const res = await api.exportarAprovados(pacote);
          lotes.push({ rotulo, ok: true, ja_exportado: Boolean(res.ja_exportado) });
        } catch (err) {
          lotes.push({ rotulo, ok: false, erro: err.message || 'Falha ao exportar.' });
        }
      }
      store.setState({ exportResult: { lotes }, isExporting: false });
      carregarVisaoGeral();
      return;
    }

    // 6b. Baixar os aprovados para o computador (PDF, CSV ou JSON)
    const btnBaixar = e.target.closest('.btn-baixar-aprovados');
    if (btnBaixar) {
      if (store.getState().baixando) return;
      const formato = btnBaixar.dataset.formato;
      salvarTextosAtivos();
      store.setState({ baixando: formato });
      try {
        const { blob, nome } = await api.baixarVarios(pacotesDosLotes(), formato);
        salvarNoComputador(blob, nome);
      } catch (err) {
        alert('Não foi possível baixar: ' + (err.message || 'falha ao gerar o arquivo.'));
      } finally {
        store.setState({ baixando: null });
      }
      return;
    }

    // 7. Filtro de Rotas na Tabela
    const filterBtn = e.target.closest('.btn-filter-route');
    if (filterBtn) {
      store.setState({ filtroRota: filterBtn.dataset.filter });
      return;
    }

    // 8. Tratar Alerta Humano: o card da Visão geral sabe o lote e a posição de origem
    const btnAlerta = e.target.closest('.btn-tratar-alerta, .btn-resolver-alerta');
    if (btnAlerta) {
      const { loteId, ordem, tipo } = btnAlerta.closest('.cl-alert-card')?.dataset || {};
      if (loteId && ordem !== undefined) {
        const resolver = btnAlerta.classList.contains('btn-resolver-alerta');
        const status = resolver ? 'resolvido' : (tipo === 'reclamacao' ? 'encaminhado' : 'mentoria_oferecida');
        tratarAlertaVisaoGeral(loteId, parseInt(ordem, 10), status);
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
      // Guarda antes o texto que a pessoa já editou: marcar a caixa redesenha a tela.
      salvarTextosAtivos();
      store.setState({ autorizado: e.target.checked });
    }
  });

  // Change events para selects e input de arquivo
  document.addEventListener('change', async (e) => {
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
      await importarArquivo(e.target.files[0]);
      e.target.value = ''; // permite escolher o mesmo arquivo de novo depois de corrigi-lo
    }
  });

  // Arrastar e soltar: delegado no documento porque a área é redesenhada a cada mudança de estado.
  const sobreDropzone = (e) => e.target instanceof Element && e.target.closest('#dropzone-area');
  const realcarDropzone = (ligado) => {
    const area = document.getElementById('dropzone-area');
    if (!area) return;
    area.style.borderColor = ligado ? 'var(--accent-lime)' : '';
    area.style.backgroundColor = ligado ? 'var(--bg-surface-2)' : '';
  };
  document.addEventListener('dragover', (e) => {
    if (!e.dataTransfer?.types?.includes('Files')) return;
    e.preventDefault(); // sem isso o navegador abre o arquivo em vez de entregá-lo à página
    e.dataTransfer.dropEffect = sobreDropzone(e) ? 'copy' : 'none';
    realcarDropzone(Boolean(sobreDropzone(e)));
  });
  document.addEventListener('dragleave', (e) => {
    if (!e.relatedTarget) realcarDropzone(false);
  });
  document.addEventListener('drop', async (e) => {
    if (!e.dataTransfer?.types?.includes('Files')) return;
    e.preventDefault();
    realcarDropzone(false);
    const file = e.dataTransfer.files?.[0];
    if (sobreDropzone(e) && file) await importarArquivo(file);
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
        store.setState({ logado: true, usuario: res.usuario, authErro: null, activeTab: 'visao' });
        carregarVisaoGeral();
      } catch (err) {
        store.setState({ authErro: err.message || 'Usuário ou senha inválidos.' });
      }
    }
  });
}

// Lê o arquivo escolhido ou solto na tela Importar. O backend faz a leitura, para o CSV e o
// JSON seguirem as mesmas regras (separador, acentos, colunas alternativas, autor anônimo).
async function importarArquivo(file) {
  const extensao = (file.name.split('.').pop() || '').toLowerCase();
  if (!['csv', 'json'].includes(extensao)) {
    alert(`O arquivo "${file.name}" não é CSV nem JSON.`);
    return;
  }
  try {
    const lido = await api.lerArquivo(file);
    const atual = store.getState();
    store.setState({
      arquivo: file,
      leitura: {
        nome: lido.nome,
        detalhe: `${Math.max(1, Math.round(file.size / 1024))} KB · ${lido.formato} (${lido.total} msgs)`,
        total: lido.total,
        anonimas: lido.anonimas,
        lote: lido.lote,
      },
      origem: lido.origem_do_arquivo ? lido.lote.origem_comunidade : atual.origem,
      periodo: lido.periodo_do_arquivo ? lido.lote.periodo_referencia : atual.periodo,
      duplicado: null,
    });
  } catch (err) {
    alert(`Não foi possível ler "${file.name}": ${err.message}`);
  }
}

// Entrega o arquivo ao navegador, que salva na pasta de downloads da pessoa.
function salvarNoComputador(blob, nome) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = nome;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
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
  const { activeItem, decisoes, loteId, textosEditados, autorizado } = store.getState();
  if (!activeItem) return;

  store.setState({
    decisoes: { ...decisoes, [activeItem]: decisao },
    // A decisão mudou: a mensagem da exportação anterior deixa de valer.
    exportResult: null,
    exportErro: null,
  });
  // Grava no lote do item, com os textos e a autorização dele, antes de trocar o foco.
  if (loteId) {
    api.salvarDecisao(loteId, activeItem, decisao, textosEditados, autorizado);
  }

  // Avança para o próximo pendente: no mesmo lote e depois nos seguintes.
  if (decisao !== 'p') {
    const proximo = proximoPendente();
    if (proximo) focar(proximo.loteId, proximo.itemId);
  }
}

// Inicialização
document.addEventListener('DOMContentLoaded', async () => {
  document.documentElement.setAttribute('data-theme', store.getState().theme);
  store.subscribe(renderApp);
  initEventHandlers();
  initInsightsEvents();

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
    if (auth.logado) carregarVisaoGeral();
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
