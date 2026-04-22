import pytest
import pandas as pd
from sqlalchemy import text
from src.data.data_provider import get_dw_engine, get_companies, get_available_competencias

def test_db_connection():
    engine = get_dw_engine()
    with engine.connect() as conn:
        res = conn.execute(text("SELECT 1")).scalar()
        assert res == 1

def test_get_companies():
    # Integração: testa se a view/tabela existe e se o mapeamento padrão é gerado
    companies = get_companies()
    assert isinstance(companies, list)
    if not companies:
        # Se o BD estiver vazio não quebra, mas a lista deve existir.
        pass
    else:
        assert 'label' in companies[0]
        assert 'value' in companies[0]

def test_get_available_competencias():
    comps = get_available_competencias()
    assert isinstance(comps, list)
    if comps:
        assert 'label' in comps[0]
        assert 'value' in comps[0]
