# 🤝 Contribuindo para Dash Ticket Vendedor

Obrigado por considerar contribuir para este projeto! Este documento fornece diretrizes e procedimentos.

## 📋 Como Reportar Bugs

### Antes de Reportar
- ✅ Verifique se o bug já foi reportado
- ✅ Reproduza o bug em ambiente local
- ✅ Colete logs relevantes

### Ao Reportar
```markdown
**Descrição**
Uma descrição clara do bug.

**Passos para Reproduzir**
1. ...
2. ...

**Comportamento Esperado**
O que deveria acontecer.

**Comportamento Observado**
O que realmente aconteceu.

**Logs**
```
Cole logs relevantes aqui
```

**Ambiente**
- Python: 3.12
- PostgreSQL: 15
- OS: Ubuntu 22.04
```

## 🎯 Sugerindo Features

### Antes de Sugerir
- ✅ Verifique se não existe issue similar
- ✅ Verifique o [roadmap](ARCHITECTURE.md#11-roadmap-futuro)

### Ao Sugerir
```markdown
**Descrição da Feature**
O que você quer adicionar?

**Caso de Uso**
Por que essa feature é importante?

**Solução Proposta**
Como você implementaria?

**Alternativas Consideradas**
Outras formas de resolver o problema?
```

## 🔧 Setup para Desenvolvimento

```bash
# 1. Fork o repositório
# 2. Clone seu fork
git clone https://github.com/seu-usuario/dash_ticket_vendedor.git
cd dash_ticket_vendedor

# 3. Adicionar upstream
git remote add upstream https://github.com/original-owner/dash_ticket_vendedor.git

# 4. Criar branch
git checkout -b feature/sua-feature

# 5. Setup local (veja SETUP_LOCAL.md)
source venv/bin/activate
pip install -r requirements.txt

# 6. Fazer mudanças
# 7. Rodar testes
pytest tests/ -v

# 8. Commit e push
git add .
git commit -m "feat: descrição clara da mudança"
git push origin feature/sua-feature

# 9. Abrir Pull Request
```

## 📝 Estilo de Código

### Python

```python
# ✅ Bom
def get_seller_performance(
    seller_id: int,
    start_date: datetime.date,
    end_date: datetime.date
) -> pd.DataFrame:
    """
    Retorna performance do vendedor em período.
    
    Args:
        seller_id: ID do vendedor
        start_date: Data inicial
        end_date: Data final
        
    Returns:
        DataFrame com dados de performance
    """
    query = """
    SELECT * FROM fact_sales
    WHERE seller_id = %s AND date BETWEEN %s AND %s
    """
    return pd.read_sql(query, self.conn, params=[seller_id, start_date, end_date])

# ❌ Ruim
def get_data(id, d1, d2):
    q = f"SELECT * FROM fact_sales WHERE seller_id = {id} AND date BETWEEN '{d1}' AND '{d2}'"
    return pd.read_sql(q, self.conn)
```

### Regras
- ✅ Type hints obrigatórios
- ✅ Docstrings para funções públicas
- ✅ 4 espaços de indentação
- ✅ Max 88 caracteres por linha
- ✅ Variáveis em snake_case
- ✅ Classes em PascalCase
- ✅ Use f-strings (não .format)

### Ferramentas
```bash
# Formatação
black src/

# Lint
flake8 src/ --max-line-length=88

# Type checking
mypy src/ --strict

# Tests
pytest tests/ -v --cov=src
```

## ✅ Checklist antes de PR

- [ ] Código está formatado (`black`)
- [ ] Sem linting errors (`flake8`)
- [ ] Testes passam (`pytest`)
- [ ] Type hints em funções novas
- [ ] Docstrings em funções públicas
- [ ] Commit message descreve mudança
- [ ] PR referencia issue relevante

## 🧪 Testes

```bash
# Todos os testes
pytest tests/ -v

# Testes específicos
pytest tests/unit/test_auth.py -v

# Com cobertura
pytest tests/ --cov=src --cov-report=html

# Watch (re-run ao salvar)
pytest-watch tests/
```

## 📚 Documentação

Se adiciona feature, documenta:

1. **Code comments** — Por que, não como
2. **Docstrings** — Função, argumentos, return
3. **README.md** — Se afeta usuário final
4. **ARCHITECTURE.md** — Se muda design
5. **Tests** — Como usar a feature

## 🔄 Processo de Review

1. ✅ Code review (2+ mantainers)
2. ✅ CI/CD passa (testes, lint, type checks)
3. ✅ 1 aprovação de maintainer
4. ✅ Merge para main

## 📦 Release Process

```bash
# 1. Criar tag
git tag -a v1.2.3 -m "Release 1.2.3"

# 2. Push tag
git push upstream v1.2.3

# 3. GitHub Actions cria release automaticamente
# (Futuro: PyPI package)
```

## 💬 Comunicação

- **Issues:** Bugs e features
- **Discussions:** Perguntas e ideias
- **Pull Requests:** Código
- **Email:** Para questões sensíveis

## 📖 Documentação Importante

Leia antes de contribuir:
- [ARCHITECTURE.md](../ARCHITECTURE.md) — Entender design
- [SETUP_LOCAL.md](../SETUP_LOCAL.md) — Setup local
- [DATA_MODEL.md](../DATA_MODEL.md) — Schema do banco

## 🎓 Recursos Úteis

- [Dash Documentation](https://dash.plotly.com)
- [PostgreSQL Docs](https://www.postgresql.org/docs)
- [Python Type Hints](https://peps.python.org/pep-0484)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)

## 🙏 Agradecimentos

Valorizamos toda contribuição! Cada PR faz o projeto melhor.

---

**Dúvidas?** Abra uma issue com tag `[QUESTION]`
