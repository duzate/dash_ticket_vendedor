"""
data_provider.py — Camada de Acesso a Dados do DW (Data Warehouse).

Responsabilidades:
    - Gerenciar a conexão com o PostgreSQL (pool singleton via lru_cache).
    - Prover funções de consulta para o dashboard (competências, empresas, vendedores, performance).

Regras de Negócio:
    - META: armazenada com id_empresa = 0 (centralizada). Nunca filtra por empresa.
    - REALIZADO / DEVOLUÇÃO / CANCELAMENTO / DESCONTO / COMISSÃO: filtram por empresa.
    - TICKET MÉDIO = valor_realizado / qtd_transacoes (apenas registros com qtd > 0).
"""

import os
import logging
import functools
from pathlib import Path
from typing import Optional

import pandas as pd
from sqlalchemy import create_engine, Engine, text
from dotenv import load_dotenv

# Carrega .env da raiz do projeto, independente do diretório de trabalho atual
_ENV_PATH = Path(__file__).parent.parent.parent / ".env"
load_dotenv(_ENV_PATH)

log = logging.getLogger(__name__)

# ─── Conexão ─────────────────────────────────────────────────────────────────

@functools.lru_cache(maxsize=1)
def get_dw_engine() -> Engine:
    """Retorna o engine SQLAlchemy do DW (singleton thread-safe via lru_cache)."""
    # Procura variáveis POSTGRES_*; se não encontrar, usa os padrões funcionais do DW local.
    user = os.environ.get("POSTGRES_USER", "dw_admin")
    pwd  = os.environ.get("POSTGRES_PASSWORD", "dw_super_password123")
    db   = os.environ.get("POSTGRES_DB",       "sankhya_dw")
    host = os.environ.get("POSTGRES_HOST",     "localhost")
    port = os.environ.get("POSTGRES_PORT",     "5433")

    url  = f"postgresql+psycopg2://{user}:{pwd}@{host}:{port}/{db}"
    log.info("Conectando ao DW em %s:%s/%s (User: %s)", host, port, db, user)

    try:
        engine = create_engine(url, pool_size=10, max_overflow=20, pool_pre_ping=True)
        # Teste rápido de conexão
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return engine
    except Exception as e:
        log.error("Falha ao inicializar o engine do Data Warehouse: %s", e)
        raise



# ─── Helpers internos ────────────────────────────────────────────────────────

def _period_where(alias: str, start: Optional[str], end: Optional[str]) -> Optional[str]:
    if start and end:
        return f"{alias}.id_tempo >= '{start}' AND {alias}.id_tempo <= '{end}'"
    return None


def _sellers_where(alias: str, seller_ids: Optional[list[int]]) -> Optional[str]:
    if seller_ids:
        ids = ",".join(map(str, seller_ids))
        return f"{alias}.id_vendedor IN ({ids})"
    return None


def _build_where(*conditions: Optional[str]) -> str:
    clauses = [c for c in conditions if c]
    return ("WHERE " + " AND ".join(clauses)) if clauses else ""


def _read(query: str) -> pd.DataFrame:
    """Executa uma query e retorna um DataFrame. Loga erros e retorna vazio."""
    try:
        with get_dw_engine().connect() as conn:
            return pd.read_sql(query, con=conn)
    except Exception:
        log.exception("Erro ao executar query no DW.")
        return pd.DataFrame()


# ─── Queries públicas ─────────────────────────────────────────────────────────

def get_companies() -> list[dict]:
    """Retorna empresas com dados reais (id_empresa > 0) no DW."""
    df = _read("SELECT DISTINCT id_empresa FROM fato_vendasdiarias WHERE id_empresa > 0 ORDER BY id_empresa")
    return [{"label": f"Empresa {int(r['id_empresa'])}", "value": int(r["id_empresa"])} for _, r in df.iterrows()]


def get_sellers(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    company_id: Optional[int] = None,
) -> list[dict]:
    """Retorna vendedores com qualquer movimento (realizado, meta ou devolução) no período/empresa."""
    conds = ["(F.valor_realizado <> 0 OR F.valor_devolucao <> 0 OR F.valor_meta_diaria <> 0)"]
    if start_date and end_date:
        conds.append(f"F.id_tempo >= '{start_date}' AND F.id_tempo <= '{end_date}'")
    if company_id is not None:
        conds.append(f"F.id_empresa = {company_id}")

    where = "WHERE " + " AND ".join(conds)
    query = f"""
        SELECT DISTINCT V.Id_Vendedor AS id, V.Nome_Comercial AS name
        FROM dim_vendedor V
        INNER JOIN fato_vendasdiarias F ON V.Id_Vendedor = F.id_vendedor
        {where}
        ORDER BY V.Nome_Comercial ASC
    """
    df = _read(query)
    return df.to_dict("records") if not df.empty else []


def get_available_competencias() -> list[dict]:
    """Retorna os ciclos fiscais disponíveis no DW, ordenados do mais recente ao mais antigo."""
    df = _read("SELECT label, dtref, dtinic, dtfin FROM dim_tempo_ref ORDER BY dtref DESC")
    if df.empty:
        return []
    return [
        {
            "label": str(r["label"]) if r.get("label") else pd.to_datetime(r["dtref"]).strftime("%m/%Y"),
            "value": f"{r['dtinic']}|{r['dtfin']}|{r['dtref']}",
        }
        for _, r in df.iterrows()
    ]


def query_sales_performance(
    seller_ids: Optional[list[int]] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    company_id: Optional[int] = None,
) -> tuple[pd.DataFrame, None, dict]:
    """
    Consulta consolidada de performance de vendas.

    Returns:
        (df_daily, None, cards_dict) — df_daily com colunas [date, realized, meta];
        cards_dict com os KPIs agregados do período.
    """
    _empty = (pd.DataFrame(), None, {"meta": 0, "realizado": 0, "ticket_medio": 0})

    # Se filtro por empresa mas sem vendedor, busca vendedores elegíveis
    resolved_sellers = seller_ids
    if company_id is not None and not resolved_sellers:
        slist = get_sellers(start_date, end_date, company_id)
        resolved_sellers = [s["id"] for s in slist] or [-1]

    # WHERE para Metas (empresa = 0, centralizado)
    where_meta = _build_where(
        _period_where("F", start_date, end_date),
        _sellers_where("F", resolved_sellers),
        "F.id_empresa = 0",
    )

    # WHERE para Realizado (filtra empresa se fornecida)
    empresa_real = f"F.id_empresa = {company_id}" if company_id is not None else "F.id_empresa > 0"
    where_real = _build_where(
        _period_where("F", start_date, end_date),
        _sellers_where("F", resolved_sellers),
        empresa_real,
    )

    q_daily = f"""
        SELECT date, SUM(realized) AS realized, SUM(meta) AS meta
        FROM (
            SELECT F.id_tempo AS date, SUM(F.valor_realizado) AS realized, 0::numeric AS meta
            FROM fato_vendasdiarias F {where_real} GROUP BY F.id_tempo
            UNION ALL
            SELECT F.id_tempo AS date, 0::numeric AS realized, SUM(F.valor_meta_diaria) AS meta
            FROM fato_vendasdiarias F {where_meta} GROUP BY F.id_tempo
        ) sub
        GROUP BY date ORDER BY date ASC
    """

    q_summary = f"""
        WITH stats_per_seller AS (
            SELECT 
                id_vendedor,
                SUM(valor_realizado) as v_realizado,
                SUM(valor_devolucao) as v_devolucao,
                SUM(valor_cancelado) as v_cancelado,
                SUM(valor_desconto) as v_desconto,
                SUM(qtd_transacoes) as v_tkts,
                (
                    SELECT (F2.valor_comissao / NULLIF(F2.valor_realizado, 0))
                    FROM fato_vendasdiarias F2
                    WHERE F2.id_vendedor = F.id_vendedor
                      AND F2.id_tempo >= '2026-01-01'
                      AND F2.valor_comissao > 0 
                      AND F2.valor_realizado > 0
                    ORDER BY F2.id_tempo DESC LIMIT 1
                ) as v_taxa
            FROM fato_vendasdiarias F
            {where_real}
            GROUP BY id_vendedor
        ),
        meta_calc AS (
            SELECT COALESCE(SUM(meta_vendedor), 0) as meta_total
            FROM (
                SELECT id_vendedor, MAX(valor_meta_mensal) AS meta_vendedor
                FROM fato_vendasdiarias F {where_meta}
                GROUP BY id_vendedor
            ) sub
        )
        SELECT
            (SELECT meta_total FROM meta_calc) AS meta,
            COALESCE(SUM(v_realizado), 0) AS realizado,
            COALESCE(SUM(v_devolucao), 0) AS devolucao,
            COALESCE(SUM(v_cancelado), 0) AS cancelado,
            COALESCE(SUM(v_realizado * COALESCE(v_taxa, 0.01)), 0) AS comissao,
            COALESCE(SUM(v_desconto),  0) AS desconto,
            COALESCE(SUM(v_tkts),      0) AS tkts,
            CASE WHEN COALESCE(SUM(v_tkts), 0) > 0
                 THEN COALESCE(SUM(v_realizado), 0) / NULLIF(SUM(v_tkts), 0)
                 ELSE 0
            END AS ticket_medio
        FROM stats_per_seller
    """

    q_ranking = f"""
        SELECT V.Nome_Comercial AS name, COALESCE(SUM(F.valor_realizado), 0) AS realized
        FROM fato_vendasdiarias F
        JOIN dim_vendedor V ON V.Id_Vendedor = F.id_vendedor
        {where_real}
        GROUP BY V.Nome_Comercial
        ORDER BY realized DESC
        LIMIT 5
    """

    df_daily   = _read(q_daily)
    df_summary = _read(q_summary)
    df_ranking = _read(q_ranking)

    if df_summary.empty:
        return _empty

    # Preenche NaNs com 0 para evitar erros de conversão no callback
    cards = df_summary.iloc[0].fillna(0).to_dict()
    # Garante que ranking e outras chaves necessárias existam
    cards["ranking"] = df_ranking.to_dict("records") if not df_ranking.empty else []

    # Adiciona chaves faltantes com valor 0 se necessário
    expected_keys = ["meta", "realizado", "devolucao", "cancelado", "desconto", "comissao", "tkts", "ticket_medio"]
    for key in expected_keys:
        if key not in cards:
            cards[key] = 0

    return df_daily, None, cards
