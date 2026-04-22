def test_fmt_brl():
    from src.shared.utils.formatters import fmt_brl
    assert fmt_brl(1000.5) == "R$ 1.000,50"
    assert fmt_brl(0) == "R$ 0,00"
    assert fmt_brl(-50.25) == "R$ -50,25"
    assert fmt_brl(1234567.89) == "R$ 1.234.567,89"

def test_fmt_brl_compact():
    from src.shared.utils.formatters import fmt_brl_compact
    assert fmt_brl_compact(1500) == "R$ 1,5K"
    assert fmt_brl_compact(2500000) == "R$ 2,50M"
    assert fmt_brl_compact(500) == "R$ 500,00"

def test_fmt_pct():
    from src.shared.utils.formatters import fmt_pct
    assert fmt_pct(50.555) == "50,6%"
    assert fmt_pct(100) == "100,0%"
    assert fmt_pct(0) == "0,0%"
