import pandas as pd
import logging

log = logging.getLogger("etl.transform")

def transform_sales_data(data_dict, target_date):
    """
    Transforma e consolida os dados brutos (Bronze) para o Schema Estrela (Gold).
    
    Etapas:
    1. Validação de integridade.
    2. Criação de base única (Vendedor + Empresa).
    3. Consolidação de Realizado (Vendas - Devoluções).
    4. Cálculo de Metas e Comissões.
    5. Mapeamento para o Schema do DW.
    """
    log.info(f"Transformando dados para a data: {target_date}")
    
    # 1. Verificação de Dados
    if not data_dict:
        return pd.DataFrame()

    df_vendas = data_dict.get('vendas', pd.DataFrame())
    df_dev    = data_dict.get('devolucoes', pd.DataFrame())
    df_canc   = data_dict.get('canceladas', pd.DataFrame())
    df_metas  = data_dict.get('metas', pd.DataFrame())

    # Se não há absolutamente nada para processar, encerra
    if all(df.empty for df in [df_vendas, df_dev, df_canc, df_metas]):
        log.warning(f"Nenhum dado encontrado para {target_date}")
        return pd.DataFrame()

    # 2. Construção da Base (Universo de Vendedores e Empresas ativos no dia)
    # Garantimos que cada combinação Vendedor/Empresa tenha uma linha
    seeds = []
    for df in [df_vendas, df_dev, df_canc, df_metas]:
        if not df.empty and 'codvend' in df.columns:
            seeds.append(df[['codvend', 'codemp']])
    
    df_fato = pd.concat(seeds).drop_duplicates().reset_index(drop=True)

    # 3. Integração das Métricas (Joins)
    # Agregamos Vendas
    if not df_vendas.empty:
        df_fato = pd.merge(df_fato, df_vendas, on=['codvend', 'codemp'], how='left')
    
    # Agregamos Devoluções
    if not df_dev.empty:
        df_fato = pd.merge(df_fato, df_dev[['codvend', 'codemp', 'vlr_devolucao']], on=['codvend', 'codemp'], how='left')
    
    # Agregamos Cancelamentos
    if not df_canc.empty:
        df_fato = pd.merge(df_fato, df_canc[['codvend', 'codemp', 'vlr_cancelada']], on=['codvend', 'codemp'], how='left')
    
    # Agregamos Metas e Regras de Comissão
    if not df_metas.empty:
        # 1. Separamos o Percentual de Comissão para aplicar em todas as filiais
        df_perc = df_metas[['codvend', 'perc_comissao']].drop_duplicates('codvend')
        df_fato = pd.merge(df_fato, df_perc, on='codvend', how='left')
        
        # 2. Agregamos a Meta Mensal apenas onde codemp é 0 (registro mestre de meta)
        df_metas_only = df_metas[['codvend', 'codemp', 'meta_mensal', 'dtinic', 'dtfin']]
        df_fato = pd.merge(df_fato, df_metas_only, on=['codvend', 'codemp'], how='left')

    # Limpeza e Padronização: 
    # Garante que colunas métricas existam mesmo que os merges tenham sido pulados por falta de dados
    for col in ['vlr_nota', 'vlr_devolucao', 'vlr_cancelada', 'meta_mensal', 'perc_comissao', 'vlr_desconto', 'qtd_transacoes']:
        if col not in df_fato.columns:
            df_fato[col] = 0

    # Transforma NaNs resultantes dos merges em Zero
    df_fato = df_fato.fillna(0)

    # 4. Cálculos de Negócio
    # --- Cálculo de Metas Diárias ---
    target_dt = pd.to_datetime(target_date)
    holidays = ['2025-12-25', '2026-01-01', '2026-02-17']
    is_holiday = target_date in holidays
    is_working_day = target_dt.dayofweek < 6 and not is_holiday
    
    def calculate_daily_goal(row):
        try:
            if not is_working_day or row['meta_mensal'] <= 0:
                return 0
            
            # Repete a lógica de dias úteis (Seg-Sab) excluindo os feriados específicos do SQL
            dr = pd.date_range(start=row['dtinic'], end=row['dtfin'])
            # Filtra Sábados (dayofweek < 6) e remove feriados
            working_days_df = dr[dr.dayofweek < 6]
            working_days_count = len([d for d in working_days_df if d.strftime('%Y-%m-%d') not in holidays])
            
            return row['meta_mensal'] / max(working_days_count, 1)
        except Exception as e:
            log.error(f"Erro ao calcular meta diária: {e}")
            return 0

    df_fato['valor_meta_diaria'] = df_fato.apply(calculate_daily_goal, axis=1)

    # --- Cálculo de Realizado Líquido e Comissão ---
    df_fato['vlr_liquido'] = (df_fato['vlr_nota'] - df_fato['vlr_devolucao']).clip(lower=0)
    df_fato['valor_comissao'] = df_fato['vlr_liquido'] * (df_fato['perc_comissao'] / 100)

    # 5. Mapeamento Final (Schema Gold)
    # Renomeamos para bater exatamente com as colunas do PostgreSQL
    df_final = pd.DataFrame({
        'id_tempo':          [target_date] * len(df_fato),
        'id_vendedor':       df_fato['codvend'].astype(int),
        'id_empresa':        df_fato['codemp'].astype(int),
        'valor_realizado':   df_fato['vlr_liquido'],
        'valor_cancelado':   df_fato['vlr_cancelada'],
        'valor_devolucao':   df_fato['vlr_devolucao'],
        'valor_comissao':    df_fato['valor_comissao'],
        'valor_meta_diaria': df_fato['valor_meta_diaria'],
        'valor_meta_mensal': df_fato['meta_mensal'],
        'valor_desconto':    df_fato.get('vlr_desconto', 0),
        'qtd_transacoes':    df_fato.get('qtd_transacoes', 0).astype(int)
    })

    log.info(f"Transformação concluída: {len(df_final)} registros.")
    return df_final
