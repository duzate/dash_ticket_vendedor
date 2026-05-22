import dash_bootstrap_components as dbc
from dash import dcc, html
from components.kpi_card import kpi_card
from components.sidebar import sidebar
from data_provider import get_available_competencias, get_companies
from layouts.rankings import rankings_layout

def get_filters_bar(current_user, seller_name: str = None, title: str = "Dashboard"):
    competencias = get_available_competencias()
    initial_comp = competencias[0]['value'] if competencias else None
    user_role = current_user.role
    username = current_user.username
    role_upper = (user_role or "").upper()
    is_seller = role_upper == "SELLER"
    is_admin = role_upper == "ADMIN"
    is_manager = role_upper == "MANAGER"

    all_companies = get_companies()
    initial_company = None
    if is_manager and current_user.managed_sellers:
        company_options = [c for c in all_companies if c['value'] in current_user.managed_sellers]
        initial_company = company_options[0]['value'] if company_options else None
    else:
        company_options = all_companies

    return dbc.Row(className="g-2 mb-4 align-items-center filter-control-bar p-2 mx-0 rounded-3", children=[
        # Coluna 1: Logo & Título
        dbc.Col(xs=12, lg=2, children=[
            html.H6(title, id="page-title-header", className="mb-0 fw-bold"),
            html.Small(f"User: {username}", className="text-muted extra-small")
        ]),

        # Coluna 2: Filtros
        dbc.Col(xs=12, lg=7, children=[
            dbc.Row(className="g-2", children=[
                dbc.Col(
                    dcc.Dropdown(
                        id='company-dropdown', options=company_options,
                        value=initial_company,
                        placeholder="Filial", className="custom-dropdown", clearable=not is_manager
                    ) if not is_seller else dcc.Dropdown(id='company-dropdown', style={'display': 'none'}),
                    width=4
                ),
                dbc.Col(
                    dcc.Dropdown(
                        id='active-seller-dropdown', options=[],
                        placeholder="Vendedor", className="custom-dropdown", clearable=True
                    ) if not is_seller else html.Div([
                        html.I(className="fa-solid fa-user-tie me-2", style={'color': 'var(--primary)'}),
                        html.Span(seller_name or username, className="fw-bold text-white"),
                    ], className="d-flex align-items-center ps-2 h-100",
                    id='active-seller-dropdown'),
                    width=4
                ),
                dbc.Col(dcc.Dropdown(
                    id='competencia-dropdown', options=competencias,
                    value=initial_comp, className="custom-dropdown", clearable=False
                ), width=4),
            ])
        ]),

        # Coluna 3: Logout & Admin & Profile
        dbc.Col(xs=12, lg=3, className="text-end", children=[
            dbc.Button([
                html.I(className="fa-solid fa-users-gear me-2"),
                "Usuários"
            ], id="open-users-modal", color="info", size="sm", className="px-3 rounded-2 fw-bold me-2") if is_admin else None,

            dbc.Button(
                html.I(className="fa-solid fa-circle-user"),
                id="open-profile-modal", color="secondary", size="sm",
                className="px-3 rounded-2 fw-bold me-2",
                title="Meu Perfil"
            ),

            dbc.Button([
                html.I(className="fa-solid fa-right-from-bracket me-2"),
                "Sair"
            ], id="logout-btn", color="danger", size="sm", className="px-3 rounded-2 fw-bold")
        ])
    ])

def sales_performance_content():
    return html.Div([
        # ── METRICS SECTION ───────────────────────────────────────────────
        dbc.Row(className="g-2 mb-2", children=[
            dbc.Col(kpi_card("Objetivo", "card-meta-total", "primary", icon="fa-solid fa-crosshairs"), xs=6, md=4, xl=2),
            dbc.Col(kpi_card("Realizado", "card-realizado-total", "success", sub_id="card-realizado-proj", icon="fa-solid fa-dollar-sign"), xs=6, md=4, xl=2),
            dbc.Col(kpi_card("% Ativ.", "card-perc-realizado", "info", sub_id="card-perc-proj", icon="fa-solid fa-award"), xs=6, md=4, xl=2),
            dbc.Col(kpi_card("Falta", "card-restante", "danger", icon="fa-solid fa-flag-checkered"), xs=6, md=4, xl=2),
            dbc.Col(kpi_card("Tkt. Médio", "card-ticket-medio", "info", sub_id="card-ticket-tkts", icon="fa-solid fa-receipt"), xs=6, md=4, xl=2),
            dbc.Col(kpi_card("Média Dia", "card-media-realizado", "warning", icon="fa-solid fa-calendar-check"), xs=6, md=4, xl=2),
        ]),

        # ── CHARTS ROW ────────────────────────────────────────────────────
        dbc.Row(className="g-2 mb-2", children=[
            dbc.Col(xs=12, lg=8, children=[
                html.Div(className="glass-card p-3 h-100", children=[
                    html.H6("Performance Diária vs Meta", className="mb-2 small fw-bold"),
                    dcc.Graph(id="daily-performance-chart", className="dash-graph", style={'height': '260px'}, config={'displayModeBar': False})
                ])
            ]),
            dbc.Col(xs=12, lg=4, children=[
                html.Div(className="glass-card p-3 h-100", children=[
                    html.H6(id="summary-chart-title", children="Resumo do Ciclo", className="mb-2 small fw-bold"),
                    dcc.Graph(id="summary-bar-chart", className="dash-graph", style={'height': '260px'}, config={'displayModeBar': False})
                ])
            ]),
        ]),

        # ── FINANCIAL DETAILS ROW ─────────────────────────────────────────
        dbc.Row(className="g-2", children=[
            dbc.Col(xs=12, md=4, children=[
                html.Div(className="glass-card p-3 h-100", children=[
                    html.P("Impacto em Vendas", className="extra-small text-muted mb-2 fw-bold"),
                    dbc.Row([
                        dbc.Col([
                            html.Div("Total Perdido", className="extra-small text-muted"),
                            html.Div(id="card-dev-canc-total", className="h4 text-danger fw-bold mb-0", children="---")
                        ]),
                        dbc.Col([html.Div(id="card-dev-canc-perc", className="small text-end fw-bold", children="---")])
                    ]),
                    html.Hr(className="my-2 opacity-10"),
                    dbc.Row([
                        dbc.Col([html.Small("Devoluções:", className="text-muted"), html.Div(id="card-dev-valor", className="small fw-bold")], width=6),
                        dbc.Col([html.Small("Cancelados:", className="text-muted"), html.Div(id="card-canc-valor", className="small fw-bold")], width=6),
                    ])
                ])
            ]),
            dbc.Col(xs=12, md=4, children=[
                html.Div(className="glass-card p-3 h-100", children=[
                    html.P("Políticas de Desconto", className="extra-small text-muted mb-2 fw-bold"),
                    dbc.Row([
                        dbc.Col([
                            html.Div("Total Concedido", className="extra-small text-muted"),
                            html.Div(id="card-descontos-total", className="h4 text-primary fw-bold mb-0", children="---")
                        ]),
                        dbc.Col([html.Div(id="card-descontos-perc", className="small text-end fw-bold", children="---")])
                    ]),
                    html.Hr(className="my-2 opacity-10"),
                    html.Div([html.Small("Ticket Médio de Desconto:", className="text-muted"), html.Div(id="card-descontos-medio", className="small fw-bold")])
                ])
            ]),
            dbc.Col(xs=12, md=4, children=[
                html.Div(className="glass-card p-3 h-100", children=[
                    html.P("Comissões & Prêmios", className="extra-small text-muted mb-2 fw-bold"),
                    dbc.Row([
                        dbc.Col([
                            html.Div("Remuneração Estimada", className="extra-small text-muted"),
                            html.Div(id="card-remuneracao-total", className="h4 text-success fw-bold mb-0", children="---")
                        ]),
                        dbc.Col([html.Div(id="card-premiacao", className="small text-end fw-bold", children="---")])
                    ]),
                    html.Hr(className="my-2 opacity-10"),
                    html.Div([html.Small("Comissão Base:", className="text-muted"), html.Div(id="card-comissao", className="small fw-bold")])
                ])
            ]),
        ]),
    ])

def get_page_content(pathname: str):
    """Retorna apenas o conteúdo interno da página solicitada."""
    if pathname == "/rankings":
        return rankings_layout()
    return sales_performance_content()

def get_dashboard_shell(current_user, seller_name: str = None, title: str = "Dashboard", content=None):
    """Retorna a estrutura (casca) do dashboard sem o conteúdo interno variável."""
    username = current_user.username
    role_upper = (current_user.role or "").upper()
    is_admin = role_upper == "ADMIN"

    return html.Div(
        id="dashboard-wrapper",
        className="app-container",
        children=[
            sidebar(),
            html.Div(
                id="content-area",
                className="content-area content-no-transition",
                children=[
                    # Header/Filtros
                    html.Div(id="dashboard-header-container", children=get_filters_bar(current_user, seller_name, title=title)),
                    
                    # Conteúdo Variável (onde a mágica da fluidez acontece)
                    html.Div(id="dashboard-inner-content", children=content),

                    # ── MODALS (Mantidos na casca para persistência) ─────────────────────────
                    dbc.Modal([
                        dbc.ModalHeader(dbc.ModalTitle("Gestão de Usuários"), close_button=True),
                        dbc.ModalBody([
                            html.Div(id="users-list-container", className="mb-4", style={'maxHeight': '300px', 'overflowY': 'auto'}),
                            html.Hr(),
                            html.H6("Criar / Editar Usuário", className="mb-3 fw-bold"),
                            dbc.Row(className="g-2", children=[
                                dbc.Col([dbc.Input(id="user-mgmt-username", placeholder="Usuário", size="sm")], width=6),
                                dbc.Col([dbc.Input(id="user-mgmt-password", placeholder="Senha", type="password", size="sm")], width=6),
                            ]),
                            dbc.Row(className="g-2 mt-2", children=[
                                dbc.Col([
                                    dcc.Dropdown(
                                        id="user-mgmt-role",
                                        options=[
                                            {'label': 'Admin', 'value': 'ADMIN'},
                                            {'label': 'Gerente', 'value': 'MANAGER'},
                                            {'label': 'Vendedor', 'value': 'SELLER'}
                                        ],
                                        placeholder="Papel",
                                        className="custom-dropdown"
                                    )
                                ], width=6),
                                dbc.Col([dbc.Input(id="user-mgmt-seller-id", placeholder="ID Vendedor (só para SELLER)", type="number", size="sm")], width=6),
                            ]),
                            dbc.Row(className="g-2 mt-2", children=[
                                dbc.Col([
                                    dcc.Dropdown(
                                        id="user-mgmt-company",
                                        options=get_companies(),
                                        placeholder="Filial (só para GERENTE)",
                                        className="custom-dropdown",
                                        multi=True,
                                    )
                                ], width=12),
                            ]),
                            html.Div(id="user-mgmt-status", className="mt-2 extra-small")
                        ]),
                        dbc.ModalFooter([
                            dbc.Button("Salvar Usuário", id="user-mgmt-save", color="primary", size="sm"),
                        ]),
                    ], id="users-modal", size="lg", is_open=False, className="glass-modal"),

                    dbc.Modal([
                        dbc.ModalHeader(
                            dbc.ModalTitle([
                                html.I(className="fa-solid fa-circle-user me-2", style={'color': 'var(--primary)'}),
                                "Meu Perfil"
                            ]),
                            close_button=True
                        ),
                        dbc.ModalBody([
                            html.Div(className="profile-user-info mb-4", children=[
                                html.Div(className="profile-avatar mx-auto mb-3", children=[
                                    html.I(className="fa-solid fa-user", style={'fontSize': '2rem', 'color': 'var(--primary)'})
                                ]),
                                html.H5(username, className="text-center mb-0 fw-bold"),
                                html.P(
                                    html.Span(
                                        {'ADMIN': 'Administrador', 'MANAGER': 'Gerente', 'SELLER': 'Vendedor'}.get(role_upper, role_upper),
                                        className="profile-role-badge"
                                    ),
                                    className="text-center mt-1 mb-0"
                                ),
                            ]),
                            html.Hr(className="my-3"),
                            html.H6([
                                html.I(className="fa-solid fa-lock me-2", style={'color': 'var(--warning)'}),
                                "Alterar Senha"
                            ], className="mb-3 fw-bold"),
                            dbc.Row(className="g-3", children=[
                                dbc.Col([
                                    dbc.Label("Senha Atual", className="extra-small text-muted fw-bold mb-1"),
                                    dbc.InputGroup([
                                        dbc.InputGroupText(html.I(className="fa-solid fa-key"), className="profile-input-icon"),
                                        dbc.Input(id="profile-current-password", type="password", placeholder="Digite sua senha atual", className="profile-input")
                                    ], className="profile-input-group")
                                ], width=12),
                                dbc.Col([
                                    dbc.Label("Nova Senha", className="extra-small text-muted fw-bold mb-1"),
                                    dbc.InputGroup([
                                        dbc.InputGroupText(html.I(className="fa-solid fa-lock-open"), className="profile-input-icon"),
                                        dbc.Input(id="profile-new-password", type="password", placeholder="Mínimo 6 caracteres", className="profile-input")
                                    ], className="profile-input-group")
                                ], width=12),
                                dbc.Col([
                                    dbc.Label("Confirmar Nova Senha", className="extra-small text-muted fw-bold mb-1"),
                                    dbc.InputGroup([
                                        dbc.InputGroupText(html.I(className="fa-solid fa-shield-halved"), className="profile-input-icon"),
                                        dbc.Input(id="profile-confirm-password", type="password", placeholder="Repita a nova senha", className="profile-input")
                                    ], className="profile-input-group")
                                ], width=12),
                            ]),
                            html.Div(id="profile-change-status", className="mt-3")
                        ]),
                        dbc.ModalFooter([
                            dbc.Button([html.I(className="fa-solid fa-xmark me-2"), "Cancelar"], id="profile-modal-cancel", color="secondary", size="sm", outline=True),
                            dbc.Button([html.I(className="fa-solid fa-floppy-disk me-2"), "Salvar Senha"], id="profile-save-password", color="primary", size="sm", className="fw-bold"),
                        ])
                    ], id="profile-modal", size="md", is_open=False, className="glass-modal profile-modal-custom"),

                    # Modal do Perfil do Cliente
                    dbc.Modal([
                        dbc.ModalHeader(
                            dbc.ModalTitle([
                                html.I(className="fa-solid fa-address-card me-2", style={'color': 'var(--primary)'}),
                                "Perfil Avançado do Cliente"
                            ]),
                            close_button=True
                        ),
                        dbc.ModalBody(id="client-profile-modal-body", children=[
                            dbc.Spinner(color="primary", children=html.Div(id="client-profile-content"))
                        ]),
                        dbc.ModalFooter(
                            dbc.Button([html.I(className="fa-solid fa-xmark me-2"), "Fechar"], id="close-client-profile", color="secondary", size="sm", outline=True)
                        )
                    ], id="client-profile-modal", size="lg", is_open=False, className="glass-modal client-modal-wide"),
                    # Modal do Perfil da Marca
                    dbc.Modal([
                        dbc.ModalHeader(
                            dbc.ModalTitle([
                                html.I(className="fa-solid fa-tags me-2", style={'color': 'var(--success)'}),
                                "Top 5 Produtos da Marca"
                            ]),
                            close_button=True
                        ),
                        dbc.ModalBody(id="brand-profile-modal-body", children=[
                            dbc.Spinner(color="success", children=html.Div(id="brand-profile-content"))
                        ]),
                        dbc.ModalFooter(
                            dbc.Button([html.I(className="fa-solid fa-xmark me-2"), "Fechar"], id="close-brand-profile", color="secondary", size="sm", outline=True)
                        )
                    ], id="brand-profile-modal", size="md", is_open=False, className="glass-modal profile-modal-custom")
                ]
            )
        ]
    )

def create_layout(current_user, seller_name: str = None, pathname: str = "/"):
    """
    Função de compatibilidade que retorna o layout completo.
    Idealmente, será substituída pelo uso direto de get_dashboard_shell + get_page_content.
    """
    title = "Sales Performance" if pathname == "/" else "TOP 10 Rankings"
    content = get_page_content(pathname)
    return get_dashboard_shell(current_user, seller_name, title=title, content=content)
