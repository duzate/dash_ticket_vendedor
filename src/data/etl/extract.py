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
def extract_rankings(source_conn, target_date=None):
    """
    Extrai o TOP 10 de Clientes, Marcas e Produtos para o mês da target_date.
    """
    if target_date is None:
        target_date = datetime.datetime.now().strftime('%Y-%m-%d')
    
    # Início e fim do mês
    dt = datetime.datetime.strptime(target_date, '%Y-%m-%d')
    start_month = dt.replace(day=1).strftime('%Y-%m-%d')
    # Simplificação: assume fim do mês como 31 dias depois ou similar, 
    # mas o Oracle BETWEEN resolverá se usarmos o próximo mês.
    
    print(f"[ETL: Extract] Extraindo Rankings para o período de {start_month}...")

    # 1. TOP 10 Clientes (Agrupado por Empresa/Vendedor/Global)
    q_clientes = f"""
        SELECT * FROM (
            SELECT 
                agg.codemp, agg.codvend, agg.id_item, agg.label_item, agg.valor,
                ROW_NUMBER() OVER (PARTITION BY agg.codemp, agg.codvend ORDER BY agg.valor DESC) AS posicao
            FROM (
                SELECT 
                    CAB.CODEMP AS codemp,
                    CAB.CODVEND AS codvend,
                    PAR.CODPARC AS id_item,
                    PAR.NOMEPARC AS label_item,
                    SUM(ITE.VLRTOT - ITE.VLRDESC) AS valor
                FROM SANKHYA.TGFCAB CAB
                JOIN SANKHYA.TGFPAR PAR ON PAR.CODPARC = CAB.CODPARC
                JOIN SANKHYA.TGFITE ITE ON ITE.NUNOTA = CAB.NUNOTA
                WHERE CAB.DTENTSAI >= TO_DATE('{start_month}', 'YYYY-MM-DD')
                  AND CAB.DTENTSAI <= TO_DATE('{target_date}', 'YYYY-MM-DD')
                  AND CAB.CODTIPOPER IN (3107,3108,3109,3112,3200,3207,3216,3217)
                  AND CAB.STATUSNFE = 'A'
                GROUP BY GROUPING SETS (
                    (CAB.CODEMP, CAB.CODVEND, PAR.CODPARC, PAR.NOMEPARC), -- Nível Detalhado
                    (CAB.CODVEND, PAR.CODPARC, PAR.NOMEPARC),            -- Total por Vendedor
                    (CAB.CODEMP, PAR.CODPARC, PAR.NOMEPARC),             -- Total por Empresa
                    (PAR.CODPARC, PAR.NOMEPARC)                          -- Total Geral
                )
            ) agg
        ) WHERE posicao <= 10
    """

    # 2. TOP 10 Marcas
    q_marcas = f"""
        SELECT * FROM (
            SELECT 
                agg.codemp, agg.codvend, agg.id_item, agg.label_item, agg.valor,
                ROW_NUMBER() OVER (PARTITION BY agg.codemp, agg.codvend ORDER BY agg.valor DESC) AS posicao
            FROM (
                SELECT 
                    CAB.CODEMP AS codemp,
                    CAB.CODVEND AS codvend,
                    NVL(PRO.CODMARCA, 0) AS id_item,
                    NVL(PRO.MARCA, 'SEM MARCA') AS label_item,
                    SUM(ITE.VLRTOT - ITE.VLRDESC) AS valor
                FROM SANKHYA.TGFCAB CAB
                JOIN SANKHYA.TGFITE ITE ON ITE.NUNOTA = CAB.NUNOTA
                JOIN SANKHYA.TGFPRO PRO ON PRO.CODPROD = ITE.CODPROD
                WHERE CAB.DTENTSAI >= TO_DATE('{start_month}', 'YYYY-MM-DD')
                  AND CAB.DTENTSAI <= TO_DATE('{target_date}', 'YYYY-MM-DD')
                  AND CAB.CODTIPOPER IN (3107,3108,3109,3112,3200,3207,3216,3217)
                  AND CAB.STATUSNFE = 'A'
                GROUP BY GROUPING SETS (
                    (CAB.CODEMP, CAB.CODVEND, PRO.CODMARCA, PRO.MARCA),
                    (CAB.CODVEND, PRO.CODMARCA, PRO.MARCA),
                    (CAB.CODEMP, PRO.CODMARCA, PRO.MARCA),
                    (PRO.CODMARCA, PRO.MARCA)
                )
            ) agg
        ) WHERE posicao <= 10
    """

    # 3. TOP 10 Produtos
    q_produtos = f"""
        SELECT * FROM (
            SELECT 
                agg.codemp, agg.codvend, agg.id_item, agg.label_item, agg.valor,
                ROW_NUMBER() OVER (PARTITION BY agg.codemp, agg.codvend ORDER BY agg.valor DESC) AS posicao
            FROM (
                SELECT 
                    CAB.CODEMP AS codemp,
                    CAB.CODVEND AS codvend,
                    PRO.CODPROD AS id_item,
                    PRO.DESCRPROD AS label_item,
                    SUM(ITE.VLRTOT - ITE.VLRDESC) AS valor
                FROM SANKHYA.TGFCAB CAB
                JOIN SANKHYA.TGFITE ITE ON ITE.NUNOTA = CAB.NUNOTA
                JOIN SANKHYA.TGFPRO PRO ON PRO.CODPROD = ITE.CODPROD
                WHERE CAB.DTENTSAI >= TO_DATE('{start_month}', 'YYYY-MM-DD')
                  AND CAB.DTENTSAI <= TO_DATE('{target_date}', 'YYYY-MM-DD')
                  AND CAB.CODTIPOPER IN (3107,3108,3109,3112,3200,3207,3216,3217)
                  AND CAB.STATUSNFE = 'A'
                GROUP BY GROUPING SETS (
                    (CAB.CODEMP, CAB.CODVEND, PRO.CODPROD, PRO.DESCRPROD),
                    (CAB.CODVEND, PRO.CODPROD, PRO.DESCRPROD),
                    (CAB.CODEMP, PRO.CODPROD, PRO.DESCRPROD),
                    (PRO.CODPROD, PRO.DESCRPROD)
                )
            ) agg
        ) WHERE posicao <= 10
    """

    try:
        df_cli = pd.read_sql(q_clientes, con=source_conn)
        df_mar = pd.read_sql(q_marcas,   con=source_conn)
        df_pro = pd.read_sql(q_produtos, con=source_conn)
        
        for df in [df_cli, df_mar, df_pro]:
            df.columns = [c.lower() for c in df.columns]
            df['dtref'] = start_month 
            # Normaliza nulos do GROUPING SETS para 0 (nosso padrão de dimensão 'Global')
            df['codemp']  = df['codemp'].fillna(0).astype(int)
            df['codvend'] = df['codvend'].fillna(0).astype(int)

        return {
            "CLIENTE": df_cli,
            "MARCA":   df_mar,
            "PRODUTO": df_pro
        }
    except Exception as e:
        print(f"[ERROR] Falha ao extrair rankings: {e}")
        return None

import json

def extract_client_profiles(source_conn, target_date, clients_df):
    """
    Extrai o perfil detalhado dos clientes (Top 5 Produtos, Top 3 Vendedores, Tempo Médio de Compra).
    clients_df é o DataFrame retornado na chave 'CLIENTE' por extract_rankings.
    """
    if clients_df is None or clients_df.empty:
        return pd.DataFrame()
        
    # Obtém a lista única de clientes
    client_ids = clients_df['id_item'].unique().tolist()
    client_ids = [int(c) for c in client_ids if int(c) > 0]
    
    if not client_ids:
        return pd.DataFrame()
        
    # Limita a 1000 clientes por vez para evitar erro de IN clause no Oracle
    # Como os rankings têm 10 por empresa/vendedor, não deve passar muito disso.
    if len(client_ids) > 1000:
        client_ids = client_ids[:1000]
        
    ids_str = ",".join(map(str, client_ids))
    
    # Busca dados dos últimos 6 meses para ter uma base boa para o tempo médio
    dt = datetime.datetime.strptime(target_date, '%Y-%m-%d')
    start_date = (dt - datetime.timedelta(days=180)).strftime('%Y-%m-%d')
    
    print(f"[ETL: Extract] Extraindo Perfil para {len(client_ids)} clientes...")
    
    # Query unificada de transações dos clientes nos últimos 6 meses
    q_transacoes = f"""
        SELECT 
            CAB.CODEMP AS codemp,
            CAB.CODPARC AS id_cliente,
            CAB.CODVEND AS codvend,
            VEN.APELIDO AS nome_vendedor,
            ITE.CODPROD AS codprod,
            PRO.DESCRPROD AS nome_produto,
            NVL(PRO.REFFORN, ' ') AS refforn,
            NVL(PRO.COMPLDESC, ' ') AS complemento,
            TRUNC(CAB.DTENTSAI) AS data_compra,
            SUM(ITE.VLRTOT - ITE.VLRDESC) AS valor
        FROM SANKHYA.TGFCAB CAB
        JOIN SANKHYA.TGFITE ITE ON ITE.NUNOTA = CAB.NUNOTA
        JOIN SANKHYA.TGFPRO PRO ON PRO.CODPROD = ITE.CODPROD
        JOIN SANKHYA.TGFVEN VEN ON VEN.CODVEND = CAB.CODVEND
        WHERE CAB.CODPARC IN ({ids_str})
          AND CAB.DTENTSAI >= TO_DATE('{start_date}', 'YYYY-MM-DD')
          AND CAB.DTENTSAI <= TO_DATE('{target_date}', 'YYYY-MM-DD')
          AND CAB.CODTIPOPER IN (3107,3108,3109,3112,3200,3207,3216,3217)
          AND CAB.STATUSNFE = 'A'
        GROUP BY CAB.CODEMP, CAB.CODPARC, CAB.CODVEND, VEN.APELIDO, ITE.CODPROD, PRO.DESCRPROD, PRO.REFFORN, PRO.COMPLDESC, TRUNC(CAB.DTENTSAI)
    """
    
    try:
        df = pd.read_sql(q_transacoes, con=source_conn)
        if df.empty:
            return pd.DataFrame()
            
        df.columns = [c.lower() for c in df.columns]
        
        profiles = []
        
        # Cria as combinações multi-dimensionais (codemp e codvend)
        df_global_all = df.copy()
        df_global_all['codemp'] = 0
        df_global_all['codvend'] = 0
        
        df_comp_only = df.copy()
        df_comp_only['codvend'] = 0
        
        df_vend_only = df.copy()
        df_vend_only['codemp'] = 0
        
        df_full = df.copy()
        
        df_all = pd.concat([df_global_all, df_comp_only, df_vend_only, df_full], ignore_index=True)
        
        # Agrupa por (codemp, id_cliente, codvend)
        grouped = df_all.groupby(['codemp', 'id_cliente', 'codvend'])
        
        for (codemp, id_cliente, codvend), group in grouped:
            # 1. Top 5 Produtos
            top_produtos = group.groupby(['codprod', 'nome_produto', 'refforn', 'complemento'])['valor'].sum().reset_index()
            top_produtos = top_produtos.sort_values('valor', ascending=False).head(5)
            produtos_list = [
                {
                    "nome": row['nome_produto'],
                    "valor": float(row['valor']),
                    "refforn": str(row['refforn']).strip(),
                    "complemento": str(row['complemento']).strip()
                }
                for _, row in top_produtos.iterrows()
            ]
            
            # 2. Top 3 Vendedores
            top_vends = group.groupby(['codvend', 'nome_vendedor'])['valor'].sum().reset_index()
            top_vends = top_vends.sort_values('valor', ascending=False).head(3)
            vendedores_list = [{"nome": row['nome_vendedor'], "valor": float(row['valor'])} for _, row in top_vends.iterrows()]
            
            # 3. Tempo Médio de Compra
            datas_compra = pd.Series(pd.to_datetime(group['data_compra'].unique())).sort_values()
            if len(datas_compra) > 1:
                diffs = datas_compra.diff().dt.days.dropna()
                tempo_medio = float(diffs.mean())
            else:
                tempo_medio = 0.0
                
            # DtRef é o início do mês corrente
            dtref = dt.replace(day=1).strftime('%Y-%m-%d')
                
            profiles.append({
                "dtref": dtref,
                "id_cliente": int(id_cliente),
                "id_empresa": int(codemp),
                "id_vendedor": int(codvend),
                "top_produtos": json.dumps(produtos_list),
                "top_vendedores": json.dumps(vendedores_list),
                "tempo_medio_compra": tempo_medio
            })
            
        return pd.DataFrame(profiles)
        
    except Exception as e:
        print(f"[ERROR] Falha ao extrair perfil de clientes: {e}")
        return pd.DataFrame()


def extract_brand_profiles(source_conn, target_date, brands_df):
    """
    Extrai o perfil das marcas (Top 5 Produtos mais vendidos da marca no período).
    brands_df é o DataFrame retornado na chave 'MARCA' por extract_rankings.
    """
    if brands_df is None or brands_df.empty:
        return pd.DataFrame()
        
    brand_ids = brands_df['id_item'].unique().tolist()
    brand_ids = [int(b) for b in brand_ids]
    
    if not brand_ids:
        return pd.DataFrame()
        
    ids_str = ",".join(map(str, brand_ids))
    
    dt = datetime.datetime.strptime(target_date, '%Y-%m-%d')
    start_month = dt.replace(day=1).strftime('%Y-%m-%d')
    
    print(f"[ETL: Extract] Extraindo Perfil para {len(brand_ids)} marcas no período...")
    
    q_transacoes = f"""
        SELECT 
            CAB.CODEMP AS codemp,
            NVL(PRO.CODMARCA, 0) AS id_marca,
            CAB.CODVEND AS codvend,
            PRO.CODPROD AS codprod,
            PRO.DESCRPROD AS nome_produto,
            NVL(PRO.REFFORN, ' ') AS refforn,
            NVL(PRO.COMPLDESC, ' ') AS complemento,
            SUM(ITE.VLRTOT - ITE.VLRDESC) AS valor
        FROM SANKHYA.TGFCAB CAB
        JOIN SANKHYA.TGFITE ITE ON ITE.NUNOTA = CAB.NUNOTA
        JOIN SANKHYA.TGFPRO PRO ON PRO.CODPROD = ITE.CODPROD
        WHERE NVL(PRO.CODMARCA, 0) IN ({ids_str})
          AND CAB.DTENTSAI >= TO_DATE('{start_month}', 'YYYY-MM-DD')
          AND CAB.DTENTSAI <= TO_DATE('{target_date}', 'YYYY-MM-DD')
          AND CAB.CODTIPOPER IN (3107,3108,3109,3112,3200,3207,3216,3217)
          AND CAB.STATUSNFE = 'A'
        GROUP BY CAB.CODEMP, NVL(PRO.CODMARCA, 0), CAB.CODVEND, PRO.CODPROD, PRO.DESCRPROD, PRO.REFFORN, PRO.COMPLDESC
    """
    
    try:
        df = pd.read_sql(q_transacoes, con=source_conn)
        if df.empty:
            return pd.DataFrame()
            
        df.columns = [c.lower() for c in df.columns]
        
        profiles = []
        
        # Cria as combinações multi-dimensionais (codemp e codvend)
        df_global_all = df.copy()
        df_global_all['codemp'] = 0
        df_global_all['codvend'] = 0
        
        df_comp_only = df.copy()
        df_comp_only['codvend'] = 0
        
        df_vend_only = df.copy()
        df_vend_only['codemp'] = 0
        
        df_full = df.copy()
        
        df_all = pd.concat([df_global_all, df_comp_only, df_vend_only, df_full], ignore_index=True)
        
        grouped = df_all.groupby(['codemp', 'id_marca', 'codvend'])
        
        for (codemp, id_marca, codvend), group in grouped:
            top_produtos = group.groupby(['codprod', 'nome_produto', 'refforn', 'complemento'])['valor'].sum().reset_index()
            top_produtos = top_produtos.sort_values('valor', ascending=False).head(5)
            produtos_list = [
                {
                    "nome": row['nome_produto'],
                    "valor": float(row['valor']),
                    "refforn": str(row['refforn']).strip(),
                    "complemento": str(row['complemento']).strip()
                }
                for _, row in top_produtos.iterrows()
            ]
            
            profiles.append({
                "dtref": start_month,
                "id_marca": int(id_marca),
                "id_empresa": int(codemp),
                "id_vendedor": int(codvend),
                "top_produtos": json.dumps(produtos_list)
            })
            
        return pd.DataFrame(profiles)
        
    except Exception as e:
        print(f"[ERROR] Falha ao extrair perfil de marcas: {e}")
        return pd.DataFrame()

