"""
runner.py — Orquestrador do pipeline ETL diário.

Executa o ciclo Extract → Transform → Load para o dia especificado.
Por padrão, processa D-1 (ontem).
"""

import sys
import logging
import datetime
from pathlib import Path

# Garante que o pacote etl é encontrado ao executar diretamente
sys.path.insert(0, str(Path(__file__).parent.parent))

from etl.extract import connect_oracle, extract_sales_data, extract_rankings, extract_client_profiles, extract_brand_profiles
from etl.transform import transform_sales_data
from etl.load_dw import connect_postgres_dw, apply_upsert_postgres, load_rankings, load_client_profiles, load_brand_profiles
from etl.sync_periods import sync_fiscal_periods
from etl.sync_dimensions import sync_sellers, sync_companies, sync_parceiros, sync_marcas, sync_produtos

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("etl.runner")


def _run_single_day(target_date: str, source_conn, dw_engine) -> bool:
    """Executa o pipeline para um único dia. Reutiliza conexões."""
    try:
        # 1. Extração (Bronze)
        log.info("Passo 1/3: Extração de dados do ERP Oracle para %s...", target_date)
        data_dict = extract_sales_data(source_conn, target_date)
        if not data_dict:
            log.error("Extração retornou vazio para %s.", target_date)
            return False

        # 2. Transformação (Silver → Gold)
        log.info("Passo 2/3: Transformação e consolidação de regras de negócio para %s...", target_date)
        df_fato = transform_sales_data(data_dict, target_date)
        if df_fato is None or df_fato.empty:
            log.warning("Sem movimentação para %s.", target_date)
            return True 

        # 3. Carga (Gold → DW)
        log.info("Passo 3/3: Carga UPSERT no Data Warehouse para %s...", target_date)
        apply_upsert_postgres(df_fato, dw_engine)

        # 4. Rankings (Opcional: Pode rodar apenas uma vez por dia ou no final do mês)
        # Vamos rodar sempre para manter o TOP 10 atualizado do mês
        log.info("Passo 4/4: Atualizando Rankings para %s...", target_date)
        rankings_dict = extract_rankings(source_conn, target_date)
        if rankings_dict:
            load_rankings(rankings_dict, dw_engine)
            
            if "CLIENTE" in rankings_dict:
                log.info("Passo 5/6: Atualizando Perfis dos Clientes para %s...", target_date)
                profiles_df = extract_client_profiles(source_conn, target_date, rankings_dict["CLIENTE"])
                if profiles_df is not None and not profiles_df.empty:
                    load_client_profiles(profiles_df, dw_engine)

            if "MARCA" in rankings_dict:
                log.info("Passo 6/6: Atualizando Perfis das Marcas para %s...", target_date)
                brand_profiles_df = extract_brand_profiles(source_conn, target_date, rankings_dict["MARCA"])
                if brand_profiles_df is not None and not brand_profiles_df.empty:
                    load_brand_profiles(brand_profiles_df, dw_engine)

        return True
    except Exception:
        log.exception("Erro ao processar dia %s", target_date)
        return False

def run_daily_pipeline(target_date: str | None = None, reprocess_month: bool = True) -> bool:
    """
    Executa o pipeline ETL para a data especificada.
    Por padrão, reprocessa do início do mês até a data alvo para garantir 
    que metas lançadas retroativamente sejam validadas.
    """
    if target_date is None:
        # Padrão: HOJE (para o ETL a cada 10 min atualizar as vendas em quase-tempo-real)
        target_date = datetime.datetime.now().strftime("%Y-%m-%d")

    dt_target = datetime.datetime.strptime(target_date, "%Y-%m-%d")
    
    # Define o período de processamento
    if reprocess_month:
        # Aumentamos o lookback para 45 dias para cobrir o início de ciclos
        # e o look-forward para 20 dias para garantir que as metas futuras do ciclo 
        # atual já estejam no DW para acompanhamento total.
        dt_start = dt_target - datetime.timedelta(days=60)
        dt_end   = dt_target + datetime.timedelta(days=10)
        log.info("═══ INÍCIO ETL (MODO RETROATIVO/PROJETADO) ═══ Período: %s até %s", 
                 dt_start.strftime("%Y-%m-%d"), dt_end.strftime("%Y-%m-%d"))
    else:
        dt_start = dt_target
        dt_end   = dt_target
        log.info("═══ INÍCIO ETL (MODO DIÁRIO) ═══ Data alvo: %s", target_date)

    try:
        source_conn = connect_oracle()
        dw_engine   = connect_postgres_dw()
        if source_conn is None or dw_engine is None:
            raise RuntimeError("Falha ao estabelecer conexões.")

        # Sincroniza dimensões e períodos antes de iniciar a carga de fatos
        try:
            log.info("Iniciando sincronização de dimensões e períodos...")
            sync_fiscal_periods()
            sync_sellers()
            sync_companies()
            sync_parceiros()
            sync_marcas()
            sync_produtos()
        except Exception:
            log.exception("Erro durante sincronização de dimensões. Prosseguindo com ETL de fatos...")

        all_success = True
        current_dt = dt_start
        while current_dt <= dt_end:
            current_str = current_dt.strftime("%Y-%m-%d")
            success = _run_single_day(current_str, source_conn, dw_engine)
            if not success:
                all_success = False
            current_dt += datetime.timedelta(days=1)

        if all_success:
            log.info("═══ ETL CONCLUÍDO COM SUCESSO ═══")
        else:
            log.error("═══ ETL CONCLUÍDO COM ERROS EM ALGUNS DIAS ═══")
        
        return all_success

    except Exception:
        log.exception("═══ FALHA FATAL NO ORQUESTRADOR ═══")
        return False


if __name__ == "__main__":
    date_arg = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else None
    
    # Execução a cada 10 minutos deve ser leve (sem reprocess_month por padrão).
    # O modo retroativo (pesado) só ocorre se passarmos explicitamente a flag --monthly
    do_monthly = "--monthly" in sys.argv
    
    success = run_daily_pipeline(date_arg, reprocess_month=do_monthly)
    sys.exit(0 if success else 1)
