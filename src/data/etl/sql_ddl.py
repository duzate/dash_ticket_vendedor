# etl/sql_ddl.py
# PostgreSQL DDL — Schema completo do Data Warehouse

SQL_CREATE_DW_SCHEMA = """
-- ====================================================================
-- DIMENSÕES
-- ====================================================================

CREATE TABLE IF NOT EXISTS Dim_Tempo (
    Id_Tempo     VARCHAR(10) PRIMARY KEY,  -- 'YYYY-MM-DD'
    Ano          INTEGER,
    Mes          INTEGER,
    Dia          INTEGER,
    Trimestre    INTEGER,
    Nome_Mes     VARCHAR(20),
    Dia_Da_Semana VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS Dim_Vendedor (
    Id_Vendedor   INTEGER PRIMARY KEY,
    Nome_Comercial VARCHAR(200),
    Nivel_Acesso  VARCHAR(50),
    Id_Gestor     INTEGER,
    Equipe        VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS Dim_StatusPedido (
    Id_Status INTEGER PRIMARY KEY,
    Descricao VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS Dim_Empresa (
    Id_Empresa INTEGER PRIMARY KEY,
    Nome       VARCHAR(200)
);

CREATE TABLE IF NOT EXISTS Dim_Parceiro (
    Id_Parceiro   INTEGER PRIMARY KEY,
    Nome_Parceiro VARCHAR(200)
);

CREATE TABLE IF NOT EXISTS Dim_Marca (
    Id_Marca   INTEGER PRIMARY KEY,
    Nome_Marca VARCHAR(200)
);

CREATE TABLE IF NOT EXISTS Dim_Produto (
    Id_Produto   INTEGER PRIMARY KEY,
    Nome_Produto VARCHAR(200),
    Refforn      VARCHAR(100),
    Complemento  VARCHAR(200)
);

ALTER TABLE Dim_Produto ADD COLUMN IF NOT EXISTS Refforn VARCHAR(100);
ALTER TABLE Dim_Produto ADD COLUMN IF NOT EXISTS Complemento VARCHAR(200);

-- Períodos fiscais usados no selector de competência do Dashboard
CREATE TABLE IF NOT EXISTS Dim_Tempo_Ref (
    DtRef  VARCHAR(10) PRIMARY KEY,  -- 'YYYY-MM-DD' data de referência do mês
    DtInic VARCHAR(10) NOT NULL,     -- 'YYYY-MM-DD' primeiro dia útil / calendário
    DtFin  VARCHAR(10) NOT NULL,     -- 'YYYY-MM-DD' último  dia útil / calendário
    Label  VARCHAR(50)               -- Rótulo amigável  ex: 'Abril / 2026'
);

-- ====================================================================
-- FATOS
-- ====================================================================

-- Regra de Empresa:
--   id_empresa  = 0  → registro de META (centralizado, sem empresa)
--   id_empresa  > 0  → registro de REALIZADO / DEVOLUÇÃO / DESCONTO (por filial)
CREATE TABLE IF NOT EXISTS Fato_VendasDiarias (
    Id_Fato          SERIAL PRIMARY KEY,
    Id_Tempo         VARCHAR(10)     NOT NULL,
    Id_Vendedor      INTEGER         NOT NULL,
    Id_Empresa       INTEGER         NOT NULL DEFAULT 0,
    Valor_Meta_Diaria  NUMERIC(15,2) NOT NULL DEFAULT 0,
    Valor_Meta_Mensal  NUMERIC(15,2) NOT NULL DEFAULT 0,
    Valor_Realizado    NUMERIC(15,2) NOT NULL DEFAULT 0,
    Valor_Devolucao    NUMERIC(15,2) NOT NULL DEFAULT 0,
    Valor_Cancelado    NUMERIC(15,2) NOT NULL DEFAULT 0,
    Valor_Comissao     NUMERIC(15,2) NOT NULL DEFAULT 0,
    Valor_Desconto     NUMERIC(15,2) NOT NULL DEFAULT 0,
    Qtd_Transacoes     INTEGER       NOT NULL DEFAULT 0,
    CONSTRAINT fk_fato_vendedor
        FOREIGN KEY (Id_Vendedor) REFERENCES Dim_Vendedor(Id_Vendedor),
    CONSTRAINT unique_tempo_vendedor_empresa
        UNIQUE (Id_Tempo, Id_Vendedor, Id_Empresa)
);

-- ====================================================================
-- RANKINGS
-- ====================================================================
CREATE TABLE IF NOT EXISTS Fato_Rankings (
    Id_Ranking   SERIAL PRIMARY KEY,
    DtRef        VARCHAR(10) NOT NULL, -- 'YYYY-MM-DD' (início do mês)
    Id_Vendedor  INTEGER NOT NULL,
    Id_Empresa   INTEGER NOT NULL,
    Tipo         VARCHAR(20) NOT NULL, -- 'CLIENTE', 'MARCA', 'PRODUTO'
    Id_Item      INTEGER NOT NULL,
    Valor        NUMERIC(15,2) NOT NULL,
    Posicao      INTEGER NOT NULL,
    Label_Item   VARCHAR(200),         -- Nome denormalizado para performance rápida
    CONSTRAINT unique_rank_ref_vendedor_empresa_tipo_pos
        UNIQUE (DtRef, Id_Vendedor, Id_Empresa, Tipo, Posicao)
);

-- ====================================================================
-- PERFIS DE CLIENTES
-- ====================================================================
CREATE TABLE IF NOT EXISTS Fato_Cliente_Perfil (
    Id_Perfil          SERIAL PRIMARY KEY,
    DtRef              VARCHAR(10) NOT NULL,
    Id_Cliente         INTEGER NOT NULL,
    Id_Empresa         INTEGER NOT NULL,
    Id_Vendedor        INTEGER NOT NULL DEFAULT 0,
    Top_Produtos       JSONB,
    Top_Vendedores     JSONB,
    Tempo_Medio_Compra NUMERIC(15,2),
    CONSTRAINT unique_perfil_ref_cliente_empresa_vendedor
        UNIQUE (DtRef, Id_Cliente, Id_Empresa, Id_Vendedor)
);

-- ====================================================================
-- PERFIS DE MARCAS
-- ====================================================================
CREATE TABLE IF NOT EXISTS Fato_Marca_Perfil (
    Id_Perfil          SERIAL PRIMARY KEY,
    DtRef              VARCHAR(10) NOT NULL,
    Id_Marca           INTEGER NOT NULL,
    Id_Empresa         INTEGER NOT NULL,
    Id_Vendedor        INTEGER NOT NULL DEFAULT 0,
    Top_Produtos       JSONB,
    CONSTRAINT unique_perfil_ref_marca_empresa_vendedor
        UNIQUE (DtRef, Id_Marca, Id_Empresa, Id_Vendedor)
);

-- ====================================================================
-- INDEXAÇÃO ANALÍTICA
-- ====================================================================

-- Leitura por período (filtro de competência no dash)
CREATE INDEX IF NOT EXISTS idx_fato_id_tempo
    ON Fato_VendasDiarias(Id_Tempo);

-- Leitura por vendedor
CREATE INDEX IF NOT EXISTS idx_fato_id_vendedor
    ON Fato_VendasDiarias(Id_Vendedor);

-- Leitura por empresa (filtro de filial no dash)
CREATE INDEX IF NOT EXISTS idx_fato_id_empresa
    ON Fato_VendasDiarias(Id_Empresa);

-- Leitura composta: empresa + período (query principal do dash)
CREATE INDEX IF NOT EXISTS idx_fato_empresa_tempo
    ON Fato_VendasDiarias(Id_Empresa, Id_Tempo);

-- Leitura composta: vendedor + período (query por vendedor)
CREATE INDEX IF NOT EXISTS idx_fato_vendedor_tempo
    ON Fato_VendasDiarias(Id_Vendedor, Id_Tempo);

-- ====================================================================
-- SEGURANÇA E USUÁRIOS
-- ====================================================================
CREATE TABLE IF NOT EXISTS Dash_Users (
    Id               SERIAL PRIMARY KEY,
    Username         VARCHAR(100) UNIQUE NOT NULL,
    Password         VARCHAR(100) NOT NULL,
    Role             VARCHAR(50) NOT NULL,
    Seller_Id        INTEGER,
    Managed_Sellers  INTEGER[],
    Is_Active        BOOLEAN DEFAULT TRUE
);
"""


def prepare_dw(engine):
    """
    Aplica o DDL no PostgreSQL via SQLAlchemy.
    Seguro para re-execução (IF NOT EXISTS / ON CONFLICT).
    """
    from sqlalchemy import text

    statements = [
        s.strip()
        for s in SQL_CREATE_DW_SCHEMA.split(";")
        if s.strip()
    ]

    with engine.begin() as conn:
        # Executa DDL padrão
        for stmt in statements:
            try:
                conn.execute(text(stmt))
            except Exception as e:
                print(f"[DDL] Aviso (ignorado): {e}")

        # Executa Migrações para adicionar Id_Vendedor
        migrations = [
            # Cliente Perfil
            "ALTER TABLE fato_cliente_perfil ADD COLUMN IF NOT EXISTS Id_Vendedor INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE fato_cliente_perfil DROP CONSTRAINT IF EXISTS unique_perfil_ref_cliente_empresa",
            "ALTER TABLE fato_cliente_perfil DROP CONSTRAINT IF EXISTS unique_perfil_ref_cliente_empresa_vendedor",
            "ALTER TABLE fato_cliente_perfil ADD CONSTRAINT unique_perfil_ref_cliente_empresa_vendedor UNIQUE (DtRef, Id_Cliente, Id_Empresa, Id_Vendedor)",
            
            # Marca Perfil
            "ALTER TABLE fato_marca_perfil ADD COLUMN IF NOT EXISTS Id_Vendedor INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE fato_marca_perfil DROP CONSTRAINT IF EXISTS unique_perfil_ref_marca_empresa",
            "ALTER TABLE fato_marca_perfil DROP CONSTRAINT IF EXISTS unique_perfil_ref_marca_empresa_vendedor",
            "ALTER TABLE fato_marca_perfil ADD CONSTRAINT unique_perfil_ref_marca_empresa_vendedor UNIQUE (DtRef, Id_Marca, Id_Empresa, Id_Vendedor)"
        ]
        
        for mig in migrations:
            try:
                conn.execute(text(mig))
            except Exception as e:
                print(f"[DDL: Migration] Aviso: {e}")

    print("[DDL] ✓ Schema do DW e Migrações aplicados com sucesso.")


if __name__ == "__main__":
    from data_provider import get_dw_engine
    prepare_dw(get_dw_engine())
