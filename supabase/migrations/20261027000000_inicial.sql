create table comunidades (id bigint generated always as identity primary key,
  nome text not null unique, criado_em timestamptz not null default now());

create table lotes (id bigint generated always as identity primary key,
  comunidade_id bigint not null references comunidades(id),
  periodo_referencia text not null,
  hash_conteudo text not null,
  modo_llm text not null check (modo_llm in ('mock','gemini')),
  total_interacoes int not null,
  sentimento_predominante text not null check (sentimento_predominante in
    ('Altamente Positivo','Positivo','Neutro','Negativo','Altamente Negativo')),
  topicos_principais text[] not null default '{}',
  oci_bucket text, oci_caminho_objeto text,
  oci_status text check (oci_status in ('salvo_com_sucesso','salvo_localmente','erro')),
  resposta jsonb not null,
  processado_em timestamptz not null default now(),
  unique (hash_conteudo, modo_llm));

create table interacoes (id bigint generated always as identity primary key,
  lote_id bigint not null references lotes(id) on delete cascade,
  ordem int not null, autor text not null, canal text not null,
  tipo text not null check (tipo in ('depoimento','pergunta_tecnica','feedback','reclamacao','projeto','outro')),
  texto text not null, unique (lote_id, ordem));

create table analises (interacao_id bigint primary key references interacoes(id) on delete cascade,
  sentimento text not null check (sentimento in
    ('Altamente Positivo','Positivo','Neutro','Negativo','Altamente Negativo')),
  topico text not null, relevancia int not null check (relevancia between 0 and 10),
  rota text not null check (rota in ('case_sucesso','faq','alerta','nenhuma')));

create table ativos (id bigint generated always as identity primary key,
  lote_id bigint not null references lotes(id) on delete cascade,
  chave text not null,
  tipo text not null check (tipo in ('post_linkedin','newsletter','faq')),
  interacao_origem_id bigint references interacoes(id) on delete cascade,
  conteudo_gerado jsonb not null, conteudo_editado jsonb,
  status text not null default 'pendente' check (status in ('pendente','aprovado','descartado')),
  autorizacao_membro boolean not null default false,
  revisado_em timestamptz,
  unique (lote_id, chave),
  check (tipo <> 'post_linkedin' or status <> 'aprovado' or autorizacao_membro));

create table alertas (id bigint generated always as identity primary key,
  lote_id bigint not null references lotes(id) on delete cascade,
  interacao_id bigint not null references interacoes(id) on delete cascade,
  autor text not null, motivo text not null,
  status text not null default 'aberto' check (status in ('aberto','encaminhado','mentoria_oferecida','resolvido')),
  atualizado_em timestamptz not null default now());

create index on lotes (processado_em);
create index on interacoes (lote_id);

alter table comunidades enable row level security;
alter table lotes enable row level security;
alter table interacoes enable row level security;
alter table analises enable row level security;
alter table ativos enable row level security;
alter table alertas enable row level security;

create view vw_interacoes_analisadas with (security_invoker = true) as
select l.id as lote_id, l.processado_em, l.modo_llm, l.periodo_referencia, c.nome as comunidade,
       i.id as interacao_id, i.ordem, i.autor, i.canal, i.tipo,
       a.sentimento, a.topico, a.relevancia, a.rota
from interacoes i
join analises a on a.interacao_id = i.id
join lotes l on l.id = i.lote_id
join comunidades c on c.id = l.comunidade_id;
