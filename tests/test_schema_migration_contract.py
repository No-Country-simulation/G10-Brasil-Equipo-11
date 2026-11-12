from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def test_migracao_v3_registra_data_original():
    migration = (
        ROOT / "sql" / "003_data_interacao.sql"
    ).read_text(encoding="utf-8")

    sql = re.sub(r"\s+", " ", migration).upper()

    assert "ALTER TABLE CL_INTERACOES" in sql
    assert "DATA_INTERACAO DATE" in sql
    assert "SET DATA_INTERACAO" in sql
    assert "AT TIME ZONE 'AMERICA/SAO_PAULO'" in sql
    assert "DATA_INTERACAO NOT NULL" in sql
    assert "IX_CL_INT_DATA" in sql

    assert re.search(r"VALUES\s*\(\s*3\s*,", sql)
    assert "DATA ORIGINAL DAS INTERAÇÕES PARA INSIGHTS" in sql


def test_schema_runtime_cobre_tabelas_e_colunas():
    source = (
        ROOT / "app" / "database.py"
    ).read_text(encoding="utf-8").upper()

    tabelas = (
        "CL_SCHEMA_VERSION",
        "CL_PROCESSAMENTOS",
        "CL_INTERACOES",
        "CL_ATIVOS",
        "CL_ATIVO_INTERACOES",
        "CL_HISTORICO_CURADORIA",
        "CL_EXPORTACOES",
        "CL_ALERTAS",
        "CL_HISTORICO_ALERTAS",
    )

    for tabela in tabelas:
        assert f'"{tabela}"' in source, (
            f"Tabela não validada pela aplicação: {tabela}"
        )

    colunas_insights = (
        "DATA_INTERACAO",
        "AUTOR",
        "CANAL",
        "TIPO",
        "ANALISE_JSON",
    )

    for coluna in colunas_insights:
        assert f'"{coluna}"' in source, (
            f"Coluna necessária para Insights não validada: {coluna}"
        )


def test_schema_runtime_exige_versao_3():
    source = (
        ROOT / "app" / "database.py"
    ).read_text(encoding="utf-8").upper()

    assert re.search(r"IF\s+VERSION\s*!=\s*3\b", source)


def test_schema_runtime_declara_restricoes_criticas():
    source = (
        ROOT / "app" / "database.py"
    ).read_text(encoding="utf-8").upper()

    restricoes = (
        "CK_CL_PROC_STATUS",
        "CK_CL_PROC_OCI",
        "CK_CL_PROC_TOKEN",
        "UQ_CL_PROC_IDEMP",
        "FK_CL_INT_PROC",
        "UQ_CL_INT_POS",
        "UQ_CL_INT_PROC_ID",
        "FK_CL_ATI_PROC",
        "UQ_CL_ATI_CHAVE",
        "UQ_CL_ATI_PROC_ID",
        "CK_CL_ATI_STATUS",
        "CK_CL_ATI_CONSENT",
        "CK_CL_ATI_VERSAO",
        "FK_CL_AI_ATIVO",
        "FK_CL_AI_INTER",
        "FK_CL_HIST_ATIVO",
        "FK_CL_EXP_PROC",
        "UQ_CL_EXP_IDEMP",
        "CK_CL_EXP_STATUS",
        "FK_CL_ALERTA_INTERACAO",
        "UQ_CL_ALERTA_PROC_ID",
        "UQ_CL_ALERTA_INTERACAO",
        "CK_CL_ALERTA_STATUS",
        "CK_CL_ALERTA_VERSAO",
        "FK_CL_HIST_ALERTA",
        "CK_CL_HIST_ALERTA_STATUS",
    )

    for restricao in restricoes:
        assert f'"{restricao}"' in source, (
            f"Restrição crítica não validada: {restricao}"
        )


def test_ambiente_de_exemplo_nao_contem_segredos():
    env = (
        ROOT / ".env.example"
    ).read_text(encoding="utf-8")

    assert "COMMUNITYLAB_DB_MODE=disabled" in env
    assert "OCI_STORAGE_MODE=local" in env
    assert "COMMUNITYLAB_API_KEY=" in env
    assert "COMMUNITYLAB_DB_PASSWORD=" in env
    assert "GEMINI_API_KEY=" in env