from dash import html
import dash_bootstrap_components as dbc

# ─── Login Layout ─────────────────────────────────────────────────────────────
login_layout = html.Div(
    className="login-wrapper",
    children=[
        html.Div(className="login-card", children=[
            html.Div(className="login-logo-container", children=[
                html.I(className="fa-solid fa-chart-line text-primary", style={'fontSize': '2rem'}),
            ]),
            html.H2("", className="text-white text-center fw-extrabold mb-1", 
                    style={'fontSize': '2rem', 'letterSpacing': '-0.03em', 'fontFamily': 'var(--font-display)'}),
            html.P("Sankhya · BI Analítico", className="text-center mb-5",
                   style={'fontSize': '0.75rem', 'letterSpacing': '0.2em', 'color': 'rgba(255,255,255,0.4)', 'fontWeight': '700', 'textTransform': 'uppercase'}),
            
            html.Div(className="mb-4", children=[
                html.Label("Usuário", className="mb-2 ms-1", 
                           style={'fontSize': '0.7rem', 'fontWeight': '800', 'textTransform': 'uppercase', 'letterSpacing': '0.1em', 'color': 'var(--primary)'}),
                dbc.Input(id='login-username', placeholder='Digite seu usuário', type='text',
                          className="login-input"),
            ]),
            
            html.Div(className="mb-4", children=[
                html.Label("Senha", className="mb-2 ms-1", 
                           style={'fontSize': '0.7rem', 'fontWeight': '800', 'textTransform': 'uppercase', 'letterSpacing': '0.1em', 'color': 'var(--primary)'}),
                dbc.Input(id='login-password', placeholder='••••••••', type='password',
                          className="login-input"),
            ]),
            
            dbc.Button([
                html.Span("Acessar Plataforma", className="me-2"),
                html.I(className="fa-solid fa-chevron-right", style={'fontSize': '0.8rem'})
            ], id='login-button', className="login-button w-100"),
            
            html.Div(id='login-alert', className="text-danger text-center mt-4",
                     style={'fontSize': '0.85rem', 'fontWeight': '600'}),
            
            html.Div(className="mt-5 text-center", children=[
                html.P("© 2026 Nova Auto Peças · Soluções Inteligentes", 
                       className="login-footer-text")
            ])
        ])
    ]
)
