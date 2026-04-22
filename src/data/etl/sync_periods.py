import sys
from pathlib import Path
from sqlalchemy import text
import pandas as pd

# Add src/data to sys.path to allow 'from etl.xxx import ...'
_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(_ROOT / "src" / "data"))

from etl.extract import connect_oracle
from etl.load_dw import connect_postgres_dw

def sync_fiscal_periods():
    print("[ETL] Sincronizando Períodos Fiscais (AD_METAVENDA) para dim_tempo_ref...")
    o_conn = connect_oracle()
    p_engine = connect_postgres_dw()
    
    # 1. Buscar períodos no Oracle
    query_oracle = "SELECT DTREF, DTINIC, DTFIN FROM AD_METAVENDA ORDER BY DTREF"
    df_periods = pd.read_sql(query_oracle, con=o_conn)
    
    if df_periods.empty:
        print("[ERROR] Nenhum período encontrado em AD_METAVENDA.")
        return

    # 2. Carregar no PostgreSQL
    with p_engine.begin() as conn:
        for _, row in df_periods.iterrows():
            dt_ref = row['DTREF'].strftime('%Y-%m-%d')
            dt_inic = row['DTINIC'].strftime('%Y-%m-%d')
            dt_fin = row['DTFIN'].strftime('%Y-%m-%d')
            
            # Gerar Label amigável (ex: Março / 2026)
            meses = {
                1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho",
                7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
            }
            dt_obj = row['DTREF']
            label = f"{meses[dt_obj.month]} / {dt_obj.year}"
            
            upsert_sql = text("""
                INSERT INTO dim_tempo_ref (dtref, dtinic, dtfin, label)
                VALUES (:ref, :inic, :fin, :label)
                ON CONFLICT (dtref) DO UPDATE SET
                    dtinic = EXCLUDED.dtinic,
                    dtfin = EXCLUDED.dtfin,
                    label = EXCLUDED.label;
            """)
            conn.execute(upsert_sql, {"ref": dt_ref, "inic": dt_inic, "fin": dt_fin, "label": label})
            print(f"[ETL] ✓ Período {dt_ref} synced ({dt_inic} -> {dt_fin})")

if __name__ == "__main__":
    sync_fiscal_periods()
