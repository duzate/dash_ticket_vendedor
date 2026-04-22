from etl.extract import connect_oracle, extract_sales_data
from etl.transform import transform_sales_data
from etl.load_dw import connect_postgres_dw, apply_upsert_postgres
import pandas as pd
from datetime import datetime, timedelta

def load_historical_period(start_date, end_date):
    o_conn = connect_oracle()
    p_engine = connect_postgres_dw()
    
    current = datetime.strptime(start_date, '%Y-%m-%d')
    final = datetime.strptime(end_date, '%Y-%m-%d')
    
    print(f"[ETL: History] Iniciando carga de {start_date} até {end_date}...")
    
    while current <= final:
        target_str = current.strftime('%Y-%m-%d')
        print(f"\n--- Processando {target_str} ---")
        
        try:
            # 1. Extração
            raw_data = extract_sales_data(o_conn, target_str)
            
            # 2. Transformação
            df_fato = transform_sales_data(raw_data, target_str)
            
            # 3. Carga
            if not df_fato.empty:
                apply_upsert_postgres(df_fato, p_engine)
                print(f"[ETL] Sucesso para {target_str}")
            else:
                print(f"[ETL] Sem dados para {target_str}")
                
        except Exception as e:
            print(f"[ETL: Error] Erro ao carregar {target_str}: {e}")
            
        current += timedelta(days=1)

    print("\n[ETL: History] Carga finalizada!")

if __name__ == "__main__":
    # Carregando o período total de 03/2026 e parte de 04/2026
    load_historical_period('2026-02-26', '2026-04-02')
