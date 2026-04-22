import dash_bootstrap_components as dbc
from dash import html
import plotly.graph_objects as go

# ─── Plotly Base Layout ───────────────────────────────────────────────────────
PLOTLY_LAYOUT_BASE = dict(
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    font=dict(family='Inter, -apple-system, sans-serif', color='#f1f5f9', size=12.5),
    showlegend=True,
    legend=dict(
        orientation="h",
        yanchor="bottom", y=1.05,
        xanchor="center", x=0.5,
        bgcolor='rgba(0,0,0,0)',
        font=dict(size=11, color='#94a3b8'),
        itemsizing='constant',
    ),
    margin=dict(l=10, r=10, t=25, b=20),
    xaxis=dict(
        gridcolor='rgba(255,255,255,0.03)',
        zerolinecolor='rgba(255,255,255,0.06)',
        tickfont=dict(color='#64748b', size=10),
        showline=False,
        showgrid=True,
    ),
    yaxis=dict(
        gridcolor='rgba(255,255,255,0.03)',
        zerolinecolor='rgba(255,255,255,0.06)',
        tickfont=dict(color='#64748b', size=10),
        showline=False,
        showgrid=True,
    ),
    hovermode='closest',
    hoverlabel=dict(
        bgcolor='#0f172a',
        font_size=13,
        font_family='Inter, sans-serif',
        font_color='white',
        bordercolor='rgba(148, 163, 184, 0.2)',
    ),
    transition=dict(duration=500, easing='cubic-in-out'),
)


# ─── KPI Card Component ───────────────────────────────────────────────────────
def kpi_card(label, value_id, accent="primary", sub_id=None, icon=None):
    """Card KPI reutilizável com acento colorido."""
    icon_el = html.Div(className=f"kpi-icon-container bg-{accent}-soft", children=[
        html.I(className=f"{icon} text-{accent}", style={'fontSize': '0.9rem'})
    ]) if icon else None

    header = html.Div(className="d-flex align-items-start justify-content-between", children=[
        html.Span(label, className="kpi-label"),
        icon_el,
    ])

    body = [
        header,
        html.Div(id=value_id, className=f"kpi-value text-{accent}", children="---"),
    ]
    if sub_id:
        body.append(html.Span(id=sub_id, className="kpi-sub", children=""))

    return dbc.Card(
        dbc.CardBody(body, className="p-0"),
        className="kpi-card-premium h-100",
        style={'padding': '20px'},
    )
