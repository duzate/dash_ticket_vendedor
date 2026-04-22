import os
import sys
import pandas as pd
from pathlib import Path
from sqlalchemy import text

# Add root to sys.path
_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(_ROOT / "src" / "data"))

from etl.extract import connect_oracle
from etl.load_dw import connect_postgres_dw

def sync_sellers():
    oracle_conn = connect_oracle()
    pg_engine = connect_postgres_dw()
    
    if not oracle_conn:
        return

    print("[SYNC] Sincronizando Dim_Vendedor...")
    q_vendedores = """
        SELECT CODVEND AS id_vendedor, APELIDO AS nome_comercial, ATIVO AS ativo, EMAIL AS email
        FROM SANKHYA.TGFVEN
    """
    df_ven = pd.read_sql(q_vendedores, con=oracle_conn)
    df_ven.columns = [c.lower() for c in df_ven.columns]
    
    with pg_engine.begin() as conn:
        for idx, row in df_ven.iterrows():
            upsert_q = text("""
                INSERT INTO dim_vendedor (id_vendedor, nome_comercial)
                VALUES (:id_vendedor, :nome_comercial)
                ON CONFLICT (id_vendedor) DO UPDATE SET
                    nome_comercial = EXCLUDED.nome_comercial;
            """)
            conn.execute(upsert_q, row.to_dict())
    
    print(f"[SYNC] {len(df_ven)} vendedores sincronizados.")
    oracle_conn.close()

def sync_companies():
    oracle_conn = connect_oracle()
    pg_engine = connect_postgres_dw()
    
    if not oracle_conn:
        return

    print("[SYNC] Sincronizando Dim_Empresa...")
    q_emp = "SELECT CODEMP AS id_empresa, RAZAOSOCIAL AS nome FROM SANKHYA.TSIEMP"
    df_emp = pd.read_sql(q_emp, con=oracle_conn)
    df_emp.columns = [c.lower() for c in df_emp.columns]
    
    with pg_engine.begin() as conn:
        # Add virtual company 0 for metas
        conn.execute(text("INSERT INTO dim_empresa (id_empresa, nome) VALUES (0, 'CORPORATIVO (METAS)') ON CONFLICT DO NOTHING"))
        
        for idx, row in df_emp.iterrows():
            upsert_q = text("""
                INSERT INTO dim_empresa (id_empresa, nome)
                VALUES (:id_empresa, :nome)
                ON CONFLICT (id_empresa) DO UPDATE SET nome = EXCLUDED.nome;
            """)
            conn.execute(upsert_q, row.to_dict())
            
    print(f"[SYNC] {len(df_emp)} empresas sincronizadas.")
    oracle_conn.close()

if __name__ == "__main__":
    sync_sellers()
    sync_companies()
