# 🏗️ Arquitetura Técnica — Dash Ticket Vendedor

## Visão Geral

Este documento descreve a arquitetura, decisões de design e padrões técnicos implementados no Dash Ticket Vendedor.

---

## 1. Visão Geral da Arquitetura

```mermaid
graph TB
    subgraph source["📊 Fonte de Dados"]
        ERP["Oracle ERP<br/>(Sistema Transacional)"]
    end
    
    subgraph etl["🔄 Camada ETL"]
        EXTRACT["Extração<br/>(extract.py)"]
        TRANSFORM["Transformação<br/>(transform.py)"]
        LOAD["Carregamento<br/>(load_dw.py)"]
    end
    
    subgraph dw["💾 Data Warehouse"]
        POSTGRES["PostgreSQL<br/>Docker Container"]
        DIM["Tabelas Dimensionais<br/>(DIM_*)"]
        FACT["Tabelas Fatos<br/>(FACT_*)"]
    end
    
    subgraph app["🎨 Aplicação Web"]
        DASH["Dash + Plotly<br/>(Frontend Interativo)"]
        FLASK["Flask-Login<br/>(Autenticação)"]
        PROVIDER["DataProvider<br/>(Camada de Dados)"]
    end
    
    subgraph infra["🚀 Infraestrutura"]
        GUNICORN["Gunicorn<br/>(App Server)"]
        SUPERVISOR["Supervisord<br/>(Gerenciamento de Processos)"]
        DOCKER["Docker Compose<br/>(Orquestração)"]
    end
    
    ERP -->|Conexão<br/>Nativa| EXTRACT
    EXTRACT -->|Raw Data| TRANSFORM
    TRANSFORM -->|Cleaned Data| LOAD
    LOAD -->|Upsert| POSTGRES
    POSTGRES -->|DIM & FACT| DW[(Data Mart)]
    DW -->|SQL Queries| PROVIDER
    PROVIDER -->|DataFrames| DASH
    DASH -->|Usuário| FLASK
    FLASK -->|Valida| DASH
    
    GUNICORN -->|Serve| DASH
    SUPERVISOR -->|Controla| GUNICORN
    SUPERVISOR -->|Agenda| ETL[Cron Jobs]
    DOCKER -->|Orquestra| POSTGRES
    
    style source fill:#1f77b4
    style etl fill:#ff7f0e
    style dw fill:#2ca02c
    style app fill:#d62728
    style infra fill:#9467bd
```

---

## 2. Stack Tecnológico

### Backend & ETL
- **Python 3.12**: Linguagem principal, com type hints modernos
- **Dash + Plotly**: Framework web reativo para dashboards interativos
- **Flask-Login**: Camada de autenticação stateful com sessões
- **oracledb**: Driver nativo para conexão com Oracle (sem ODBC)
- **pandas**: Transformação e processamento de dados
- **PostgreSQL**: Data warehouse relacional

### Infraestrutura
- **Docker & Docker Compose**: Containerização do PostgreSQL
- **Gunicorn**: Application Server WSGI para Dash
- **Supervisord**: Gerenciador de processos (serviços + cron jobs)
- **Linux systemd**: Serviços de inicialização e timers

---

## 3. Padrões Arquiteturais

### 3.1 Clean Architecture
O projeto segue camadas bem separadas:

```
src/
├── dashboard/          # Presentation Layer (UI/Callbacks)
├── data/
│   ├── data_provider.py  # Application Layer (Business Logic)
│   └── etl/              # Data Layer (Extraction & Loading)
└── shared/             # Utilities & Constants
```

**Benefícios:**
- Separação de responsabilidades clara
- Fácil de testar cada camada independentemente
- Baixo acoplamento entre módulos

### 3.2 ETL Pipeline Pattern
O pipeline segue o padrão clássico **Extract → Transform → Load**:

```mermaid
sequenceDiagram
    participant Scheduler as Supervisor<br/>(Scheduler)
    participant Runner as runner.py<br/>(Orchestrator)
    participant Extractor as extract.py<br/>(Oracle)
    participant Transformer as transform.py<br/>(Transform)
    participant Loader as load_dw.py<br/>(PostgreSQL)
    
    Scheduler->>Runner: Inicia ETL Diário (D-1)
    Runner->>Extractor: get_sales_data()
    Extractor-->>Runner: Raw DataFrame
    Runner->>Transformer: process_sales()
    Transformer-->>Runner: Cleaned DataFrame
    Runner->>Loader: upsert_fact_sales()
    Loader-->>Runner: n_rows_inserted
    Runner->>Runner: Log Success
```

**Características:**
- **Idempotência**: Usa UPSERT em vez de INSERT (seguro para re-runs)
- **Logging Detalhado**: Rastreia cada inserção/atualização
- **Agendamento**: Executa daily D-1 via `supervisord`

### 3.3 Role-Based Access Control (RBAC)
Três camadas de autorização:

```mermaid
graph TD
    LOGIN["Login (Flask-Login)"]
    ROLE["Get Role (DB)"]
    FILTER["Apply Data Filter<br/>por Perfil"]
    RENDER["Render Dashboard"]
    
    LOGIN -->|user_id| ROLE
    ROLE -->|role_id| FILTER
    FILTER -->|Restrito| RENDER
    
    subgraph Admin["ADMIN"]
        A["Visão Completa"]
    end
    
    subgraph Manager["MANAGER"]
        M["Apenas seus<br/>subordinados"]
    end
    
    subgraph Seller["SELLER"]
        S["Apenas seus<br/>números"]
    end
```

---

## 4. Camadas Principais

### 4.1 Frontend (Dash + Plotly)
**Arquivo Principal:** `src/dashboard/app.py`

**Responsabilidades:**
- Inicializar aplicação Dash
- Registrar callbacks (interatividade)
- Configurar Flask-Login
- Servir assets (CSS/JS)

**Padrão de Callbacks:**
```python
@app.callback(
    Output('kpi-card', 'children'),
    Input('filter-date', 'value'),
    State('user-id', 'data'),
    prevent_initial_call=True
)
def update_kpi(selected_date, user_id):
    data = data_provider.get_kpi_data(user_id, selected_date)
    return render_kpi_card(data)
```

### 4.2 Autenticação (Flask-Login)
**Arquivo Principal:** `src/dashboard/auth.py`

**Features:**
- Armazenamento de credenciais em PostgreSQL (hash bcrypt)
- Sessões stateful com cookies seguros
- Fallback hardcoded (`admin/admin123`) para recuperação
- Perfis armazenados no banco (ADMIN, MANAGER, SELLER)

**Fluxo:**
1. Usuário submete login
2. Validação contra tabela `dash_users`
3. Se válido → sessão criada
4. Cada requisição → middleware verifica sessão

### 4.3 Data Provider (Business Logic)
**Arquivo Principal:** `src/data/data_provider.py`

**Responsabilidades:**
- Queries otimizadas ao DW
- Aplicar filtros baseados em perfil
- Processar dados para visualização
- Cache em memória (quando apropriado)

**Exemplo:**
```python
def get_seller_performance(seller_id: int, start_date, end_date):
    # Query com WHERE restritivo
    query = f"""
    SELECT fact.*, dim_seller.name
    FROM fact_sales fact
    JOIN dim_seller ON fact.seller_id = dim_seller.id
    WHERE fact.seller_id = {seller_id}
    AND fact.date BETWEEN '{start_date}' AND '{end_date}'
    """
    return pd.read_sql(query, self.dw_conn)
```

### 4.4 ETL Pipeline
**Diretório:** `src/data/etl/`

**Componentes:**

| Arquivo | Responsabilidade |
|---------|------------------|
| `runner.py` | Orquestração e scheduling |
| `extract.py` | Conexão Oracle e extração raw |
| `transform.py` | Limpeza, validação e transformação |
| `load_dw.py` | UPSERT em PostgreSQL |
| `sql_ddl.py` | Criação de tabelas e índices |
| `sync_dimensions.py` | Sincronização de dimensões (SCD Type 1) |
| `sync_periods.py` | Calendário e períodos de relatório |

---

## 5. Decisões de Design

### 5.1 Por que PostgreSQL em vez de Oracle?
- **DW Dedicado**: Separa transacional (ERP) de analítico (DW)
- **Custo**: Sem licenças Oracle adicionais
- **Docker**: Fácil de replicar em múltiplos ambientes
- **Índices**: Otimizado para queries OLAP

### 5.2 Por que Dash em vez de Tableau/Power BI?
- **Código**: Tudo em Python (mesmo stack do ETL)
- **Customização**: Componentes React.js (Plotly) personalizados
- **Glassmorphism**: Design moderno sem bibliotecas pesadas
- **Sem Licenças**: Open source + escalável

### 5.3 Por que oracledb em vez de cx_Oracle?
- **Driver Nativo**: Sem dependência de Oracle Client libraries
- **Performance**: Mais rápido em grandes extrações
- **Modernidade**: Suportado oficialmente pela Oracle

### 5.4 Supervisord em vez de systemd apenas
- **Multi-processo**: Gerencia Gunicorn + cron ETL
- **Auto-restart**: Reinicia serviços em caso de crash
- **Logs Centralizados**: Stdout/stderr capturados

---

## 6. Fluxo de Dados Completo

```mermaid
graph LR
    A["🕐 03:00 AM<br/>(Cron Diário)"]
    B["runner.py<br/>Inicia"]
    C["Extract<br/>Oracle"]
    D["Transform<br/>Pandas"]
    E["Load<br/>PostgreSQL"]
    F["✅ Sucesso<br/>Log"]
    G["❌ Erro<br/>Alert"]
    
    A -->|Supervisord| B
    B -->|Pull D-1| C
    C -->|Raw DF| D
    D -->|Clean DF| E
    E -->|n_rows| F
    E -->|Exception| G
    
    H["👤 Usuário<br/>Login"]
    I["🔐 Auth<br/>Flask-Login"]
    J["📊 Dashboard<br/>Dash + Plotly"]
    K["🗄️ Query<br/>DataProvider"]
    L["📉 Visualizar<br/>KPIs"]
    
    H -->|credentials| I
    I -->|valid session| J
    J -->|filter + role| K
    K -->|SELECT| L
    L -->|interativo| J
```

---

## 7. Escalabilidade & Performance

### Cache
- **Cache em Memória**: DataFrames frequentemente acessados
- **TTL**: 5 minutos para dados de KPIs
- **Invalidação**: Manual após carga ETL

### Índices PostgreSQL
```sql
-- Índices em tabelas de fatos
CREATE INDEX idx_fact_sales_seller ON fact_sales(seller_id);
CREATE INDEX idx_fact_sales_date ON fact_sales(date_key);
CREATE INDEX idx_fact_sales_seller_date ON fact_sales(seller_id, date_key);
```

### Queries Otimizadas
- Projeção de colunas (nunca `SELECT *`)
- `WHERE` com índices
- JOINs via foreign keys
- Particionamento (se necessário em futuro)

---

## 8. Segurança

### Autenticação & Autorização
- ✅ Senhas com hash bcrypt
- ✅ Sessões stateful (Flask-Login)
- ✅ CSRF protection (via Dash)
- ✅ SQL Injection prevention (parameterized queries)

### Dados Sensíveis
- `.env` para credenciais (gitignore)
- Variáveis de ambiente apenas em runtime
- Acesso ao Oracle limitado a usuário específico

### Network
- Gunicorn em localhost (nginx como reverse proxy em produção)
- PostgreSQL em container isolado
- Firewall externo restringindo porta 8050

---

## 9. Testes

**Estrutura:**
```
tests/
├── unit/              # Testes isolados (formatters, auth)
├── integration/       # DataProvider + PostgreSQL
└── e2e/              # Dashboard + Callbacks
```

**Cobertura:**
- ✅ Autenticação (login/logout/roles)
- ✅ DataProvider (queries + filtros)
- ✅ ETL (extract/transform/load)
- ✅ Callbacks (interatividade)

---

## 10. Desenvolvimento & Debugging

### Setup Local
```bash
# 1. Virtual env
python3 -m venv venv
source venv/bin/activate

# 2. Dependências
pip install -r requirements.txt

# 3. PostgreSQL (docker)
docker-compose up -d

# 4. Migrations
python src/data/etl/sql_ddl.py

# 5. Run app
python -m src.dashboard.app
# Acesso: http://localhost:8050
```

### Logging
```python
import logging
log = logging.getLogger(__name__)
log.info("Evento importante")  # INFO
log.warning("Possível problema")  # WARNING
log.error("Erro crítico")  # ERROR
```

---

## 11. Roadmap Futuro

- [ ] GraphQL API (alternativa a REST)
- [ ] WebSockets para real-time updates
- [ ] Alertas automáticos via email/Slack
- [ ] Mobile app (React Native)
- [ ] Machine Learning para previsões
- [ ] Multi-tenancy (múltiplas empresas)

---

**Última atualização:** Maio 2026
