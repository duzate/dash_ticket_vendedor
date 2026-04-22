"""
formatters.py — Utilitários de formatação de valores monetários (BRL).
"""


def fmt_brl(value: float | None) -> str:
    """Formata um número como moeda BRL. Ex: 1234.56 → 'R$ 1.234,56'."""
    try:
        v = float(value or 0)
        return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return "R$ 0,00"


def fmt_brl_compact(value: float | None) -> str:
    """Versão compacta do BRL. Ex: 1500000 → 'R$ 1,50M'."""
    try:
        v = float(value or 0)
        if abs(v) >= 1_000_000:
            return f"R$ {v / 1_000_000:.2f}M".replace(".", ",")
        if abs(v) >= 1_000:
            return f"R$ {v / 1_000:.1f}K".replace(".", ",")
        return fmt_brl(v)
    except (TypeError, ValueError):
        return "R$ 0,00"


def fmt_pct(value: float | None, decimals: int = 1) -> str:
    """Formata um número como percentual. Ex: 95.7 → '95,7%'."""
    try:
        return f"{float(value or 0):.{decimals}f}%".replace(".", ",")
    except (TypeError, ValueError):
        return "0,0%"
