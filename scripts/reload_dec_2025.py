import datetime
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src/data"))

from etl.runner import run_daily_pipeline

def reload_from_dec():
    # Inicia em 26/12/2025 e vai até 31/12/2025 (já que 2026 já foi feito)
    # Ou melhor, vamos rodar até hoje para garantir redundância e consistência.
    start_date = datetime.date(2025, 12, 26)
    end_date = datetime.date(2025, 12, 31) 
    
    current = start_date
    print(f"Iniciando RECARGA COMPLEMENTAR de {start_date} até {end_date}...")
    
    while current <= end_date:
        date_str = current.strftime("%Y-%m-%d")
        print(f"\n>>> Processando: {date_str}")
        success = run_daily_pipeline(date_str, reprocess_month=False)
        if not success:
            print(f"!!! Falha no dia {date_str}")
        current += datetime.timedelta(days=1)
    
    print("\n✅ Recarga complementar de Dezembro/2025 finalizada.")

if __name__ == "__main__":
    reload_from_dec()
