from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_migracoes_tem_versoes_e_ordem_explicitas():
    v1 = (
        ROOT / "sql" / "001_oracle_schema.sql"
    ).read_text(encoding="utf-8")

    v2 = (
        ROOT / "sql" / "002_robustez.sql"
    ).read_text(encoding="utf-8")

    assert "VERSION_NO" in v1
    assert "VALUES (1," in v1
    assert "ATTEMPT_TOKEN" in v2
    assert "VALUES (2," in v2
    assert "CL_ALERTAS" in v2
    assert "CL_HISTORICO_ALERTAS" in v2
    assert "CONSENTIMENTO_REFERENCIA" in v2


def test_schema_cobre_tabelas_do_repositorio():
    v1 = (
        ROOT / "sql" / "001_oracle_schema.sql"
    ).read_text(encoding="utf-8")

    v2 = (
        ROOT / "sql" / "002_robustez.sql"
    ).read_text(encoding="utf-8")

    merged = v1 + "\n" + v2

    for table in (
        "CL_SCHEMA_VERSION",
        "CL_PROCESSAMENTOS",
        "CL_INTERACOES",
        "CL_ATIVOS",
        "CL_ATIVO_INTERACOES",
        "CL_HISTORICO_CURADORIA",
        "CL_EXPORTACOES",
        "CL_ALERTAS",
        "CL_HISTORICO_ALERTAS",
    ):
        assert f"CREATE TABLE {table}" in merged


def test_ambiente_de_exemplo_nao_contem_segredos():
    env = (
        ROOT / ".env.example"
    ).read_text(encoding="utf-8")

    assert "COMMUNITYLAB_DB_MODE=disabled" in env
    assert "OCI_STORAGE_MODE=local" in env
    assert "COMMUNITYLAB_API_KEY=" in env
    assert "COMMUNITYLAB_DB_PASSWORD=" in env
    assert "GEMINI_API_KEY=" in env


def test_migracoes_declaram_restricoes_criticas():
    v1 = (
        ROOT / "sql" / "001_oracle_schema.sql"
    ).read_text(encoding="utf-8")

    v2 = (
        ROOT / "sql" / "002_robustez.sql"
    ).read_text(encoding="utf-8")

    merged = v1 + "\n" + v2

    for constraint in (
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
    ):
        assert constraint in merged, (
            f"Restrição crítica ausente: {constraint}"
        )