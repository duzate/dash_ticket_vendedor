import dash_bootstrap_components as dbc
from dash import html

def _nav_item(icon_class: str, label: str, subtitle: str, href: str):
    """Helper para criar itens de navegação com label e subtítulo."""
    return dbc.NavLink(
        [
            html.I(className=f"{icon_class} nav-icon"),
            html.Div([
                html.Span(label, className="nav-label"),
                html.Small(subtitle, className="nav-subtitle")
            ], className="nav-info")
        ],
        href=href,
        active="exact",
        className="nav-link-custom"
    )

def sidebar():
    return html.Div(
        id="sidebar",
        className="sidebar sidebar-no-transition",
        children=[
            # Top Header: Hamburger + Logo
            html.Div(className="sidebar-header", children=[
                html.Button(
                    html.I(className="fa-solid fa-bars"),
                    id="sidebar-toggle",
                    className="sidebar-toggle-btn"
                ),
                html.Div(className="sidebar-logo", children=[
                    html.I(className="fa-solid fa-gauge-high"),
                    html.Span("Sankhya Dash")
                ]),
            ]),
            
            # Navegação Principal
            dbc.Nav(
                [
                    _nav_item("fa-solid fa-chart-simple", "Ticket Médio", "Análise de vendedores", "/"),
                    _nav_item("fa-solid fa-chart-line", "TOP 10", "Rankings e análises", "/rankings"),
                ],
                vertical=True,
                pills=True,
                className="sidebar-nav"
            ),
            
            # Footer Info (visto na imagem de referência)
            html.Div(className="sidebar-footer-info mt-auto", children=[
                html.Small("Dashboard Analytics", className="footer-text"),
                html.Small("v1.0.0", className="footer-version")
            ])
        ]
    )
