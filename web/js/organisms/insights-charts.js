// web/js/organisms/insights-charts.js
// Gráficos da tela Insights, em HTML/CSS puro. Cada gráfico tem dica ao passar o mouse
// (ou ao focar com o teclado) e uma tabela equivalente em "Ver tabela".
// Regras de cor: sentimento é divergente (laranja/vermelho x azul, neutro cinza no meio);
// volume usa um tom só; estados (alerta, curadoria) sempre levam ícone + rótulo.
import { esc } from '../atoms/escape.js';

const fmt = (n) => Number(n || 0).toLocaleString('pt-BR');
const pctTxt = (n) => `${Number(n || 0).toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`;

// Do negativo ao positivo: a ordem das legendas e das pilhas.
export const SENTIMENTOS = [
  { chave: 'Altamente Negativo', nome: 'Muito negativo', cor: 'var(--sent-neg2)' },
  { chave: 'Negativo', nome: 'Negativo', cor: 'var(--sent-neg1)' },
  { chave: 'Neutro', nome: 'Neutro', cor: 'var(--sent-neu)' },
  { chave: 'Positivo', nome: 'Positivo', cor: 'var(--sent-pos1)' },
  { chave: 'Altamente Positivo', nome: 'Muito positivo', cor: 'var(--sent-pos2)' },
];
const TOM = [
  { chave: 'negativos', nome: 'Negativas', cor: 'var(--sent-neg1)' },
  { chave: 'neutros', nome: 'Neutras', cor: 'var(--sent-neu)' },
  { chave: 'positivos', nome: 'Positivas', cor: 'var(--sent-pos1)' },
];

// Dica: título + linhas (cor, valor, rótulo). O controlador monta o DOM com textContent.
function dica(titulo, linhas = [], extra = '') {
  const dados = JSON.stringify({ t: titulo, l: linhas, e: extra });
  return `data-dica="${esc(dados)}" tabindex="0"`;
}

function legenda(itens) {
  return `<div class="ins-legenda" aria-hidden="true">${itens
    .map(i => `<span><i style="background:${i.cor}"></i>${esc(i.nome)}</span>`).join('')}</div>`;
}

function tabela(id, cabecalho, linhas) {
  if (!linhas.length) return '';
  return `
    <details class="ins-tabela" data-detalhe="${esc(id)}">
      <summary>Ver tabela</summary>
      <div class="ins-tabela-scroll">
        <table>
          <thead><tr>${cabecalho.map(c => `<th scope="col">${esc(c)}</th>`).join('')}</tr></thead>
          <tbody>${linhas.map(l => `<tr>${l.map((c, i) => i === 0
            ? `<th scope="row" style="font-weight:500; color:var(--text);">${esc(c)}</th>`
            : `<td>${esc(c)}</td>`).join('')}</tr>`).join('')}</tbody>
        </table>
      </div>
    </details>`;
}

function vazio(texto) {
  return `<p class="ins-vazio">${esc(texto)}</p>`;
}

function cartao({ titulo, legenda: subtitulo, corpo }) {
  return `
    <section class="card ins-card">
      <h3 class="card-title">${esc(titulo)}</h3>
      ${subtitulo ? `<p class="card-caption">${esc(subtitulo)}</p>` : ''}
      ${corpo}
    </section>`;
}

// Teto "redondo" para o eixo (1, 2, 5, 10, 20, 50...).
function tetoRedondo(v) {
  if (v <= 1) return 1;
  const base = 10 ** Math.floor(Math.log10(v));
  for (const m of [1, 2, 5, 10]) if (v <= m * base) return m * base;
  return 10 * base;
}

// ---------------------------------------------------------------------------
// KPIs
// ---------------------------------------------------------------------------
export function renderResumo(r = {}) {
  const saldo = Number(r.saldo || 0);
  const saldoTxt = `${saldo > 0 ? '+' : saldo < 0 ? '−' : ''}${Math.abs(saldo).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} p.p.`;
  const tile = (rotulo, valor, nota, extra = '') => `
    <div class="card ins-kpi">
      <div class="ins-kpi-rotulo">${esc(rotulo)}</div>
      <div class="ins-kpi-valor">${esc(valor)}</div>
      ${extra}
      <div class="ins-kpi-nota">${esc(nota)}</div>
    </div>`;
  return `
    <div class="grid-4" style="margin-bottom:1.25rem;">
      ${tile('Interações analisadas', fmt(r.interacoes),
        `${fmt(r.lotes)} ${r.lotes === 1 ? 'lote' : 'lotes'} · ${fmt(r.canais)} ${r.canais === 1 ? 'canal' : 'canais'}`)}
      ${tile('Saldo de sentimento', saldoTxt,
        `${pctTxt(r.pct_positivas)} positivas menos ${pctTxt(r.pct_negativas)} negativas`)}
      ${tile('Alertas em aberto', fmt(r.alertas_abertos),
        `de ${fmt(r.alertas_total)} ${r.alertas_total === 1 ? 'alerta' : 'alertas'} no período`,
        r.alertas_abertos > 0 ? '<div class="ins-kpi-alerta">Precisa de triagem</div>' : '')}
      ${tile('Conteúdos aprovados', pctTxt(r.taxa_aprovacao),
        `${fmt(r.ativos_aprovados)} de ${fmt(r.ativos_gerados)} gerados · ${fmt(r.ativos_pendentes)} aguardando curadoria`)}
    </div>`;
}

// ---------------------------------------------------------------------------
// Sentimento ao longo do tempo: colunas divergentes em torno do zero
// ---------------------------------------------------------------------------
export function renderSentimentoTempo(dados = {}) {
  const pontos = dados.pontos || [];
  const semana = dados.granularidade === 'semana';
  const titulo = 'Como o clima da comunidade evolui';
  const sub = `Mensagens por ${semana ? 'semana' : 'dia'}: positivas acima da linha, negativas abaixo; o neutro fica dividido ao meio.`;
  if (!pontos.some(p => p.total > 0)) return cartao({ titulo, legenda: sub, corpo: vazio('Nenhuma mensagem no período.') });

  const lado = (p, chaves) => chaves.reduce((s, k) => s + (p.contagens[k] || 0), 0) + (p.contagens.Neutro || 0) / 2;
  const maior = Math.max(...pontos.map(p => Math.max(lado(p, ['Positivo', 'Altamente Positivo']), lado(p, ['Negativo', 'Altamente Negativo']))));
  const escala = tetoRedondo(maior);
  const altura = (v) => `${(v / escala) * 100}%`;
  const passoX = Math.max(1, Math.ceil(pontos.length / 12));

  const colunas = pontos.map(p => {
    const c = p.contagens;
    const seg = (v, cor) => (v > 0 ? `<div class="ins-seg" style="height:${altura(v)}; background:${cor}"></div>` : '');
    const meioNeutro = (c.Neutro || 0) / 2;
    const cima = seg(meioNeutro, 'var(--sent-neu)') + seg(c.Positivo, 'var(--sent-pos1)') + seg(c['Altamente Positivo'], 'var(--sent-pos2)');
    const baixo = seg(meioNeutro, 'var(--sent-neu)') + seg(c.Negativo, 'var(--sent-neg1)') + seg(c['Altamente Negativo'], 'var(--sent-neg2)');
    const linhas = [...SENTIMENTOS].reverse().map(s => ({ c: s.cor, v: fmt(c[s.chave]), r: s.nome }));
    const rotulo = semana ? `Semana de ${p.inicio.split('-').reverse().slice(0, 2).join('/')}` : p.rotulo;
    return `
      <div class="ins-col" role="img" aria-label="${esc(`${rotulo}: ${p.total} mensagens`)}"
           ${dica(`${rotulo} · ${fmt(p.total)} mensagens`, linhas)}>
        <div class="ins-col-cima">${cima}</div>
        <div class="ins-col-baixo">${baixo}</div>
      </div>`;
  }).join('');

  const eixoX = pontos.map((p, i) => `<span>${i % passoX === 0 ? esc(p.rotulo.replace('sem. ', '')) : ''}</span>`).join('');
  const meia = escala / 2;
  const corpo = `
    ${legenda(SENTIMENTOS)}
    <div class="ins-tempo">
      <div class="ins-tempo-eixo" aria-hidden="true" style="height:200px;">
        <span>${fmt(escala)}</span><span>${fmt(meia)}</span><span>0</span><span>${fmt(meia)}</span><span>${fmt(escala)}</span>
      </div>
      <div class="ins-tempo-plot">
        <div class="ins-tempo-colunas"><div class="ins-tempo-zero"></div>${colunas}</div>
      </div>
      <div></div>
      <div class="ins-tempo-x" aria-hidden="true">${eixoX}</div>
    </div>
    ${tabela('tempo', [semana ? 'Semana de' : 'Dia', ...SENTIMENTOS.map(s => s.nome), 'Total'],
      pontos.map(p => [p.inicio.split('-').reverse().join('/'), ...SENTIMENTOS.map(s => fmt(p.contagens[s.chave])), fmt(p.total)]))}`;
  return cartao({ titulo, legenda: sub, corpo });
}

// ---------------------------------------------------------------------------
// Sentimento por canal: barras divergentes centradas no neutro
// ---------------------------------------------------------------------------
export function renderCanais(linhas = []) {
  const titulo = 'Onde está o atrito';
  const sub = 'Tom de cada canal, do mais crítico ao mais positivo. Negativas à esquerda da linha central, positivas à direita.';
  if (!linhas.length) return cartao({ titulo, legenda: sub, corpo: vazio('Nenhum canal no período.') });

  const esq = (p) => (p['Altamente Negativo'] || 0) + (p.Negativo || 0) + (p.Neutro || 0) / 2;
  const dir = (p) => (p['Altamente Positivo'] || 0) + (p.Positivo || 0) + (p.Neutro || 0) / 2;
  const L = Math.max(...linhas.map(l => esq(l.percentuais)), 1);
  const R = Math.max(...linhas.map(l => dir(l.percentuais)), 1);
  const dominio = L + R;
  const centro = (L / dominio) * 100;

  const corpoLinhas = linhas.map(l => {
    const p = l.percentuais;
    const inicio = ((L - esq(p)) / dominio) * 100;
    const largura = ((esq(p) + dir(p)) / dominio) * 100;
    const segs = SENTIMENTOS.filter(s => p[s.chave] > 0)
      .map(s => `<div style="flex:${p[s.chave]} 1 0; background:${s.cor}"></div>`).join('');
    const saldo = `${l.saldo > 0 ? '+' : l.saldo < 0 ? '−' : ''}${Math.abs(l.saldo).toLocaleString('pt-BR', { maximumFractionDigits: 1 })}`;
    const linhasDica = [...SENTIMENTOS].reverse().map(s => ({ c: s.cor, v: pctTxt(p[s.chave]), r: `${s.nome} (${fmt(l.contagens[s.chave])})` }));
    return `
      <div class="ins-linha">
        <span class="ins-linha-nome" title="${esc(l.canal)}">${esc(l.canal)}</span>
        <div class="ins-trilho" role="img" aria-label="${esc(`${l.canal}: saldo ${saldo} pontos, ${l.total} mensagens`)}"
             ${dica(`${l.canal} · ${fmt(l.total)} mensagens`, linhasDica, `Saldo: ${saldo} p.p.`)}>
          <div class="ins-pilha" style="left:${inicio}%; width:${largura}%">${segs}</div>
          <div class="ins-centro" style="left:${centro}%"></div>
        </div>
        <span class="ins-linha-valor"><strong>${esc(saldo)}</strong> saldo · ${fmt(l.total)}</span>
      </div>`;
  }).join('');

  const corpo = `
    ${legenda(SENTIMENTOS)}
    <div class="ins-linhas">${corpoLinhas}</div>
    <div class="ins-escala" aria-hidden="true"><span></span><div><span>← mais negativas</span><span>mais positivas →</span></div><span></span></div>
    ${tabela('canais', ['Canal', ...SENTIMENTOS.map(s => s.nome), 'Saldo (p.p.)', 'Mensagens'],
      linhas.map(l => [l.canal, ...SENTIMENTOS.map(s => pctTxt(l.percentuais[s.chave])), l.saldo, fmt(l.total)]))}`;
  return cartao({ titulo, legenda: sub, corpo });
}

// ---------------------------------------------------------------------------
// Tópicos: volume e tom de cada um
// ---------------------------------------------------------------------------
export function renderTopicos(linhas = []) {
  const titulo = 'Do que a comunidade fala';
  const sub = 'Os tópicos com mais mensagens e o tom de cada um: um tópico grande e laranja é uma dor recorrente.';
  if (!linhas.length) return cartao({ titulo, legenda: sub, corpo: vazio('Nenhum tópico no período.') });

  const maior = Math.max(...linhas.map(l => l.total), 1);
  const corpoLinhas = linhas.map(l => {
    const segs = TOM.filter(t => l[t.chave] > 0)
      .map(t => `<div style="flex:${l[t.chave]} 1 0; background:${t.cor}"></div>`).join('');
    const linhasDica = TOM.map(t => ({ c: t.cor, v: fmt(l[t.chave]), r: t.nome }));
    return `
      <div class="ins-linha">
        <span class="ins-linha-nome" title="${esc(l.topico)}">${esc(l.topico)}</span>
        <div class="ins-trilho" role="img" aria-label="${esc(`${l.topico}: ${l.total} mensagens, ${l.negativos} negativas`)}"
             ${dica(`${l.topico} · ${fmt(l.total)} mensagens`, linhasDica)}>
          <div class="ins-pilha da-base" style="left:0; width:${(l.total / maior) * 100}%">${segs}</div>
        </div>
        <span class="ins-linha-valor"><strong>${fmt(l.total)}</strong> msgs</span>
      </div>`;
  }).join('');

  const corpo = `
    ${legenda(TOM)}
    <div class="ins-linhas">${corpoLinhas}</div>
    ${tabela('topicos', ['Tópico', ...TOM.map(t => t.nome), 'Total'],
      linhas.map(l => [l.topico, ...TOM.map(t => fmt(l[t.chave])), fmt(l.total)]))}`;
  return cartao({ titulo, legenda: sub, corpo });
}

// ---------------------------------------------------------------------------
// Atividade por canal ao longo do tempo: mapa de calor
// ---------------------------------------------------------------------------
export function renderAtividade(dados = {}) {
  const { colunas = [], linhas = [], maximo = 0, granularidade } = dados;
  const semana = granularidade === 'semana';
  const titulo = 'Quando e onde a comunidade conversa';
  const sub = `Mensagens por canal em cada ${semana ? 'semana' : 'dia'}. Quanto mais intensa a cor, mais mensagens.`;
  if (!linhas.length || !maximo) return cartao({ titulo, legenda: sub, corpo: vazio('Nenhuma mensagem no período.') });

  const passo = (v) => (v <= 0 ? 0 : Math.min(4, Math.ceil((v / maximo) * 4)));
  const passoX = Math.max(1, Math.ceil(colunas.length / 14));
  const faixa = (i) => {
    const de = Math.floor((maximo * (i - 1)) / 4) + 1;
    const ate = Math.floor((maximo * i) / 4);
    return de >= ate ? fmt(ate) : `${fmt(de)}–${fmt(ate)}`;
  };
  const passosLegenda = [1, 2, 3, 4].filter(i => Math.floor((maximo * i) / 4) >= Math.floor((maximo * (i - 1)) / 4) + 1);

  const corpo = `
    <div class="ins-legenda" aria-hidden="true">
      <span><i style="background:var(--heat-0)"></i>0</span>
      ${passosLegenda.map(i => `<span><i style="background:var(--heat-${i})"></i>${faixa(i)}</span>`).join('')}
    </div>
    <div class="ins-calor">
      <table>
        <thead><tr><th></th>${colunas.map((c, i) => `<th scope="col">${i % passoX === 0 ? esc(c.rotulo.replace('sem. ', '')) : ''}</th>`).join('')}<th></th></tr></thead>
        <tbody>
          ${linhas.map(l => `
            <tr>
              <th scope="row" title="${esc(l.canal)}">${esc(l.canal)}</th>
              ${l.valores.map((v, i) => `<td class="ins-cel" style="background:var(--heat-${passo(v)})"
                  ${dica(`${l.canal} · ${semana ? 'semana de ' : ''}${colunas[i].inicio.split('-').reverse().slice(0, 2).join('/')}`,
                    [{ c: `var(--heat-${Math.max(1, passo(v))})`, v: fmt(v), r: v === 1 ? 'mensagem' : 'mensagens' }])}></td>`).join('')}
              <td class="ins-total">${fmt(l.total)}</td>
            </tr>`).join('')}
        </tbody>
      </table>
    </div>
    ${tabela('atividade', ['Canal', ...colunas.map(c => c.inicio.split('-').reverse().slice(0, 2).join('/')), 'Total'],
      linhas.map(l => [l.canal, ...l.valores.map(fmt), fmt(l.total)]))}`;
  return cartao({ titulo, legenda: sub, corpo });
}

// ---------------------------------------------------------------------------
// Para onde vão as mensagens (rotas da IA)
// ---------------------------------------------------------------------------
const EXPLICA_ROTA = {
  case_sucesso: 'vira post de LinkedIn',
  faq: 'vira sugestão de FAQ',
  alerta: 'pede cuidado da equipe',
  nenhuma: 'só entra nas métricas',
};

export function renderRotas(rotas = []) {
  const titulo = 'O que a IA fez com as mensagens';
  const sub = 'Rota atribuída a cada mensagem: é daqui que saem os conteúdos e os alertas.';
  const total = rotas.reduce((s, r) => s + (r.quantidade || 0), 0);
  if (!total) return cartao({ titulo, legenda: sub, corpo: vazio('Nenhuma mensagem no período.') });

  const ordenadas = [...rotas].sort((a, b) => b.quantidade - a.quantidade);
  const maior = Math.max(...ordenadas.map(r => r.quantidade), 1);
  const corpo = `
    <div class="ins-linhas">
      ${ordenadas.map(r => `
        <div class="ins-linha">
          <span class="ins-linha-nome com-nota">${esc(r.nome)}<small>${esc(EXPLICA_ROTA[r.rota] || '')}</small></span>
          <div class="ins-trilho" role="img" aria-label="${esc(`${r.nome}: ${r.quantidade} mensagens`)}"
               ${dica(r.nome, [{ c: 'var(--chart-bar)', v: fmt(r.quantidade), r: `mensagens (${pctTxt((100 * r.quantidade) / total)})` }])}>
            ${r.quantidade ? `<div class="ins-barra" style="width:${(r.quantidade / maior) * 100}%"></div>` : ''}
          </div>
          <span class="ins-linha-valor"><strong>${fmt(r.quantidade)}</strong> · ${pctTxt(Math.round((100 * r.quantidade) / total))}</span>
        </div>`).join('')}
    </div>
    ${tabela('rotas', ['Rota', 'Mensagens', '%'], ordenadas.map(r => [r.nome, fmt(r.quantidade), pctTxt((100 * r.quantidade) / total)]))}`;
  return cartao({ titulo, legenda: sub, corpo });
}

// ---------------------------------------------------------------------------
// Aproveitamento editorial por tipo de conteúdo
// ---------------------------------------------------------------------------
const ESTADOS_CURADORIA = [
  { chave: 'aprovados', nome: 'Aprovado', cor: 'var(--estado-bom)', classe: 'bom' },
  { chave: 'pendentes', nome: 'Aguardando', cor: 'var(--estado-atencao)', classe: 'atencao' },
  { chave: 'descartados', nome: 'Descartado', cor: 'var(--estado-neutro)', classe: 'descartado' },
];

export function renderAproveitamento(linhas = []) {
  const titulo = 'O que vira conteúdo publicado';
  const sub = 'Decisões da curadoria sobre os rascunhos gerados pela IA, por tipo de conteúdo.';
  if (!linhas.length) return cartao({ titulo, legenda: sub, corpo: vazio('Nenhum conteúdo gerado no período.') });

  const corpo = `
    <div class="ins-legenda">${ESTADOS_CURADORIA.map(e => `<span class="ins-estado ${e.classe}"><i style="background:${e.cor}"></i>${esc(e.nome)}</span>`).join('')}</div>
    <div class="ins-linhas" style="gap:14px;">
      ${linhas.map(l => `
        <div class="ins-linha">
          <span class="ins-linha-nome">${esc(l.nome)}</span>
          <div class="ins-trilho" style="height:8px;" role="img"
               aria-label="${esc(`${l.nome}: ${l.aprovados} aprovados, ${l.pendentes} aguardando, ${l.descartados} descartados`)}"
               ${dica(`${l.nome} · ${fmt(l.total)} gerados`, ESTADOS_CURADORIA.map(e => ({ c: e.cor, v: fmt(l[e.chave]), r: e.nome })))}>
            <div class="ins-fina">${ESTADOS_CURADORIA.filter(e => l[e.chave] > 0)
              .map(e => `<div style="flex:${l[e.chave]} 1 0; background:${e.cor}"></div>`).join('')}</div>
          </div>
          <span class="ins-linha-valor"><strong>${fmt(l.aprovados)}</strong> de ${fmt(l.total)} aprovados</span>
        </div>`).join('')}
    </div>
    ${tabela('aproveitamento', ['Tipo', ...ESTADOS_CURADORIA.map(e => e.nome), 'Total'],
      linhas.map(l => [l.nome, ...ESTADOS_CURADORIA.map(e => fmt(l[e.chave])), fmt(l.total)]))}`;
  return cartao({ titulo, legenda: sub, corpo });
}

// ---------------------------------------------------------------------------
// Alertas: estado da triagem e fila dos abertos
// ---------------------------------------------------------------------------
const ESTADOS_ALERTA = [
  { chave: 'PENDENTE', nome: 'Em aberto', cor: 'var(--estado-atencao)', classe: 'atencao' },
  { chave: 'ENCAMINHADO', nome: 'Encaminhado', cor: 'var(--estado-neutro)', classe: 'neutro' },
  { chave: 'RESOLVIDO', nome: 'Resolvido', cor: 'var(--estado-bom)', classe: 'bom' },
];

export function renderAlertas(dados = {}) {
  const { total = 0, por_estado: estados = {}, abertos = [], abertos_restantes: restantes = 0 } = dados;
  const titulo = 'Cuidado com a comunidade';
  const sub = 'Mensagens que a IA marcou como alerta e em que pé está a triagem de cada uma.';
  if (!total) return cartao({ titulo, legenda: sub, corpo: vazio('Nenhum alerta no período.') });

  const barra = ESTADOS_ALERTA.filter(e => estados[e.chave] > 0).map(e => {
    const v = estados[e.chave];
    const share = v / total;
    return `<div style="flex:${v} 1 0; background:${e.cor}" role="img" aria-label="${esc(`${e.nome}: ${v}`)}"
                 ${dica(e.nome, [{ c: e.cor, v: fmt(v), r: `de ${fmt(total)} (${pctTxt(Math.round(100 * share))})` }])}>${share >= 0.12 ? fmt(v) : ''}</div>`;
  }).join('');

  const fila = abertos.length ? `
    <h4 style="font-size:13px; font-weight:600; margin:16px 0 6px; color:var(--text);">Em aberto, do mais antigo ao mais novo</h4>
    <div style="overflow-x:auto;">
      <table class="ins-fila">
        <thead><tr><th scope="col">Data</th><th scope="col">Canal</th><th scope="col">Membro</th><th scope="col">Motivo</th><th scope="col"><span class="sr-only">Ação</span></th></tr></thead>
        <tbody>
          ${abertos.map(a => `
            <tr>
              <td style="white-space:nowrap;">${esc(a.data ? a.data.split('-').reverse().slice(0, 2).join('/') : '')}</td>
              <td style="white-space:nowrap;">${esc(a.canal)}</td>
              <td>${esc(a.autor || 'Anônimo')}</td>
              <td class="ins-motivo">${esc(a.motivo)}</td>
              <td>${a.lote_id && a.lote_id !== 'demo' ? `<button type="button" class="btn-abrir-lote" data-lote="${esc(a.lote_id)}">Tratar</button>` : ''}</td>
            </tr>`).join('')}
        </tbody>
      </table>
    </div>
    ${restantes ? `<p class="ins-kpi-nota" style="margin-top:8px;">E mais ${fmt(restantes)} em aberto.</p>` : ''}` : `
    <p class="ins-kpi-nota" style="margin-top:6px;"><span class="ins-estado bom">Nenhum alerta em aberto no período.</span></p>`;

  const corpo = `
    <div class="ins-segmentada">${barra}</div>
    <div class="ins-legenda">${ESTADOS_ALERTA.map(e => `<span class="ins-estado ${e.classe}"><i style="background:${e.cor}"></i>${esc(e.nome)} · ${fmt(estados[e.chave])}</span>`).join('')}</div>
    ${fila}`;
  return cartao({ titulo, legenda: sub, corpo });
}

// ---------------------------------------------------------------------------
// Membros que mais participam
// ---------------------------------------------------------------------------
export function renderMembros(linhas = []) {
  const titulo = 'Quem mais participa';
  const sub = 'Membros com mais mensagens no período. Quem tem cases de sucesso é candidato a depoimento.';
  if (!linhas.length) return cartao({ titulo, legenda: sub, corpo: vazio('Nenhum membro identificado no período.') });

  const maior = Math.max(...linhas.map(l => l.total), 1);
  const corpo = `
    <div class="ins-linhas">
      ${linhas.map(l => `
        <div class="ins-linha">
          <span class="ins-linha-nome" title="${esc(l.autor)}">${esc(l.autor)}</span>
          <div class="ins-trilho" role="img" aria-label="${esc(`${l.autor}: ${l.total} mensagens`)}"
               ${dica(l.autor, [
                 { c: 'var(--chart-bar)', v: fmt(l.total), r: 'mensagens' },
                 { c: 'var(--sent-pos1)', v: fmt(l.positivos), r: 'positivas' },
                 { c: 'var(--sent-neg1)', v: fmt(l.negativos), r: 'negativas' },
               ], l.cases ? `${fmt(l.cases)} ${l.cases === 1 ? 'case de sucesso' : 'cases de sucesso'}` : '')}>
            <div class="ins-barra" style="width:${(l.total / maior) * 100}%"></div>
          </div>
          <span class="ins-linha-valor"><strong>${fmt(l.total)}</strong> msgs${l.cases ? ` · ${fmt(l.cases)} case${l.cases === 1 ? '' : 's'}` : ''}</span>
        </div>`).join('')}
    </div>
    ${tabela('membros', ['Membro', 'Mensagens', 'Positivas', 'Negativas', 'Cases'],
      linhas.map(l => [l.autor, fmt(l.total), fmt(l.positivos), fmt(l.negativos), fmt(l.cases)]))}`;
  return cartao({ titulo, legenda: sub, corpo });
}
