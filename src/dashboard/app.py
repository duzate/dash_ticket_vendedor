"""
app.py — Ponto de entrada da aplicação Dash (Sales Dashboard).

Responsabilidades:
    - Inicializar o app Dash com configurações corretas.
    - Configurar Flask-Login (autenticação stateful).
    - Registrar todos os callbacks (auth + dashboard).
    - Expor `server` para o Gunicorn.
"""

import os
import sys
import logging
from pathlib import Path

# ─── Resolução de caminhos ────────────────────────────────────────────────────
# Permite que os módulos locais (callbacks, layouts, etc.) e os pacotes
# das camadas de dados/shared sejam encontrados independentemente do CWD.
_DASHBOARD_DIR = Path(__file__).parent.resolve()
_ROOT          = _DASHBOARD_DIR.parent.parent

sys.path.insert(0, str(_DASHBOARD_DIR))           # dashboard/
sys.path.insert(0, str(_ROOT / "src" / "data"))   # src/data/
sys.path.insert(0, str(_ROOT / "src" / "shared")) # src/shared/

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("dashboard.app")

# ─── Imports da aplicação ────────────────────────────────────────────────────
import dash
import dash_bootstrap_components as dbc
from dash import html, dcc
from flask_login import LoginManager

from auth import get_user_by_id
from callbacks.auth_callbacks import register_auth_callbacks
from callbacks.dashboard_callbacks import register_dashboard_callbacks

# ─── Inicialização do Dash ────────────────────────────────────────────────────
_ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")

app = dash.Dash(
    __name__,
    assets_folder=_ASSETS_DIR,
    external_stylesheets=[
        dbc.themes.BOOTSTRAP,
        "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css",
    ],
    suppress_callback_exceptions=True,
    title="Sales Dashboard · Sankhya",
    update_title=None,
)

# Desabilita ferramentas de debug na UI e checagem de props para remover popups de erro
# app.enable_dev_tools(
#     debug=False,
#     ui=False,
#     props_check=False
# )

server = app.server
server.secret_key = os.environ.get("FLASK_SECRET_KEY", "sankhya-dashboard-2026-change-me")

# ─── Flask-Login ──────────────────────────────────────────────────────────────
_login_manager = LoginManager()
_login_manager.init_app(server)
_login_manager.login_view = "/login"


@_login_manager.user_loader
def load_user(user_id: str):
    return get_user_by_id(user_id)


# ─── Layout base ─────────────────────────────────────────────────────────────
# O layout base agora contém o "Shell" (barra lateral e área de conteúdo) 
# de forma persistente. Apenas o conteúdo interno é trocado, garantindo fluidez.
app.layout = html.Div(id="root", children=[
    dcc.Location(id="url", refresh=False),
    dcc.Store(id="sidebar-state", data="expanded", storage_type="local"),
    
    # Container Principal
    html.Div(id="page-container", children=[
        # O Shell do Dashboard será injetado aqui pelo display_page
        # mas manteremos a estrutura interna estável.
    ]),
])

# ─── Registro de Callbacks ────────────────────────────────────────────────────
register_auth_callbacks()
register_dashboard_callbacks()

log.info("Aplicação Dash inicializada com sucesso.")

# ─── Execução local (não usado em produção via Gunicorn) ─────────────────────
if __name__ == "__main__":
    app.run(debug=True, port=8050, host="0.0.0.0")
