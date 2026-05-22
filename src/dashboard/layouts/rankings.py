import dash_bootstrap_components as dbc
from dash import html
from components.ranking_list import ranking_list

def rankings_layout():
    return html.Div([
        html.Div(className="rankings-header", children=[
            html.Div(className="d-flex align-items-center mb-1", children=[
                html.I(className="fa-solid fa-arrow-trend-up text-primary me-2"),
                html.H4("TOP 10 Rankings", className="mb-0 fw-bold"),
            ]),
            html.P("Análise de desempenho por categoria", className="text-muted mb-0 small fw-bold"),
        ]),
        
        dbc.Row([
            dbc.Col(ranking_list("TOP 10 Clientes", [], "fa-solid fa-users", "primary", 
                                total_id="rank-total-clientes", list_id="rank-list-clientes"), xs=12, lg=4),
            dbc.Col(ranking_list("TOP 10 Marcas", [], "fa-solid fa-tag", "success", 
                                total_id="rank-total-marcas", list_id="rank-list-marcas"), xs=12, lg=4),
            dbc.Col(ranking_list("TOP 10 Produtos", [], "fa-solid fa-box-archive", "warning", 
                                total_id="rank-total-produtos", list_id="rank-list-produtos"), xs=12, lg=4),
        ], className="g-4")
    ])
