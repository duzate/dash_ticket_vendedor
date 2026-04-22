"""
auth_callbacks.py — Callbacks de autenticação (login, logout, roteamento de páginas).
"""

import logging

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, dcc, html
from flask_login import current_user, login_user, logout_user
from sqlalchemy import text

from auth import authenticate_user
from data_provider import get_dw_engine
from layouts.login import login_layout
from layouts.dashboard import create_layout

log = logging.getLogger(__name__)


def register_auth_callbacks() -> None:

    @dash.callback(
        Output("page-container", "children"),
        Input("url", "pathname"),
    )
    def display_page(pathname: str):
        """Roteia entre login e dashboard com base na autenticação."""
        is_auth = getattr(current_user, "is_authenticated", False)
        if pathname == "/login":
            return login_layout
        if is_auth:
            seller_name = None
            if current_user.role.upper() == "SELLER" and current_user.seller_id:
                try:
                    with get_dw_engine().connect() as conn:
                        row = conn.execute(
                            text("SELECT nome_vendedor FROM dim_vendedor WHERE id_vendedor = :id"),
                            {"id": current_user.seller_id},
                        ).fetchone()
                        if row:
                            seller_name = row.nome_vendedor
                except Exception:
                    log.warning("Não foi possível buscar nome do vendedor para seller_id=%s", current_user.seller_id)
            return create_layout(current_user, seller_name=seller_name)
        return dcc.Location(pathname="/login", id="redirect-to-login")

    @dash.callback(
        Output("url", "pathname", allow_duplicate=True),
        Output("login-alert", "children"),
        Input("login-button", "n_clicks"),
        Input("login-username", "n_submit"),
        Input("login-password", "n_submit"),
        State("login-username", "value"),
        State("login-password", "value"),
        prevent_initial_call=True,
    )
    def handle_login(n_clicks, n_submit_user, n_submit_pass, username, password):
        """Valida credenciais e autentica o usuário."""
        if not dash.callback_context.triggered:
            return dash.no_update, ""
        user = authenticate_user(username or "", password or "")
        if user:
            login_user(user)
            log.info("Login bem-sucedido: %s (%s)", user.username, user.role)
            return "/", ""
            log.warning("Tentativa de login mal-sucedida para usuário: %r", username)
            return dash.no_update, "Acesso negado. Verifique usuário e senha."

    @dash.callback(
        Output("url", "pathname", allow_duplicate=True),
        Input("logout-btn", "n_clicks"),
        prevent_initial_call=True,
    )
    def handle_logout(n_clicks):
        """Encerra a sessão do usuário."""
        if n_clicks:
            logout_user()
            return "/login"
        return dash.no_update

    # ── PROFILE MODAL: abrir / fechar ────────────────────────────────────────

    @dash.callback(
        Output("profile-modal", "is_open"),
        [
            Input("open-profile-modal",   "n_clicks"),
            Input("profile-modal-cancel", "n_clicks"),
        ],
        State("profile-modal", "is_open"),
        prevent_initial_call=True,
    )
    def toggle_profile_modal(open_clicks, cancel_clicks, is_open):
        """Abre ou fecha o modal de perfil."""
        return not is_open

    # ── PROFILE MODAL: alterar senha ─────────────────────────────────────────

    @dash.callback(
        Output("profile-change-status", "children"),
        Input("profile-save-password", "n_clicks"),
        [
            State("profile-current-password", "value"),
            State("profile-new-password",     "value"),
            State("profile-confirm-password", "value"),
        ],
        prevent_initial_call=True,
    )
    def change_password(n_clicks, current_pw, new_pw, confirm_pw):
        """Valida e persiste a nova senha do usuário logado."""
        if not current_pw or not new_pw or not confirm_pw:
            return dbc.Alert(
                [html.I(className="fa-solid fa-triangle-exclamation me-2"), "Preencha todos os campos."],
                color="warning", className="extra-small py-2 mb-0",
            )

        if new_pw != confirm_pw:
            return dbc.Alert(
                [html.I(className="fa-solid fa-triangle-exclamation me-2"), "A nova senha e a confirmação não conferem."],
                color="danger", className="extra-small py-2 mb-0",
            )

        if len(new_pw) < 6:
            return dbc.Alert(
                [html.I(className="fa-solid fa-triangle-exclamation me-2"), "A nova senha deve ter pelo menos 6 caracteres."],
                color="warning", className="extra-small py-2 mb-0",
            )

        if not getattr(current_user, "is_authenticated", False):
            return dbc.Alert("Sessão expirada. Faça login novamente.", color="danger", className="extra-small py-2 mb-0")

        if current_user.password != current_pw:
            return dbc.Alert(
                [html.I(className="fa-solid fa-lock me-2"), "Senha atual incorreta."],
                color="danger", className="extra-small py-2 mb-0",
            )

        if new_pw == current_pw:
            return dbc.Alert(
                [html.I(className="fa-solid fa-circle-info me-2"), "A nova senha deve ser diferente da senha atual."],
                color="info", className="extra-small py-2 mb-0",
            )

        if str(current_user.id) == "admin_fallback":
            return dbc.Alert(
                [html.I(className="fa-solid fa-ban me-2"), "A senha master de contingência não pode ser alterada no sistema."],
                color="warning", className="extra-small py-2 mb-0",
            )

        try:
            engine = get_dw_engine()
            with engine.connect() as conn:
                conn.execute(
                    text("UPDATE dash_users SET password = :p WHERE id = :uid"),
                    {"p": new_pw, "uid": int(current_user.id)},
                )
                conn.commit()
            current_user.password = new_pw
            log.info("Senha alterada com sucesso para: %s", current_user.username)
            return dbc.Alert(
                [html.I(className="fa-solid fa-circle-check me-2"), "Senha alterada com sucesso!"],
                color="success", className="extra-small py-2 mb-0", duration=4000,
            )
        except Exception:
            log.exception("Erro ao alterar senha para: %s", current_user.username)
            return dbc.Alert(
                [html.I(className="fa-solid fa-circle-xmark me-2"), "Erro ao salvar no banco. Tente novamente."],
                color="danger", className="extra-small py-2 mb-0",
            )
