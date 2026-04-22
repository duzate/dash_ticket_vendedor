import os
import pandas as pd
import logging
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
log = logging.getLogger("etl.load")

def connect_postgres_dw():
    """Conexão com PostgreSQL Data Warehouse via SQLAlchemy."""
    user = os.environ.get("POSTGRES_USER", "dw_admin")
    pwd  = os.environ.get("POSTGRES_PASSWORD", "dw_super_password123")
    db   = os.environ.get("POSTGRES_DB", "sankhya_dw")
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5433")
    
    connection_string = f"postgresql+psycopg2://{user}:{pwd}@{host}:{port}/{db}"
    try:
        engine = create_engine(connection_string)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return engine
    except Exception as e:
        log.error(f"Falha na conexão PostgreSQL DW: {e}")
        return None

def apply_upsert_postgres(df_fato, engine):
    """
    Insere ou atualiza registros no PostgreSQL usando a regra de CONFLICT.
    Garante sincronização da Dim_Tempo antes da carga.
    """
    if df_fato.empty or not engine:
        return

    log.info(f"Iniciando UPSERT de {len(df_fato)} registros no Data Warehouse...")

    data_dicts = df_fato.to_dict(orient='records')
    unique_dates = df_fato['id_tempo'].unique()
    
    with engine.begin() as conn:
        # 1. Garantir Dim_Tempo para todas as datas presentes no DataFrame
        # Isso evita erros de chave estrangeira se o ETL rodar retroativo
        tempo_query = text("""
            INSERT INTO dim_tempo (id_tempo, ano, mes, dia, trimestre)
            VALUES (:id_tempo, 
                    CAST(SUBSTRING(:id_tempo, 1, 4) AS INTEGER), 
                    CAST(SUBSTRING(:id_tempo, 6, 2) AS INTEGER), 
                    CAST(SUBSTRING(:id_tempo, 9, 2) AS INTEGER), 
                    EXTRACT(QUARTER FROM CAST(:id_tempo AS DATE)))
            ON CONFLICT (id_tempo) DO NOTHING;
        """)
        
        for dt in unique_dates:
            conn.execute(tempo_query, {"id_tempo": dt})

        # 2. UPSERT na Fato_VendasDiarias
        # Conflito em (id_tempo, id_vendedor, id_empresa)
        upsert_query = text("""
            INSERT INTO fato_vendasdiarias (
                id_tempo, id_vendedor, id_empresa, valor_realizado, valor_cancelado, 
                valor_devolucao, valor_comissao, valor_meta_diaria, valor_meta_mensal, valor_desconto, qtd_transacoes
            ) VALUES (
                :id_tempo, :id_vendedor, :id_empresa, :valor_realizado, :valor_cancelado, 
                :valor_devolucao, :valor_comissao, :valor_meta_diaria, :valor_meta_mensal, :valor_desconto, :qtd_transacoes
            )
            ON CONFLICT (id_tempo, id_vendedor, id_empresa) DO UPDATE SET
                valor_realizado    = EXCLUDED.valor_realizado,
                valor_cancelado    = EXCLUDED.valor_cancelado,
                valor_devolucao    = EXCLUDED.valor_devolucao,
                valor_comissao     = EXCLUDED.valor_comissao,
                valor_meta_diaria  = EXCLUDED.valor_meta_diaria,
                valor_meta_mensal  = EXCLUDED.valor_meta_mensal,
                valor_desconto     = EXCLUDED.valor_desconto,
                qtd_transacoes     = EXCLUDED.qtd_transacoes;
        """)
        
        conn.execute(upsert_query, data_dicts)
                        
    log.info(f"Carga finalizada com sucesso.")
