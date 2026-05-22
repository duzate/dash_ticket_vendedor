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
def load_rankings(rankings_dict, engine):
    """
    Insere ou atualiza os rankings no Data Warehouse.
    """
    if not rankings_dict or not engine:
        return

    log.info("Iniciando carga de Rankings no Data Warehouse...")

    with engine.begin() as conn:
        for tipo, df in rankings_dict.items():
            if df.empty:
                continue
            
            data_dicts = df.to_dict(orient='records')
            
            # Limpa rankings antigos do mesmo tipo e referência para evitar duplicação em UPSERT complexo
            # Ou usa o ON CONFLICT definido no DDL
            
            upsert_query = text("""
                INSERT INTO fato_rankings (
                    dtref, id_vendedor, id_empresa, tipo, id_item, valor, posicao, label_item
                ) VALUES (
                    :dtref, :codvend, :codemp, :tipo, :id_item, :valor, :posicao, :label_item
                )
                ON CONFLICT (dtref, id_vendedor, id_empresa, tipo, posicao) DO UPDATE SET
                    id_item    = EXCLUDED.id_item,
                    valor      = EXCLUDED.valor,
                    label_item = EXCLUDED.label_item;
            """)
            
            for row in data_dicts:
                row['tipo'] = tipo # Garante que o tipo esteja no dict
                conn.execute(upsert_query, row)
                        
    log.info("Carga de Rankings finalizada.")

def load_client_profiles(df_profiles, engine):
    """
    Insere ou atualiza os perfis de clientes no Data Warehouse.
    """
    if df_profiles is None or df_profiles.empty or not engine:
        return

    log.info(f"Iniciando carga de {len(df_profiles)} Perfis de Clientes no Data Warehouse...")

    data_dicts = df_profiles.to_dict(orient='records')

    with engine.begin() as conn:
        upsert_query = text("""
            INSERT INTO fato_cliente_perfil (
                dtref, id_cliente, id_empresa, id_vendedor, top_produtos, top_vendedores, tempo_medio_compra
            ) VALUES (
                :dtref, :id_cliente, :id_empresa, :id_vendedor, CAST(:top_produtos AS JSONB), CAST(:top_vendedores AS JSONB), :tempo_medio_compra
            )
            ON CONFLICT (dtref, id_cliente, id_empresa, id_vendedor) DO UPDATE SET
                top_produtos       = EXCLUDED.top_produtos,
                top_vendedores     = EXCLUDED.top_vendedores,
                tempo_medio_compra = EXCLUDED.tempo_medio_compra;
        """)
        
        for row in data_dicts:
            conn.execute(upsert_query, row)
                    
    log.info("Carga de Perfis de Clientes finalizada.")


def load_brand_profiles(df_profiles, engine):
    """
    Insere ou atualiza os perfis de marcas no Data Warehouse.
    """
    if df_profiles is None or df_profiles.empty or not engine:
        return

    log.info(f"Iniciando carga de {len(df_profiles)} Perfis de Marcas no Data Warehouse...")

    data_dicts = df_profiles.to_dict(orient='records')

    with engine.begin() as conn:
        upsert_query = text("""
            INSERT INTO fato_marca_perfil (
                dtref, id_marca, id_empresa, id_vendedor, top_produtos
            ) VALUES (
                :dtref, :id_marca, :id_empresa, :id_vendedor, CAST(:top_produtos AS JSONB)
            )
            ON CONFLICT (dtref, id_marca, id_empresa, id_vendedor) DO UPDATE SET
                top_produtos = EXCLUDED.top_produtos;
        """)
        
        for row in data_dicts:
            conn.execute(upsert_query, row)
                    
    log.info("Carga de Perfis de Marcas finalizada.")

