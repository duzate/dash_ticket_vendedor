"""
dashboard_callbacks.py — Callbacks de atualização do dashboard de performance.

Responsabilidade única: receber inputs dos filtros e retornar dados
formatados para todos os outputs do layout (KPIs, gráficos, detalhes).
"""

import json
import logging
from typing import Optional

import dash
import pandas as pd
import plotly.graph_objects as go
import dash_bootstrap_components as dbc
from dash import Input, Output, html
from flask_login import current_user
from sqlalchemy import text

from data_provider import get_dw_engine, get_sellers, query_sales_performance
from auth import filter_sellers_by_role
from utils.formatters import fmt_brl, fmt_brl_compact, fmt_pct
from components.kpi_card import PLOTLY_LAYOUT_BASE

log = logging.getLogger(__name__)

# ─── Constantes de design ────────────────────────────────────────────────────
_COLOR_META      = "#2563eb"
_COLOR_REALIZADO = "#16a34a"
_COLOR_PROJ      = "#facc15"
_COLOR_FALTA     = "#94a3b8"

_N_TEXT_KPIS   = 9
_N_DETAIL_KPIS = 10


def _empty_state() -> tuple:
    """Retorna o estado padrão vazio para todos os outputs do dashboard."""
    return tuple([go.Figure(), go.Figure(), "Resumo do Ciclo"] + ["---"] * (_N_TEXT_KPIS + _N_DETAIL_KPIS))


def _build_daily_chart(df_daily: pd.DataFrame, start_date=None, end_date=None) -> go.Figure:
    fig = go.Figure()
    if df_daily.empty:
        fig.add_annotation(
            text="Selecione um vendedor ou período para visualizar",
            showarrow=False,
            font=dict(size=13, color="#475569"),
            xref="paper", yref="paper", x=0.5, y=0.5,
        )
    else:
        df = df_daily.copy()
        df["date"] = pd.to_datetime(df["date"])
        fig.add_trace(go.Bar(
            name="Meta Diária",
            x=df["date"],
            y=df["meta"],
            marker=dict(color=_COLOR_META),
            text=df["meta"].apply(lambda x: fmt_brl_compact(x) if x > 0 else ""),
            textposition="outside",
            textfont=dict(size=9, color="#94a3b8"),
            hovertemplate="Meta: <b>R$ %{y:,.2f}</b><extra></extra>",
        ))
        fig.add_trace(go.Bar(
            name="Realizado",
            x=df["date"],
            y=df["realized"],
            marker=dict(color=_COLOR_REALIZADO),
            text=df["realized"].apply(lambda x: fmt_brl_compact(x) if x > 0 else ""),
            textposition="outside",
            textfont=dict(size=9, color="#16a34a"),
            hovertemplate="Realizado: <b>R$ %{y:,.2f}</b><extra></extra>",
        ))

    min_date = start_date if start_date else df["date"].min()
    max_date = end_date if end_date else df["date"].max()

    fig.update_layout(**{
        **PLOTLY_LAYOUT_BASE,
        "barmode": "group",
        "bargap": 0.15,
        "bargroupgap": 0.05,
        "hovermode": "x unified",
        "xaxis": dict(
            showgrid=False,
            tickformat="%d/%m",
            type="date",
            range=[min_date, max_date],
            automargin=True,
            fixedrange=False,
        ),
        "yaxis": dict(gridcolor="rgba(255,255,255,0.03)"),
    })
    return fig


def _build_summary_chart(meta: float, realizado: float, proj: float, falta: float) -> go.Figure:
    fig = go.Figure()
    if meta == 0 and realizado == 0:
        fig.add_annotation(
            text="Sem dados para o ciclo selecionado",
            showarrow=False,
            font=dict(size=13, color="#475569"),
            xref="paper", yref="paper", x=0.5, y=0.5,
        )
    else:
        labels = ["Meta", "Realizado", "Projetado", "Falta"]
        values = [meta, realizado, proj, falta]
        colors = [_COLOR_META, _COLOR_REALIZADO, _COLOR_PROJ, _COLOR_FALTA]
        for lb, vl, cl in zip(labels, values, colors):
            fig.add_trace(go.Bar(
                name=lb, x=[lb], y=[vl],
                marker=dict(color=cl, opacity=0.9),
                text=fmt_brl_compact(vl), textposition="outside",
                textfont=dict(size=10, color="#94a3b8"),
                hovertemplate=f"<b>{lb}</b>: R$ {vl:,.2f}<extra></extra>",
            ))

    fig.update_layout(**{
        **PLOTLY_LAYOUT_BASE,
        "showlegend": False,
        "xaxis": dict(visible=True, tickfont=dict(size=10, color="#64748b")),
        "yaxis": dict(visible=False),
        "margin": dict(t=30),
    })
    return fig


def _load_users_list() -> list:
    """Carrega e formata a lista de usuários do banco."""
    engine = get_dw_engine()
    with engine.connect() as conn:
        df = pd.read_sql(
            text("SELECT id, username, role, seller_id, COALESCE(is_active, TRUE) as active FROM dash_users ORDER BY username"),
            con=conn,
        )
    if df.empty:
        return [html.P("Nenhum usuário cadastrado no banco.", className="text-muted small")]

    rows = []
    for _, u in df.iterrows():
        status_color = "success" if u["active"] else "secondary"
        status_icon  = "fa-toggle-on" if u["active"] else "fa-toggle-off"
        seller_val   = "-" if pd.isna(u["seller_id"]) else str(int(u["seller_id"]))
        rows.append(dbc.Row([
            dbc.Col(u["username"], width=4, className="small text-truncate"),
            dbc.Col(u["role"],     width=2, className="extra-small pt-1"),
            dbc.Col(seller_val,     width=2, className="extra-small pt-1"),
            dbc.Col([
                dbc.Button(html.I(className=f"fa-solid {status_icon}"),
                           id={"type": "user-action", "index": f"toggle|{u['id']}"},
                           color=status_color, size="xs", className="me-1 py-0 px-1"),
                dbc.Button(html.I(className="fa-solid fa-trash"),
                           id={"type": "user-action", "index": f"delete|{u['id']}"},
                           color="danger", size="xs", className="py-0 px-1"),
            ], width=4, className="text-end"),
        ], className="py-1 border-bottom border-light border-opacity-10 align-items-center mx-0"))
    return rows


# ─── Registro dos callbacks ───────────────────────────────────────────────────

def register_dashboard_callbacks() -> None:

    @dash.callback(
        Output("active-seller-dropdown", "options"),
        [Input("competencia-dropdown", "value"), Input("company-dropdown", "value")],
    )
    def update_seller_options(competencia: Optional[str], company_id: Optional[int]) -> list:
        if not getattr(current_user, "is_authenticated", False) or not competencia:
            return []
        
        if current_user.role.upper() == "MANAGER":
            if not company_id or company_id not in current_user.managed_sellers:
                return []

        try:
            start, end, _ = competencia.split("|")
            sellers = get_sellers(start, end, company_id)
            allowed = filter_sellers_by_role(current_user, sellers)
            return [{"label": f"{s['id']} · {s['name']}", "value": s["id"]} for s in allowed]
        except Exception:
            log.exception("Erro ao carregar opções de vendedores.")
            return []

    @dash.callback(
        [
            Output("daily-performance-chart", "figure"),
            Output("summary-bar-chart",       "figure"),
            Output("summary-chart-title",     "children"),
            # KPIs principais
            Output("card-ticket-medio",       "children"),
            Output("card-ticket-tkts",        "children"),
            Output("card-meta-total",         "children"),
            Output("card-realizado-total",    "children"),
            Output("card-realizado-proj",     "children"),
            Output("card-perc-realizado",     "children"),
            Output("card-perc-proj",          "children"),
            Output("card-restante",           "children"),
            Output("card-media-realizado",    "children"),
            # Detalhes financeiros
            Output("card-dev-canc-total",     "children"),
            Output("card-dev-canc-perc",      "children"),
            Output("card-dev-valor",          "children"),
            Output("card-canc-valor",         "children"),
            Output("card-descontos-total",    "children"),
            Output("card-descontos-perc",     "children"),
            Output("card-descontos-medio",    "children"),
            Output("card-comissao",           "children"),
            Output("card-premiacao",          "children"),
            Output("card-remuneracao-total",  "children"),
        ],
        [
            Input("active-seller-dropdown", "value"),
            Input("competencia-dropdown",   "value"),
            Input("company-dropdown",       "value"),
        ],
    )
    def update_dashboard(
        active_seller_id: Optional[int],
        competence: Optional[str],
        company_id: Optional[int],
    ) -> tuple:
        if not getattr(current_user, "is_authenticated", False) or not competence:
            return _empty_state()
            
        if current_user.role.upper() == "MANAGER":
            if not company_id or company_id not in current_user.managed_sellers:
                return _empty_state()

        try:
            start, end, dt_ref = competence.split("|")

            role_upper = current_user.role.upper()
            target_id  = current_user.seller_id if role_upper == "SELLER" else active_seller_id
            filtro_ids = [target_id] if target_id else None

            df_daily, _, cards = query_sales_performance(filtro_ids, start, end, company_id)
            log.info("Query Results: df_daily=%d rows | realizado=%s", len(df_daily), cards.get("realizado"))

            # ── Período completo com meta diária ─────────────────────────────
            full_range  = pd.date_range(start=start, end=end)
            holidays    = ["2025-12-25", "2026-01-01", "2026-02-17"]
            working_days = [d for d in full_range if d.dayofweek < 6 and d.strftime("%Y-%m-%d") not in holidays]
            working_days_count = len(working_days)

            meta_total_periodo = float(cards.get("meta") or 0)
            daily_meta_calc    = (meta_total_periodo / working_days_count) if working_days_count > 0 else 0

            df_template = pd.DataFrame({"date": full_range.strftime("%Y-%m-%d")})
            df_daily    = pd.merge(df_template, df_daily, on="date", how="left").fillna(0)

            mask_trabalho = (pd.to_datetime(df_daily["date"]).dt.dayofweek < 6) & (~df_daily["date"].isin(holidays))
            df_daily.loc[mask_trabalho, "meta"] = daily_meta_calc

            # ── KPIs brutos ──────────────────────────────────────────────────
            meta       = meta_total_periodo
            realizado  = float(cards.get("realizado")    or 0)
            dev        = float(cards.get("devolucao")    or 0)
            canc       = float(cards.get("cancelado")    or 0)
            desc       = float(cards.get("desconto")     or 0)
            tkts       = int(cards.get("tkts")           or 0)
            comis_base = float(cards.get("comissao")     or 0)
            ticket_med = float(cards.get("ticket_medio") or 0)

            # ── Derivados ────────────────────────────────────────────────────
            achiv_perc    = (realizado / meta) if meta > 0 else 0
            total_perdido = dev + canc
            base_perdido  = realizado + total_perdido
            perc_perdido  = (total_perdido / base_perdido * 100) if base_perdido > 0 else 0
            perc_desc     = (desc / (realizado + desc) * 100) if (realizado + desc) > 0 else 0
            desc_medio    = (desc / tkts) if tkts > 0 else 0

            # ── Projeção ─────────────────────────────────────────────────────
            dias_com_venda = max(len(df_daily[df_daily["realized"] > 0]) if not df_daily.empty else 1, 1)
            proj_realizado = (realizado / dias_com_venda) * working_days_count
            perc_proj      = (proj_realizado / meta * 100) if meta > 0 else 0
            media_diaria   = realizado / dias_com_venda

            # ── Comissão e Prêmio (Conforme SQL Idealizado) ──────────────────
            achiv_perc = (realizado / meta) if meta > 0 else 0
            
            # Define a taxa total conforme o atingimento atual
            if achiv_perc >= 1.50:
                taxa_total = 0.0150
            elif achiv_perc >= 1.40:
                taxa_total = 0.0140
            elif achiv_perc >= 1.30:
                taxa_total = 0.0130
            elif achiv_perc >= 1.20:
                taxa_total = 0.0120
            elif achiv_perc >= 1.10:
                taxa_total = 0.0110
            elif achiv_perc >= 1.00:
                taxa_total = 0.0105
            else:
                taxa_total = 0.0100

            # O Prêmio é o excedente sobre 1% (conforme cláusula ELSE do SQL)
            # Premio = (Realizado * Taxa_Total) - (Realizado * 1%)
            comissao_base = comis_base # Já calculada em data_provider (Realizado * Perc_Vendedor)
            premio        = round((realizado * taxa_total) - (realizado * 0.01), 2)
            
            # Se o prêmio der negativo (vendedor com meta mas sem atingimento), zeramos
            premio = max(premio, 0)
            
            remuneracao_total = comissao_base + premio

            # ── Textos ───────────────────────────────────────────────────────
            ref_label   = pd.to_datetime(dt_ref).strftime("%m/%Y")
            chart_title = f"Resumo · {ref_label}"

            if meta == 0 and realizado > 0:
                s_restante = "Superado"
            elif meta > 0:
                s_restante = fmt_brl(max(meta - realizado, 0))
            else:
                s_restante = "R$ 0,00"

            s_perc_proj = f"Estimativa: {fmt_pct(perc_proj)}" if meta > 0 else "Sem Meta"

            return (
                _build_daily_chart(df_daily, start, end),
                _build_summary_chart(meta, realizado, proj_realizado, max(meta - realizado, 0)),
                chart_title,
                fmt_brl(ticket_med),
                f"{tkts:,} transações".replace(",", "."),
                fmt_brl(meta),
                fmt_brl(realizado),
                f"Proj. {fmt_brl_compact(proj_realizado)}",
                fmt_pct(achiv_perc * 100),
                s_perc_proj,
                s_restante,
                fmt_brl(media_diaria),
                fmt_brl(total_perdido),
                fmt_pct(perc_perdido),
                fmt_brl(dev),
                fmt_brl(canc),
                fmt_brl(desc),
                fmt_pct(perc_desc),
                fmt_brl(desc_medio),
                fmt_brl(comis_base),
                fmt_brl(premio),
                fmt_brl(remuneracao_total),
            )

        except Exception:
            log.exception("Erro em update_dashboard.")
            return _empty_state()

    # ─── USER MANAGEMENT CALLBACKS ───────────────────────────────────────────

    @dash.callback(
        [Output("users-modal", "is_open"), Output("users-list-container", "children")],
        [Input("open-users-modal", "n_clicks"), Input({"type": "user-action", "index": dash.ALL}, "n_clicks")],
        [dash.State("users-modal", "is_open")],
        prevent_initial_call=True,
    )
    def handle_users_modal(n_clicks_open, n_clicks_actions, is_open):
        ctx = dash.callback_context
        if not ctx.triggered:
            return is_open, dash.no_update

        trigger_id = ctx.triggered[0]["prop_id"]
        engine = get_dw_engine()

        if "user-action" in trigger_id:
            prop_id_obj  = json.loads(trigger_id.split(".")[0])
            action_type, target_user_id = prop_id_obj["index"].split("|")
            with engine.connect() as conn:
                if action_type == "delete":
                    conn.execute(text("DELETE FROM dash_users WHERE id = :id"), {"id": target_user_id})
                elif action_type == "toggle":
                    conn.execute(text("UPDATE dash_users SET is_active = NOT COALESCE(is_active, TRUE) WHERE id = :id"), {"id": target_user_id})
                conn.commit()

        try:
            return True, _load_users_list()
        except Exception:
            log.exception("Erro ao carregar gestão de usuários.")
            return True, [html.P("Erro ao carregar gestão de usuários.", className="text-danger small")]

    @dash.callback(
        Output("user-mgmt-status", "children"),
        [Input("user-mgmt-save", "n_clicks")],
        [
            dash.State("user-mgmt-username",  "value"),
            dash.State("user-mgmt-password",  "value"),
            dash.State("user-mgmt-role",      "value"),
            dash.State("user-mgmt-seller-id", "value"),
            dash.State("user-mgmt-company",   "value"),
        ],
        prevent_initial_call=True,
    )
    def save_user(n_clicks, username, password, role, seller_id, company_ids):
        if not n_clicks or not username or not password or not role:
            return "Preencha Usuário, Senha e Papel."

        username = username.lower().strip()
        managed = (company_ids if isinstance(company_ids, list) else [company_ids]) \
                  if role == "MANAGER" and company_ids else None

        try:
            engine = get_dw_engine()
            with engine.connect() as conn:
                exists = conn.execute(text("SELECT COUNT(*) FROM dash_users WHERE username = :u"), {"u": username}).scalar()
                if exists:
                    conn.execute(text("""
                        UPDATE dash_users SET password = :p, role = :r, seller_id = :s, managed_sellers = :m
                        WHERE username = :u
                    """), {"u": username, "p": password, "r": role, "s": seller_id, "m": managed})
                    msg = f"Usuário {username} atualizado!"
                else:
                    conn.execute(text("""
                        INSERT INTO dash_users (username, password, role, seller_id, managed_sellers, is_active)
                        VALUES (:u, :p, :r, :s, :m, TRUE)
                    """), {"u": username, "p": password, "r": role, "s": seller_id, "m": managed})
                    msg = f"Usuário {username} criado!"
                conn.commit()
            return dbc.Alert(msg, color="success", duration=2000)
        except Exception:
            log.exception("Erro ao salvar usuário.")
            return dbc.Alert("Erro ao salvar no banco.", color="danger")
