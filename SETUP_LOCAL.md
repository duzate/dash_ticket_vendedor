# 🚀 Setup Local — Dash Ticket Vendedor

Guia passo-a-passo para executar o projeto em sua máquina local.

---

## Pré-requisitos

- **Python 3.12+** (ou 3.11)
- **Docker & Docker Compose** (para o PostgreSQL)
- **Git**
- **Linux/macOS** ou **WSL2** (Windows com Linux)

### Verificar Requisitos

```bash
python --version          # Python 3.12+
docker --version          # Docker 20.10+
docker-compose --version  # Docker Compose 2.0+
git --version            # Git 2.40+
```

---

## 1️⃣ Clonar o Repositório

```bash
git clone https://github.com/seu-usuario/dash_ticket_vendedor.git
cd dash_ticket_vendedor
```

---

## 2️⃣ Criar Virtual Environment

```bash
# Criar venv
python3 -m venv venv

# Ativar (Linux/macOS)
source venv/bin/activate

# Ativar (Windows - PowerShell)
.\venv\Scripts\Activate.ps1

# Ativar (Windows - CMD)
venv\Scripts\activate.bat
```

**Verificar ativação:**
```bash
which python    # Deve mostrar /path/to/venv/bin/python
python --version
```

---

## 3️⃣ Instalar Dependências

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**Esperado:**
```
Successfully installed dash-2.14.1, plotly-5.17.0, ... 
```

---

## 4️⃣ Configurar Variáveis de Ambiente

Criar arquivo `.env` na raiz do projeto:

```bash
cp .env.example .env
```

Editar `.env`:

```env
# Aplicação
FLASK_ENV=development
DEBUG=True
SECRET_KEY=sua-chave-secreta-aqui-dev-only

# PostgreSQL (Data Warehouse)
PG_USER=dashuser
PG_PASSWORD=dashpass123
PG_HOST=localhost
PG_PORT=5432
PG_DATABASE=dashboard_dw

# Oracle ERP (Opcional - para testes com ETL)
# Se não tiver acesso a um Oracle, deixe vazio
ERP_USER=seu_usuario
ERP_PASSWORD=sua_senha
ERP_DSN=seu_dsn_oracle
ERP_ENABLED=false

# Servidor
APP_HOST=localhost
APP_PORT=8050
```

---

## 5️⃣ Subir PostgreSQL com Docker

```bash
# Iniciar container PostgreSQL
docker-compose up -d

# Verificar se está rodando
docker ps
```

**Esperado:**
```
CONTAINER ID   IMAGE              NAMES
abc123def456   postgres:15        dashboard_db
```

Aguarde ~10 segundos para o banco estar pronto.

---

## 6️⃣ Inicializar Banco de Dados

```bash
# Criar tabelas
python -m src.data.etl.sql_ddl

# Criar usuário admin de recuperação
python -c "
from src.data.auth_setup import create_default_admin
create_default_admin()
print('✅ Admin padrão criado: admin/admin123')
"
```

**Verificar criação:**
```bash
# Conectar ao PostgreSQL
psql postgresql://dashuser:dashpass123@localhost:5432/dashboard_dw

# Listar tabelas
\dt

# Sair
\q
```

---

## 7️⃣ Executar a Aplicação

```bash
# Do diretório raiz
python -m src.dashboard.app

# Ou
python src/dashboard/app.py
```

**Esperado:**
```
Dash is running on http://127.0.0.1:8050

WARNING in dash._callback_context: ...
INFO:werkzeug: * Running on http://127.0.0.1:8050 (Press CTRL+C to quit)
```

---

## 8️⃣ Acessar o Dashboard

Abra seu navegador:

```
http://localhost:8050
```

**Tela de Login:**
```
Username: admin
Password: admin123
```

**Tela de Login (Alt):**
```
Username: demo
Password: demo123
```

---

## 9️⃣ (Opcional) Executar ETL Manualmente

Se tiver acesso a um Oracle ERP, pode testar o pipeline:

```bash
# Carregar setup do .env
export $(cat .env | xargs)

# Executar ETL
python -m src.data.etl.runner

# Ou com logging detalhado
python -m src.data.etl.runner --verbose
```

**Esperado:**
```
[INFO] ETL started at 2026-05-22 10:30:00
[INFO] Extracting data from Oracle...
[INFO] Rows extracted: 1,250
[INFO] Transforming...
[INFO] Loading to PostgreSQL...
[INFO] Rows inserted: 1,100
[INFO] Rows updated: 150
[INFO] ETL completed in 3m 45s ✅
```

---

## 🔟 Executar Testes

```bash
# Testes unitários
pytest tests/unit/ -v

# Testes de integração
pytest tests/integration/ -v

# Todos os testes
pytest tests/ -v --cov=src

# Apenas testes E2E (requer app rodando)
pytest tests/e2e/ -v
```

---

## ⚠️ Troubleshooting

### Porta 8050 já em uso

```bash
# Encontrar processo
lsof -i :8050

# Matar processo
kill -9 <PID>

# Ou executar em porta diferente
python src/dashboard/app.py --port 8051
```

### PostgreSQL não conecta

```bash
# Verificar container
docker ps | grep postgres

# Ver logs
docker logs dashboard_db

# Reiniciar
docker-compose restart

# Ou subir tudo de novo
docker-compose down
docker-compose up -d
```

### Módulos não encontrados

```bash
# Garantir que está no venv
source venv/bin/activate

# Reinstalar dependências
pip install -r requirements.txt --force-reinstall
```

### Arquivo `.env` não carregado

```bash
# Verificar localização
ls -la .env

# Garantir permissões
chmod 600 .env
```

---

## 📂 Estrutura de Arquivos Esperada

```
dash_ticket_vendedor/
├── .env                    # ← Você criou aqui
├── .env.example           # Template
├── requirements.txt
├── src/
│   ├── dashboard/
│   │   └── app.py         # ← Main app
│   ├── data/
│   │   ├── data_provider.py
│   │   └── etl/
│   │       ├── runner.py
│   │       └── sql_ddl.py
│   └── shared/
├── tests/
├── logs/                  # ← Criado após primeira execução
├── venv/                  # ← Seu virtual env
└── docker-compose.yml
```

---

## 🔄 Fluxo Típico de Desenvolvimento

```bash
# 1. Ativar venv
source venv/bin/activate

# 2. Ter PostgreSQL rodando (em outro terminal)
docker-compose up -d

# 3. Rodar app em modo watch
python -m src.dashboard.app

# 4. Em outro terminal, rodar testes
pytest tests/ -v --watch

# 5. Fazer mudanças no código
# (App recarrega automaticamente)

# 6. Ver logs
tail -f logs/gunicorn_err.log
```

---

## 💡 Dicas Úteis

### Hot Reload
O Dash detecta mudanças em:
- Callbacks (`src/dashboard/callbacks/`)
- Layouts (`src/dashboard/layouts/`)
- CSS (`src/dashboard/assets/`)

**Não recarrega automaticamente:**
- `app.py` (main)
- `auth.py`
- Imports de data provider

**Solução:** Ctrl+C e re-executar.

### Debug Mode
```python
# Em app.py
app.run_server(debug=True, dev_tools_hot_reload=True)
```

### Inspecionar Banco

```bash
# Conectar
psql postgresql://dashuser:dashpass123@localhost:5432/dashboard_dw

# Ver dados
SELECT COUNT(*) FROM dash_users;
SELECT * FROM dash_users LIMIT 5;

# Ver tabelas
\dt
```

### Logs em Tempo Real

```bash
# Terminal 1: Logs da app
tail -f logs/gunicorn_err.log

# Terminal 2: Logs do Docker
docker logs -f dashboard_db

# Terminal 3: Rodando a app
python -m src.dashboard.app
```

---

## 🎯 Próximos Passos

1. **Explorar o código**: Veja [ARCHITECTURE.md](ARCHITECTURE.md) para entender a estrutura
2. **Conhecer as features**: Leia [FEATURES.md](FEATURES.md) para ver capacidades
3. **Estudar o modelo**: Consulte [DATA_MODEL.md](DATA_MODEL.md) para o schema do banco
4. **Rodar os testes**: `pytest tests/` para validar tudo
5. **Mexer nos callbacks**: Modifique `src/dashboard/callbacks/` para aprender Dash

---

## 📚 Documentação Adicional

- [README.md](README.md) — Visão geral do projeto
- [ARCHITECTURE.md](ARCHITECTURE.md) — Arquitetura técnica detalhada
- [FEATURES.md](FEATURES.md) — Features e capacidades
- [DATA_MODEL.md](DATA_MODEL.md) — Schema do banco de dados

---

**Última atualização:** Maio 2026
**Testado com:** Python 3.12, Docker 24.0, PostgreSQL 15
