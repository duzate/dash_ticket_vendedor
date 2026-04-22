import os
import pandas as pd
import oracledb
import datetime
from dotenv import load_dotenv

load_dotenv()

def connect_oracle():
    """Conecta ao banco Oracle do ERP usando as credenciais do .env."""
    try:
        user = os.environ.get("ERP_USER")
        pwd = os.environ.get("ERP_PASSWORD")
        dsn = os.environ.get("ERP_DSN")  # Ex: 192.168.0.10:1521/ERP
        
        if not user or not pwd:
            print("[Aviso] Credenciais ERP_USER não encontradas no .env!")
            return None
            
        print(f"[ETL] Conectando ao Banco ERP em {dsn}...")
        conn = oracledb.connect(user=user, password=pwd, dsn=dsn)
        return conn
    except Exception as e:
        print(f"[ERROR] Conexão com ERP Oracle falhou: {e}")
        return None

def extract_sales_data(source_conn, target_date=None):
    """
    Extracts raw sales data from the source (ERP/System).
    We extract day-by-day (D-1) by default to not overwhelm the DB.
    """
    if target_date is None:
        target_date = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        
    print(f"[ETL: Extract] Buscando dados brutos (Bronze) de Vendas, Devoluções e Metas para o dia: {target_date}...")

    # 1. Extração de Vendas (Grau: Diário por Vendedor)
    q_vendas = f"""
        SELECT 
            TRUNC(CAB.DTENTSAI) AS data_ref,
            CAB.CODEMP AS codemp,
            CAB.CODVEND AS codvend,
            SUM(ITE.VLRTOT - ROUND(ITE.VLRDESC, 2)) AS vlr_nota,
            SUM((ROUND(ITE.VLRCUS, 2) * ITE.QTDNEG) - (ITE.VLRTOT - ROUND(ITE.VLRDESC, 2))) AS vlr_desconto,
            COUNT(DISTINCT CAB.NUNOTA) AS qtd_transacoes
        FROM SANKHYA.TGFCAB CAB
        JOIN SANKHYA.TGFITE ITE ON ITE.NUNOTA = CAB.NUNOTA
        WHERE TRUNC(CAB.DTENTSAI) = TO_DATE('{target_date}', 'YYYY-MM-DD')
          AND CAB.CODTIPOPER IN (3107,3108,3109,3112,3200,3207,3216,3217)
          AND CAB.STATUSNFE = 'A'
        GROUP BY TRUNC(CAB.DTENTSAI), CAB.CODEMP, CAB.CODVEND
    """

    # 2. Extração de Devoluções
    q_devolucao = f"""
        SELECT 
            TRUNC(CAB.DTENTSAI) AS data_ref,
            CAB.CODEMP AS codemp,
            CAB.CODVEND AS codvend,
            SUM(ITE.VLRTOT - ITE.VLRDESC) AS vlr_devolucao
        FROM SANKHYA.TGFCAB CAB
        JOIN SANKHYA.TGFITE ITE ON ITE.NUNOTA = CAB.NUNOTA
        WHERE TRUNC(CAB.DTENTSAI) = TO_DATE('{target_date}', 'YYYY-MM-DD')
          AND CAB.CODTIPOPER IN (2200,2201,2209)
        GROUP BY TRUNC(CAB.DTENTSAI), CAB.CODEMP, CAB.CODVEND
    """

    # 3. Extração de Canceladas
    q_cancelada = f"""
        SELECT 
            TRUNC(CAN.DTNEG) AS data_ref,
            EXC.CODEMP AS codemp,
            EXC.CODVEND AS codvend,
            SUM(ITE_X.VLRTOT - ITE_X.VLRDESC) AS vlr_cancelada
        FROM SANKHYA.TGFCAN CAN
        JOIN SANKHYA.TGFCAB_EXC EXC ON EXC.NUNOTA = CAN.NUNOTA
        JOIN SANKHYA.TGFITE_EXC ITE_X ON ITE_X.NUNOTA = EXC.NUNOTA
        WHERE TRUNC(CAN.DTNEG) = TO_DATE('{target_date}', 'YYYY-MM-DD')
          AND EXC.CODTIPOPER IN (3107,3108,3109,3112,3200,3207,3216,3217)
        GROUP BY TRUNC(CAN.DTNEG), EXC.CODEMP, EXC.CODVEND
    """

    # 4. Extração de Metas (Vigentes para a data)
    q_meta = f"""
        SELECT 
            VEN.CODVEND AS codvend,
            0 as codemp,
            VEND.VLRMETAVENDEDOR AS meta_mensal,
            VEND.PERCCOMISSAO AS perc_comissao,
            MET.DTINIC, MET.DTFIN
        FROM SANKHYA.AD_METAVENDEDOR VEND
        JOIN SANKHYA.AD_METAVENDA MET ON VEND.CODMETAVENDA = MET.CODMETAVENDA
        JOIN SANKHYA.TGFVEN VEN ON VEN.CODVEND = VEND.CODVEND
        WHERE TO_DATE('{target_date}', 'YYYY-MM-DD') BETWEEN MET.DTINIC AND MET.DTFIN
    """

    try:
        df_vendas = pd.read_sql(q_vendas, con=source_conn)
        df_devolucoes = pd.read_sql(q_devolucao, con=source_conn)
        df_canceladas = pd.read_sql(q_cancelada, con=source_conn)
        df_metas = pd.read_sql(q_meta, con=source_conn)
        
        # Padroniza nomes colunas
        for df in [df_vendas, df_devolucoes, df_canceladas, df_metas]:
            df.columns = [c.lower() for c in df.columns]

        return {
            "vendas": df_vendas,
            "devolucoes": df_devolucoes,
            "canceladas": df_canceladas,
            "metas": df_metas
        }
    except Exception as e:
        print(f"[ERROR] Falha ao extrair dados granulares: {e}")
        return None
