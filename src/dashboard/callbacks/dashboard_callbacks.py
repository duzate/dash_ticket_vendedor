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
from dash import Input, Output, State, html
from flask_login import current_user
from sqlalchemy import text

from data_provider import (
    get_available_competencias,
    get_dw_engine,
    query_sales_performance,
    get_rankings,
    get_sellers
)
from auth import filter_sellers_by_role
from utils.formatters import fmt_brl, fmt_brl_compact, fmt_pct
from layouts.dashboard import get_page_content
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

    # ─── NAVEGAÇÃO INTERNA (FLUIDEZ) ───────────────────────────────────────────
    @dash.callback(
        [
            Output("dashboard-inner-content", "children"),
            Output("page-title-header", "children")
        ],
        Input("url", "pathname"),
    )
    def update_dashboard_inner_content(pathname):
        """Atualiza apenas o conteúdo interno quando a URL muda dentro do dashboard."""
        if pathname == "/login":
            return dash.no_update, dash.no_update
        
        title = "Sales Performance" if pathname == "/" else "TOP 10 Rankings"
        return get_page_content(pathname), title

    # ─── SIDEBAR TOGGLE ────────────────────────────────────────────────────────
    @dash.callback(
        Output("sidebar-state", "data"),
        Input("sidebar-toggle", "n_clicks"),
        State("sidebar-state", "data"),
        prevent_initial_call=True
    )
    def toggle_sidebar(n, current_state):
        if n:
            return "collapsed" if current_state == "expanded" else "expanded"
        return current_state

    # Callback CLIENTSIDE para atualização instantânea das classes
    # Isso evita o "pulo" de layout (glitch) ao navegar entre páginas com a sidebar colapsada.
    dash.clientside_callback(
        """
        function(state) {
            const sidebarClass = state === "collapsed" ? "sidebar collapsed" : "sidebar";
            const contentClass = state === "collapsed" ? "content-area collapsed" : "content-area";
            return [sidebarClass, contentClass];
        }
        """,
        Output("sidebar", "className"),
        Output("content-area", "className"),
        Input("sidebar-state", "data")
    )

    @dash.callback(
        [
            Output("rank-list-clientes", "children"),
            Output("rank-total-clientes", "children"),
            Output("rank-list-marcas",   "children"),
            Output("rank-total-marcas",   "children"),
            Output("rank-list-produtos", "children"),
            Output("rank-total-produtos", "children"),
        ],
        [
            Input("competencia-dropdown", "value"),
            Input("company-dropdown", "value"),
            Input("active-seller-dropdown", "value")
        ],
    )
    def update_rankings_data(competence, company, seller):
        if not getattr(current_user, "is_authenticated", False) or not competence:
            return [[]] * 6
        
        try:
            # Extrai a data de referência
            _, _, dt_ref = competence.split("|")
            
            # Normaliza filtros
            cid = company[0] if isinstance(company, list) and company else company
            vid = seller[0] if isinstance(seller, list) and seller else (seller or 0)

            role_upper = current_user.role.upper()
            if role_upper == "SELLER":
                vid = current_user.seller_id
                # SELLER usa cid=0 (suas metas são consolidadas) sem acesso global
                cid_for_ranking = 0
            elif role_upper == "MANAGER":
                if not current_user.managed_sellers:
                    return [[]] * 6
                if cid and cid in current_user.managed_sellers:
                    # Filial específica selecionada e autorizada
                    cid_for_ranking = cid
                else:
                    # Nenhuma filial selecionada → usa lista de managed_sellers (sem expor ranking global)
                    cid_for_ranking = current_user.managed_sellers
            else:
                # ADMIN: usa cid selecionado ou 0 (global)
                cid_for_ranking = cid if cid else 0

            data = get_rankings(dt_ref, vid, cid_for_ranking)
            
            def build_items(items, color, is_client=False, is_brand=False, is_product=False):
                list_elements = []
                total = 0
                for item in items:
                    val = float(item['valor'])
                    total += val
                    
                    props = {"className": "d-flex align-items-center justify-content-between ranking-item mb-2 rounded-3"}
                    if is_client and 'id_item' in item:
                        props['id'] = {'type': 'client-rank-item', 'index': int(item['id_item'])}
                        props['style'] = {'cursor': 'pointer', 'transition': 'transform 0.2s'}
                        props['className'] += " client-clickable-item"
                        props['n_clicks'] = 0
                    elif is_brand and 'id_item' in item:
                        props['id'] = {'type': 'brand-rank-item', 'index': int(item['id_item'])}
                        props['style'] = {'cursor': 'pointer', 'transition': 'transform 0.2s'}
                        props['className'] += " brand-clickable-item"
                        props['n_clicks'] = 0
                        
                    if is_product:
                        refforn = item.get('refforn', '')
                        complemento = item.get('complemento', '')
                        subtitle_parts = []
                        if refforn:
                            subtitle_parts.append(f"REF: {refforn}")
                        if complemento:
                            subtitle_parts.append(f"COMP: {complemento}")
                        subtitle_text = " | ".join(subtitle_parts) if subtitle_parts else ""
                        
                        name_and_sub = html.Div(className="d-flex flex-column ms-3 text-truncate", style={'flex': '1', 'minWidth': '0'}, children=[
                            html.Span(item['label_item'], className="fw-bold text-truncate", style={'maxWidth': '100%'}),
                            html.Span(subtitle_text, className="text-muted small text-truncate", style={'fontSize': '0.72rem', 'maxWidth': '100%'})
                        ]) if subtitle_text else html.Span(item['label_item'], className="ms-3 fw-bold text-truncate", style={'flex': '1', 'minWidth': '0', 'maxWidth': '100%'})
                        
                        list_elements.append(
                            html.Div(**props, children=[
                                html.Div(className="d-flex align-items-center", style={'flex': '1', 'minWidth': '0', 'marginRight': '10px'}, children=[
                                    html.Div(str(item['posicao']), className=f"rank-badge bg-{color}"),
                                    name_and_sub
                                ]),
                                html.Span(fmt_brl(val), className="fw-bold small", style={'flexShrink': '0'})
                            ])
                        )
                    else:
                        list_elements.append(
                            html.Div(**props, children=[
                                html.Div(className="d-flex align-items-center", style={'flex': '1', 'minWidth': '0', 'marginRight': '10px'}, children=[
                                    html.Div(str(item['posicao']), className=f"rank-badge bg-{color}"),
                                    html.Span(item['label_item'], className="ms-3 fw-bold text-truncate", style={'flex': '1', 'minWidth': '0', 'maxWidth': '100%'})
                                ]),
                                html.Span(fmt_brl(val), className="fw-bold small", style={'flexShrink': '0'})
                            ])
                        )
                if not list_elements:
                    list_elements = [html.P("Sem dados para este ciclo", className="text-muted small p-3")]
                return list_elements, fmt_brl(total)

            cli_list, cli_total = build_items(data.get("CLIENTE", []), "primary", is_client=True)
            mar_list, mar_total = build_items(data.get("MARCA", []), "success", is_brand=True)
            pro_list, pro_total = build_items(data.get("PRODUTO", []), "warning", is_product=True)

            return cli_list, cli_total, mar_list, mar_total, pro_list, pro_total
        except Exception:
            log.exception("Erro ao carregar rankings.")
            return [[]] * 6

    @dash.callback(
        Output("active-seller-dropdown", "options"),
        [Input("competencia-dropdown", "value"), Input("company-dropdown", "value")],
    )
    def update_seller_options(competencia: Optional[str], company_id: Optional[int]) -> list:
        if not getattr(current_user, "is_authenticated", False) or not competencia:
            return []

        try:
            start, end, _ = competencia.split("|")
            
            if current_user.role.upper() == "MANAGER":
                if company_id:
                    if company_id not in current_user.managed_sellers:
                        return [] # Tentou acessar filial não permitida
                    cid_filter = company_id
                else:
                    cid_filter = current_user.managed_sellers
            else:
                cid_filter = company_id
                
            sellers = get_sellers(start, end, cid_filter)
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
            
        try:
            start, end, dt_ref = competence.split("|")

            role_upper = current_user.role.upper()
            
            # Enforce company filter for manager
            if role_upper == "MANAGER":
                if company_id:
                    if company_id not in current_user.managed_sellers:
                        return _empty_state()
                    cid_filter = company_id
                else:
                    cid_filter = current_user.managed_sellers
            else:
                cid_filter = company_id

            if role_upper == "SELLER":
                filtro_ids = [current_user.seller_id]
            else:
                filtro_ids = [active_seller_id] if active_seller_id else None

            df_daily, _, cards = query_sales_performance(filtro_ids, start, end, cid_filter)
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

    # ─── CLIENT PROFILE MODAL CALLBACK ───────────────────────────────────────
    @dash.callback(
        [Output("client-profile-modal", "is_open"), Output("client-profile-content", "children")],
        [Input({"type": "client-rank-item", "index": dash.ALL}, "n_clicks"),
         Input("close-client-profile", "n_clicks")],
        [State("competencia-dropdown", "value"), State("company-dropdown", "value"), State("active-seller-dropdown", "value")],
        prevent_initial_call=True
    )
    def open_client_profile(n_clicks_list, close_clicks, competence, company, seller):
        ctx = dash.callback_context
        if not ctx.triggered:
            return dash.no_update, dash.no_update

        trigger_id_str = ctx.triggered[0]["prop_id"].split(".")[0]
        if "close-client-profile" in trigger_id_str:
            return False, dash.no_update

        # Verifica se algum clique foi realmente > 0
        if not any(c is not None and c > 0 for c in n_clicks_list):
            return dash.no_update, dash.no_update

        trigger_id_str = ctx.triggered[0]["prop_id"].split(".")[0]
        try:
            trigger_id = json.loads(trigger_id_str)
            client_id = int(trigger_id["index"])
        except Exception:
            return dash.no_update, dash.no_update
            
        if not competence:
            return True, html.P("Selecione uma competência.")
            
        # Pega a data base
        _, _, dt_ref = competence.split("|")
        cid = company[0] if isinstance(company, list) and company else (company or 0)
        vid = seller[0] if isinstance(seller, list) and seller else (seller or 0)
        
        role_upper = getattr(current_user, "role", "").upper()
        if role_upper == "SELLER":
            vid = current_user.seller_id
        elif role_upper == "MANAGER":
            if cid not in current_user.managed_sellers:
                if current_user.managed_sellers:
                    cid = current_user.managed_sellers[0]
                else:
                    return True, html.P("Sem permissão para esta filial.")
        
        from data_provider import get_client_profile
        profile = get_client_profile(dt_ref, client_id, cid, vid)
        
        # Monta o layout
        top_prods = profile.get('top_produtos', [])
        top_vends = profile.get('top_vendedores', [])
        t_medio = profile.get('tempo_medio_compra', 0)
        
        # Cabecalho do cliente com gradiente sutil e avatar moderno
        header_card = html.Div(className="client-profile-header mb-4 p-3 rounded-4 d-flex align-items-center gap-3", style={
            "background": "linear-gradient(135deg, rgba(96, 165, 250, 0.15), rgba(30, 41, 59, 0.3))",
            "border": "1px solid rgba(255, 255, 255, 0.08)",
            "backdrop-filter": "blur(10px)"
        }, children=[
            html.Div(className="profile-avatar-large d-flex align-items-center justify-content-center bg-primary bg-opacity-25 rounded-circle", style={
                "width": "50px", "height": "50px", "border": "2px solid rgba(96, 165, 250, 0.3)", "flex-shrink": 0
            }, children=[
                html.I(className="fa-solid fa-building text-primary h4 mb-0")
            ]),
            html.Div([
                html.H5(profile.get("nome_cliente", f"Cliente #{client_id}"), className="mb-1 fw-bold text-white", style={"font-size": "1.15rem"}),
                html.Div(className="d-flex align-items-center gap-2", children=[
                    html.Span(f"ID: {client_id}", className="badge bg-secondary bg-opacity-50 text-white-50 px-2 py-0.5 rounded-pill", style={"font-size": "10px"}),
                    html.Span("Últimos 6 meses de movimentações", className="text-muted extra-small")
                ])
            ])
        ])

        # Grid de Produtos (Col 1)
        max_prod_val = max([p['valor'] for p in top_prods]) if top_prods else 1
        prod_items = []
        for p in top_prods:
            pct = (p['valor'] / max_prod_val) * 100
            refforn = p.get('refforn', '')
            complemento = p.get('complemento', '')
            subtitle_parts = []
            if refforn:
                subtitle_parts.append(f"REF: {refforn}")
            if complemento:
                subtitle_parts.append(f"COMP: {complemento}")
            subtitle_text = " | ".join(subtitle_parts) if subtitle_parts else ""
            
            prod_items.append(html.Div(className="mb-3", children=[
                html.Div(className="d-flex flex-column mb-1", children=[
                    html.Span(p['nome'], className="fw-semibold text-truncate text-white-50", style={"font-size": "0.82rem", "max-width": "100%"}),
                    html.Span(subtitle_text, className="text-muted small text-truncate", style={"font-size": "0.72rem", "max-width": "100%"}) if subtitle_text else None
                ]),
                dbc.Progress(value=pct, color="primary", style={"height": "5px", "background": "rgba(255, 255, 255, 0.05)"}, className="rounded-pill")
            ]))
        
        prod_col = dbc.Col(xs=12, md=7, children=[
            html.Div(className="glass-card p-4 h-100", children=[
                html.H6([html.I(className="fa-solid fa-box-open me-2 text-primary"), "Top 5 Produtos Comprados"], className="fw-bold mb-4 text-white d-flex align-items-center", style={"font-size": "0.9rem"}),
                html.Div(prod_items) if top_prods else html.P("Nenhum produto registrado no período.", className="text-muted small py-4 text-center")
            ])
        ])

        # Grid de Vendedores (Col 2)
        max_vend_val = max([v['valor'] for v in top_vends]) if top_vends else 1
        vend_items = []
        for v in top_vends:
            pct = (v['valor'] / max_vend_val) * 100
            vend_items.append(html.Div(className="mb-3", children=[
                html.Div(className="mb-1", children=[
                    html.Span(v['nome'], className="fw-semibold text-truncate text-white-50", style={"font-size": "0.82rem"}),
                ]),
                dbc.Progress(value=pct, color="success", style={"height": "5px", "background": "rgba(255, 255, 255, 0.05)"}, className="rounded-pill")
            ]))

        # Tempo Médio de Recompra (Hero Card)
        t_card = html.Div(className="glass-card p-3 mb-3 text-center d-flex flex-column align-items-center justify-content-center", style={
            "background": "linear-gradient(135deg, rgba(245, 158, 11, 0.08), rgba(15, 23, 42, 0.6))"
        }, children=[
            html.Div(className="bg-warning-soft mb-2 rounded-circle d-flex align-items-center justify-content-center", style={"width": "42px", "height": "42px", "background": "rgba(245, 158, 11, 0.15)"}, children=[
                html.I(className="fa-solid fa-clock-rotate-left text-warning h5 mb-0")
            ]),
            html.Span("Tempo Médio de Recompra", className="text-muted extra-small fw-semibold uppercase mb-1", style={"letter-spacing": "0.05em"}),
            html.H3(f"{t_medio:.1f} dias" if t_medio > 0 else "N/A", className="fw-extrabold text-warning mb-1", style={"font-size": "1.75rem", "font-family": "var(--font-display)"}),
            html.P("Frequência média entre pedidos novos.", className="text-white-50 extra-small mb-0")
        ])

        v_card = html.Div(className="glass-card p-4", children=[
            html.H6([html.I(className="fa-solid fa-user-tie me-2 text-success"), "Top Vendedores"], className="fw-bold mb-4 text-white d-flex align-items-center", style={"font-size": "0.9rem"}),
            html.Div(vend_items) if top_vends else html.P("Nenhum vendedor registrado.", className="text-muted small py-2 text-center")
        ])

        side_col = dbc.Col(xs=12, md=5, children=[
            t_card,
            v_card
        ])

        content = html.Div([
            header_card,
            dbc.Row([
                prod_col,
                side_col
            ], className="g-3")
        ])
        
        return True, content

    # ─── BRAND PROFILE MODAL CALLBACK ────────────────────────────────────────
    @dash.callback(
        [Output("brand-profile-modal", "is_open"), Output("brand-profile-content", "children")],
        [Input({"type": "brand-rank-item", "index": dash.ALL}, "n_clicks"),
         Input("close-brand-profile", "n_clicks")],
        [State("competencia-dropdown", "value"), State("company-dropdown", "value"), State("active-seller-dropdown", "value")],
        prevent_initial_call=True
    )
    def open_brand_profile(n_clicks_list, close_clicks, competence, company, seller):
        ctx = dash.callback_context
        if not ctx.triggered:
            return dash.no_update, dash.no_update

        trigger_id_str = ctx.triggered[0]["prop_id"].split(".")[0]
        if "close-brand-profile" in trigger_id_str:
            return False, dash.no_update

        # Verifica se algum clique foi realmente > 0
        if not any(c is not None and c > 0 for c in n_clicks_list):
            return dash.no_update, dash.no_update

        try:
            trigger_id = json.loads(trigger_id_str)
            brand_id = int(trigger_id["index"])
        except Exception:
            return dash.no_update, dash.no_update
            
        if not competence:
            return True, html.P("Selecione uma competência.")
            
        # Pega a data base
        _, _, dt_ref = competence.split("|")
        cid = company[0] if isinstance(company, list) and company else (company or 0)
        vid = seller[0] if isinstance(seller, list) and seller else (seller or 0)
        
        role_upper = getattr(current_user, "role", "").upper()
        if role_upper == "SELLER":
            vid = current_user.seller_id
        elif role_upper == "MANAGER":
            if cid not in current_user.managed_sellers:
                if current_user.managed_sellers:
                    cid = current_user.managed_sellers[0]
                else:
                    return True, html.P("Sem permissão para esta filial.")
        
        from data_provider import get_brand_profile
        profile = get_brand_profile(dt_ref, brand_id, cid, vid)
        
        # Monta o layout
        top_prods = profile.get('top_produtos', [])
        
        # Cabecalho da marca com gradiente sutil e avatar moderno
        header_card = html.Div(className="brand-profile-header mb-4 p-3 rounded-4 d-flex align-items-center gap-3", style={
            "background": "linear-gradient(135deg, rgba(74, 222, 128, 0.15), rgba(30, 41, 59, 0.3))",
            "border": "1px solid rgba(255, 255, 255, 0.08)",
            "backdrop-filter": "blur(10px)"
        }, children=[
            html.Div(className="profile-avatar-large d-flex align-items-center justify-content-center bg-success bg-opacity-25 rounded-circle", style={
                "width": "50px", "height": "50px", "border": "2px solid rgba(74, 222, 128, 0.3)", "flex-shrink": 0
            }, children=[
                html.I(className="fa-solid fa-tags text-success h4 mb-0")
            ]),
            html.Div([
                html.H5(profile.get("nome_marca", f"Marca #{brand_id}"), className="mb-1 fw-bold text-white", style={"font-size": "1.15rem"}),
                html.Div(className="d-flex align-items-center gap-2", children=[
                    html.Span(f"ID: {brand_id}", className="badge bg-secondary bg-opacity-50 text-white-50 px-2 py-0.5 rounded-pill", style={"font-size": "10px"}),
                    html.Span("Produtos mais vendidos no período", className="text-muted extra-small")
                ])
            ])
        ])

        # Grid de Produtos
        max_prod_val = max([p['valor'] for p in top_prods]) if top_prods else 1
        prod_items = []
        for p in top_prods:
            pct = (p['valor'] / max_prod_val) * 100
            refforn = p.get('refforn', '')
            complemento = p.get('complemento', '')
            subtitle_parts = []
            if refforn:
                subtitle_parts.append(f"REF: {refforn}")
            if complemento:
                subtitle_parts.append(f"COMP: {complemento}")
            subtitle_text = " | ".join(subtitle_parts) if subtitle_parts else ""
            
            prod_items.append(html.Div(className="mb-3", children=[
                html.Div(className="d-flex flex-column mb-1", children=[
                    html.Span(p['nome'], className="fw-semibold text-truncate text-white-50", style={"max-width": "100%", "font-size": "0.82rem"}),
                    html.Span(subtitle_text, className="text-muted small text-truncate", style={"font-size": "0.72rem", "max-width": "100%"}) if subtitle_text else None
                ]),
                dbc.Progress(value=pct, color="success", style={"height": "5px", "background": "rgba(255, 255, 255, 0.05)"}, className="rounded-pill")
            ]))
        
        prod_col = html.Div(className="glass-card p-4", children=[
            html.H6([html.I(className="fa-solid fa-box-open me-2 text-success"), "Top 5 Produtos mais Vendidos da Marca"], className="fw-bold mb-4 text-white d-flex align-items-center", style={"font-size": "0.9rem"}),
            html.Div(prod_items) if top_prods else html.P("Nenhum produto registrado no período.", className="text-muted small py-4 text-center")
        ])

        content = html.Div([
            header_card,
            prod_col
        ])
        
        return True, content

