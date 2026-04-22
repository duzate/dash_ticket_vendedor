import datetime
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src/data"))

from etl.runner import run_daily_pipeline

def reload_full_year():
    start_date = datetime.date(2026, 1, 1)
    # Re-processa até o final do ciclo de Abril (25/04) para garantir metas futuras
    end_date = datetime.date(2026, 4, 30) 
    
    current = start_date
    print(f"Iniciando RECARGA TOTAL de {start_date} até {end_date}...")
    
    while current <= end_date:
        date_str = current.strftime("%Y-%m-%d")
        print(f"\n>>> Processando: {date_str}")
        # Usamos reprocess_month=False no runner para ele não tentar fazer lookback 
        # recursivo, apenas processar o dia específico no loop.
        success = run_daily_pipeline(date_str, reprocess_month=False)
        if not success:
            print(f"!!! Falha no dia {date_str}")
        current += datetime.timedelta(days=1)

if __name__ == "__main__":
    reload_full_year()
