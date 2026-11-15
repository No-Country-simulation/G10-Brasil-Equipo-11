// web/js/demo/dados-demo.js
// Dados fictícios da demonstração da landing, no mesmo formato de /api/visao-geral e /api/curadoria/fila.
// Pessoas, canais e mensagens são inventados.

const hoje = new Date();
const diasAtras = (n, h = 10) => {
  const d = new Date(hoje);
  d.setDate(d.getDate() - n);
  d.setHours(h, 12, 0, 0);
  return d;
};
const iso = (n, h) => diasAtras(n, h).toISOString();
const dia = (n) => diasAtras(n).toISOString().slice(0, 10);
const periodo = `${hoje.getFullYear()}-${String(hoje.getMonth() + 1).padStart(2, '0')}`;

const a = (autor, canal, texto, sentimento, rota, relevancia, tipo = 'outro') =>
  ({ autor, canal, texto, sentimento, rota, relevancia, tipo });

const LOTE_DISCORD = {
  lote_id: 'demo-1',
  origem: 'Discord · Comunidade Dev',
  periodo,
  processado_em: iso(3, 9),
  autorizado: false,
  alertas: {},
  decisoes: {},
  resultado: {
    analises: [
      a('Marina Lopes', '#conquistas', 'Fui aprovada no processo seletivo e o projeto do bootcamp fez toda a diferença na entrevista!', 'Altamente Positivo', 'case_sucesso', 9),
      a('Caio Ribeiro', '#duvidas', 'Alguém sabe por que meu deploy falha com erro de porta já em uso?', 'Neutro', 'faq', 7, 'duvida'),
      a('Bianca Souza', '#duvidas', 'Como faço para guardar segredos fora do repositório sem complicar o projeto?', 'Neutro', 'faq', 6, 'duvida'),
      a('Rafael Nunes', '#feedback', 'A plataforma caiu na hora da entrega e ninguém respondeu no suporte.', 'Altamente Negativo', 'alerta', 8, 'reclamacao'),
      a('Júlia Prado', '#geral', 'Bom dia, pessoal! Bora codar.', 'Positivo', 'nenhuma', 2),
    ],
    ativos_distribuicao_gerados: {
      post_linkedin: {
        titulo: 'Do bootcamp para a vaga',
        copy: 'A Marina passou no processo seletivo e contou que o projeto final do bootcamp foi o assunto da entrevista. 🚀\n\nÉ isso que acontece quando a prática vem antes da teoria.\n\n#Carreira #Comunidade #Tecnologia',
        potencial_engajamento: 'Alto',
      },
      destaque_newsletter_semanal: {
        secao: 'Conquistas da semana',
        chamada: 'Projeto do bootcamp abre portas',
        resumo: 'Uma integrante da comunidade foi aprovada em processo seletivo e atribuiu o resultado ao projeto prático.',
      },
      sugestao_conteudo_faq: [
        { tema: 'Erro de porta em uso no deploy', conteudo: 'Verifique se outro processo já usa a porta e configure a aplicação para ler a porta de uma variável de ambiente.', origem: '#duvidas' },
        { tema: 'Segredos fora do repositório', conteudo: 'Use um arquivo .env fora do controle de versão e um exemplo sem valores (.env.example) para documentar as variáveis.', origem: '#duvidas' },
      ],
    },
  },
};

const LOTE_TELEGRAM = {
  lote_id: 'demo-2',
  origem: 'Telegram · Python Iniciantes',
  periodo,
  processado_em: iso(1, 18),
  autorizado: false,
  alertas: {},
  decisoes: {},
  resultado: {
    analises: [
      a('Pedro Alves', '#ajuda', 'Qual a diferença entre lista e tupla na prática?', 'Neutro', 'faq', 6, 'duvida'),
      a('Lia Moreira', '#ajuda', 'Meu ambiente virtual não ativa no Windows, aparece erro de permissão.', 'Negativo', 'faq', 7, 'duvida'),
      a('Tiago Costa', '#geral', 'Estou travado há uma semana e pensando em desistir do curso.', 'Negativo', 'alerta', 8, 'duvida'),
      a('Ana Beatriz', '#vitrine', 'Publiquei meu primeiro projeto com README completo, obrigada pelas dicas!', 'Positivo', 'case_sucesso', 7),
    ],
    ativos_distribuicao_gerados: {
      destaque_newsletter_semanal: {
        secao: 'Primeiros projetos',
        chamada: 'README completo no primeiro projeto',
        resumo: 'Integrante iniciante publicou o primeiro projeto com documentação seguindo as dicas do grupo.',
      },
      sugestao_conteudo_faq: [
        { tema: 'Lista ou tupla?', conteudo: 'Lista é mutável e serve para coleções que mudam; tupla é imutável e boa para dados fixos, como coordenadas.', origem: '#ajuda' },
        { tema: 'Ambiente virtual no Windows', conteudo: 'Rode o PowerShell como usuário e libere scripts locais com Set-ExecutionPolicy RemoteSigned -Scope CurrentUser.', origem: '#ajuda' },
      ],
    },
  },
};

export const LOTES_DEMO = [LOTE_DISCORD, LOTE_TELEGRAM];

function contarAtivos(lote) {
  const g = lote.resultado.ativos_distribuicao_gerados;
  return {
    post: g.post_linkedin ? 1 : 0,
    newsletter: g.destaque_newsletter_semanal ? 1 : 0,
    faq: (g.sugestao_conteudo_faq || []).length,
  };
}

function alertasDoLote(lote) {
  return lote.resultado.analises
    .map((an, ordem) => ({ an, ordem }))
    .filter(({ an }) => an.rota === 'alerta')
    .map(({ an, ordem }) => ({
      lote_id: lote.lote_id, ordem, origem: lote.origem, periodo: lote.periodo,
      autor: an.autor, canal: an.canal, texto: an.texto, tipo: an.tipo,
    }));
}

const interacoes = [];
[LOTE_DISCORD, LOTE_TELEGRAM].forEach((lote, i) => {
  lote.resultado.analises.forEach((an, j) => {
    interacoes.push({ lote_id: lote.lote_id, data: dia(i * 2 + (j % 3)), ...an });
  });
});
[
  a('Sofia Lima', '#geral', 'Alguém vai no meetup de sábado?', 'Neutro', 'nenhuma', 3),
  a('Gustavo Reis', '#feedback', 'As aulas ao vivo estão ótimas, só o áudio às vezes falha.', 'Positivo', 'nenhuma', 4),
  a('Helena Dias', '#conquistas', 'Consegui meu primeiro freela graças ao portfólio!', 'Altamente Positivo', 'case_sucesso', 6),
].forEach((an, k) => interacoes.push({ lote_id: 'demo-1', data: dia(k + 1), ...an }));

export const VISAO_DEMO = {
  oracle_configurado: true,
  atualizado_em: hoje.toISOString(),
  janela: { inicio: dia(6), fim: dia(0) },
  lotes_pendentes: LOTES_DEMO.map(lote => {
    const porTipo = contarAtivos(lote);
    return {
      lote_id: lote.lote_id, origem: lote.origem, periodo: lote.periodo, processado_em: lote.processado_em,
      ativos_pendentes: porTipo.post + porTipo.newsletter + porTipo.faq, ativos_por_tipo: porTipo,
      alertas_pendentes: alertasDoLote(lote).length,
    };
  }),
  alertas_pendentes: LOTES_DEMO.flatMap(alertasDoLote),
  alertas_tratados_janela: 3,
  interacoes,
};
