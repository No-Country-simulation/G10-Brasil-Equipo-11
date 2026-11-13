-- O histórico passa a seguir o dia em que cada mensagem foi escrita, e não o dia da importação.
alter table interacoes add column data date;

-- Lotes antigos não trazem a data das mensagens: ficam com o dia em que foram processados.
update interacoes i set data = (l.processado_em at time zone 'America/Sao_Paulo')::date
from lotes l where l.id = i.lote_id;

alter table interacoes alter column data set not null;
create index on interacoes (data);

create or replace view vw_interacoes_analisadas with (security_invoker = true) as
select l.id as lote_id, l.processado_em, l.modo_llm, l.periodo_referencia, c.nome as comunidade,
       i.id as interacao_id, i.ordem, i.autor, i.canal, i.tipo,
       a.sentimento, a.topico, a.relevancia, a.rota,
       i.data
from interacoes i
join analises a on a.interacao_id = i.id
join lotes l on l.id = i.lote_id
join comunidades c on c.id = l.comunidade_id;
