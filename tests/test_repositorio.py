import os
import pytest

def test_testes_simulados_nunca_veem_o_banco():
    assert os.environ.get("DATABASE_URL") == ""
