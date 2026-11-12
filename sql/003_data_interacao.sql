-- CommunityLab - Oracle Database v3
-- Adiciona a data original de cada interação.
--
-- Pré-requisito histórico: schema na versão 2.
-- Esta migração já foi executada no banco COMMUNITYLAB_APP.
-- Não executar novamente no banco que já está na versão 3.

ALTER TABLE CL_INTERACOES
ADD (
    DATA_INTERACAO DATE
);

UPDATE CL_INTERACOES i
SET DATA_INTERACAO = (
    SELECT TRUNC(
        CAST(
            p.CRIADO_EM AT TIME ZONE 'America/Sao_Paulo'
            AS DATE
        )
    )
    FROM CL_PROCESSAMENTOS p
    WHERE p.ID = i.PROCESSAMENTO_ID
)
WHERE DATA_INTERACAO IS NULL;

ALTER TABLE CL_INTERACOES
MODIFY (
    DATA_INTERACAO NOT NULL
);

CREATE INDEX IX_CL_INT_DATA
ON CL_INTERACOES (DATA_INTERACAO);

INSERT INTO CL_SCHEMA_VERSION (
    VERSION_NO,
    DESCRIPTION
)
VALUES (
    3,
    'Data original das interações para Insights'
);

COMMIT;