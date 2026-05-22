import dash_bootstrap_components as dbc
from dash import html

def ranking_list(title, items, icon, color="primary", total_id=None, list_id=None):
    """
    items: list of dicts like {'rank': 1, 'name': 'NIKE', 'value': 'R$ 234.560,80'}
    """
    
    header = html.Div(className="d-flex align-items-center justify-content-between mb-4", children=[
        html.Div(className="d-flex align-items-center", children=[
            html.Div(className=f"kpi-icon-container bg-{color}-soft me-3", children=[
                html.I(className=f"{icon} text-{color}")
            ]),
            html.H6(title, className="mb-0 fw-bold")
        ]),
        html.Div(className="text-end", children=[
            html.Small("Total", className="text-muted d-block extra-small fw-bold"),
            html.Span("---", id=total_id, className=f"fw-bold text-{color}")
        ]) if total_id else None
    ])

    list_items = []
    for i, item in enumerate(items):
        item_id = item.get('id_item', i)
        
        # Se for a lista de clientes, adicionamos um id para o callback (Pattern-Matching) e estilo de cursor
        props = {}
        if list_id == 'rank-list-clientes' and 'id_item' in item:
            props['id'] = {'type': 'client-rank-item', 'index': item_id}
            props['style'] = {'cursor': 'pointer', 'transition': 'transform 0.2s'}
            props['className'] = "d-flex align-items-center justify-content-between ranking-item mb-2 rounded-3 client-clickable-item"
        else:
            props['className'] = "d-flex align-items-center justify-content-between ranking-item mb-2 rounded-3"
            
        list_items.append(
            html.Div(n_clicks=0, **props, children=[
                html.Div(className="d-flex align-items-center", children=[
                    html.Div(str(item['rank']), className=f"rank-badge bg-{color}"),
                    html.Span(item['name'], className="ms-3 fw-bold text-truncate", style={'maxWidth': '160px'})
                ]),
                html.Span(item['value'], className="fw-bold small")
            ])
        )

    return html.Div(className="glass-card p-4 h-100", children=[
        header,
        html.Div(list_items, id=list_id, className="ranking-body")
    ])
