# 📊 Sales Dashboard — Ticket Vendedor

**Plataforma analítica de performance de vendas**, construída em Python Dash com integração ao Data Warehouse PostgreSQL (populado via ETL a partir do ERP Sankhya). Visual glassmorphism premium, autenticação segura e controle administrativo completo.

---

## 🖥️ Acesso à Aplicação

| Ambiente | URL |
|---|---|
| Produção (rede local) | http://192.168.0.110:8050 |

---

## 🔐 Autenticação e Controle de Acesso

O sistema de login é **100% baseado em banco de dados** (`dash_users` no PostgreSQL DW). Não existem usuários mocados no código — com exceção do `admin`, que é uma conta de recuperação de emergência.

### Conta de Recuperação de Emergência
| Usuário | Senha | Papel |
|---|---|---|
| `admin` | `admin123` | ADMIN |

> ⚠️ Esta conta é hardcoded somente como **fallback** caso o banco esteja inacessível. Em operação normal, todos os acessos são gerenciados pelo painel Administrativo.

### Regras de Acesso por Papel

| Papel | O que pode ver |
|---|---|
| `ADMIN` | Todos os vendedores, dashboard completo + painel de Usuários |
| `MANAGER` | Apenas os vendedores listados em `managed_sellers` |
| `SELLER` | Apenas sua própria performance (filtrado pelo `seller_id`) |

### Criando Usuários (via Painel Admin)
1. Logue com a conta `admin`
2. Clique em **"Usuários"** no cabeçalho
3. Preencha nome de usuário, senha, papel e ID do vendedor (para papel SELLER)
4. Clique em **Salvar**

> **Atenção:** Usernames são sempre convertidos para **letras minúsculas** automaticamente. Ex: `Pablo.Ferreira` → `pablo.ferreira`

---

## 🏗️ Estrutura do Projeto

```
dash_ticket_vendedor/
├── src/
│   ├── dashboard/                  # Camada de apresentação (Dash App)
│   │   ├── app.py                  # Ponto de entrada, Flask-Login, registro de callbacks
│   │   ├── auth.py                 # Autenticação, User model, filtro por papel
│   │   ├── callbacks/
│   │   │   ├── auth_callbacks.py   # Login, logout, roteamento de páginas
│   │   │   └── dashboard_callbacks.py  # KPIs, filtros, modal de usuários (Admin)
│   │   ├── layouts/
│   │   │   ├── dashboard.py        # Layout principal + header + modal de usuários
│   │   │   └── login.py            # Tela de login
│   │   ├── components/
│   │   │   └── kpi_card.py         # Componente de card de métricas
│   │   └── assets/
│   │       └── index.css           # Design system (glassmorphism, variáveis CSS)
│   │
│   ├── data/
│   │   ├── data_provider.py        # Queries ao DW PostgreSQL (KPIs, vendedores)
│   │   └── etl/
│   │       ├── runner.py           # Executor principal do ETL
│   │       ├── extract.py          # Extração do ERP Sankhya (Oracle)
│   │       ├── transform.py        # Transformações e cálculos de negócio
│   │       ├── load_dw.py          # Carga no PostgreSQL DW
│   │       ├── sync_dimensions.py  # Sincronização de dimensões (vendedores, etc.)
│   │       ├── sync_periods.py     # Geração de calendário de períodos
│   │       ├── historical_loader.py # Carga histórica inicial
│   │       └── sql_ddl.py          # DDL das tabelas do DW
│   │
│   └── shared/
│       └── utils/
│           └── formatters.py       # Formatadores de moeda, percentual, etc.
│
├── deployment/
│   ├── start.sh                    # Script de inicialização em produção
│   ├── supervisord.conf            # Configuração do Supervisord (Gunicorn + ETL)
│   └── docker-compose.yml          # Container PostgreSQL DW
│
├── .env                            # Variáveis de ambiente (credenciais) — NÃO versionar
├── .env.example                    # Template de variáveis de ambiente
└── requirements.txt                # Dependências Python
```

---

## ⚙️ Como Iniciar em Produção

```bash
# Subir toda a stack (PostgreSQL + Gunicorn + ETL)
bash deployment/start.sh
```

O script:
1. Inicia o container Docker do PostgreSQL DW
2. Encerra qualquer instância anterior do Gunicorn/Supervisord
3. Inicializa o Gunicorn (2 workers, porta 8050) via Supervisord
4. Executa o ETL de atualização de dados ao subir

### Monitoramento de Logs

```bash
# Log da aplicação (erros Gunicorn, autenticação, etc.)
tail -f logs/gunicorn_err.log

# Log do ETL (extração do Sankhya)
tail -f logs/etl_out.log
```

---

## 🗄️ Banco de Dados (PostgreSQL DW)

| Parâmetro | Valor |
|---|---|
| Host | `localhost` |
| Porta | `5433` |
| Banco | `sankhya_dw` |
| Usuário | `dw_admin` |
| Container | `dash_dw_postgres` |

### Tabela de Usuários do Dashboard

```sql
-- Estrutura da tabela dash_users
SELECT id, username, role, seller_id, is_active FROM dash_users;

-- Adicionar coluna is_active (se não existir)
ALTER TABLE dash_users ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;
```

---

## 📦 Dependências Principais

| Pacote | Finalidade |
|---|---|
| `dash` + `dash-bootstrap-components` | Framework do dashboard |
| `flask-login` | Gerenciamento de sessão e autenticação |
| `gunicorn` | Servidor WSGI de produção |
| `supervisord` | Gerenciamento de processos |
| `sqlalchemy` + `psycopg2` | Conexão com PostgreSQL DW |
| `oracledb` | Conexão com ERP Sankhya (Oracle) |

```bash
pip install -r requirements.txt
```

---

## 🔍 Checklist de Problemas Comuns

| Sintoma | Causa Provável | Solução |
|---|---|---|
| "Acesso negado" para usuário cadastrado | `is_active = FALSE` no banco | Reativar via painel Admin |
| Página não carrega (ERR_CONNECTION_RESET) | Porta 8050 ocupada por processo zumbi | `fuser -k 8050/tcp && bash deployment/start.sh` |
| Erro de coluna `is_active` no log | Schema desatualizado | `ALTER TABLE dash_users ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;` |
| Container `dash_dw_postgres` em conflito | Container já rodando | `docker start dash_dw_postgres` (sem recriar) |
| ETL não atualiza dados | Falha na conexão Oracle | Verificar `logs/etl_err.log` e credenciais no `.env` |
