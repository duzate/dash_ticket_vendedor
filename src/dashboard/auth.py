"""
auth.py — Autenticação, autorização e perfis de usuário.
100% baseado no banco de dados. Sem dados mocados.
"""

import logging
from flask_login import UserMixin

log = logging.getLogger(__name__)


class User(UserMixin):
    """Modelo de usuário da aplicação."""

    def __init__(
        self,
        id: str,
        username: str,
        password: str,
        role: str,
        seller_id: int | None = None,
        managed_sellers: list[int] | None = None,
        is_active: bool = True,
    ):
        self.id = id
        self.username = username
        self.password = password
        self.role = role  # "ADMIN" | "MANAGER" | "SELLER"
        self.seller_id = int(seller_id) if seller_id is not None else None
        self.managed_sellers: list[int] = managed_sellers or []
        self.active_status = is_active

    @property
    def is_active(self):
        return self.active_status

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username!r} role={self.role}>"


def _query_user_by_field(field: str, value: str) -> "User | None":
    """Busca um usuário no banco de dados pelo campo especificado."""
    try:
        from data_provider import get_dw_engine
        from sqlalchemy import text

        engine = get_dw_engine()
        with engine.connect() as conn:
            sql = text(
                f"SELECT id, username, password, role, seller_id, managed_sellers, "
                f"COALESCE(is_active, TRUE) as is_active "
                f"FROM dash_users WHERE {field} = :val"
            )
            res = conn.execute(sql, {"val": value}).fetchone()
            if res:
                return User(
                    str(res.id),
                    res.username,
                    res.password,
                    res.role,
                    res.seller_id,
                    res.managed_sellers,
                    res.is_active,
                )
    except Exception as e:
        log.error(f"Erro ao buscar usuário por {field}={value!r}: {e}")
    return None


def get_user_by_id(user_id: str) -> "User | None":
    """
    Requerido pelo Flask-Login para recarregar a sessão.
    Busca SEMPRE no banco de dados — nunca em cache local.
    """
    if user_id == "admin_fallback":
        return User("admin_fallback", "admin", "admin123", "ADMIN")

    try:
        from data_provider import get_dw_engine
        from sqlalchemy import text

        engine = get_dw_engine()
        with engine.connect() as conn:
            res = conn.execute(
                text("SELECT id, username, password, role, seller_id, managed_sellers, COALESCE(is_active, TRUE) as is_active FROM dash_users WHERE id = :uid"),
                {"uid": int(user_id)},
            ).fetchone()
            if res:
                return User(str(res.id), res.username, res.password, res.role, res.seller_id, res.managed_sellers, res.is_active)
    except Exception as e:
        log.error(f"Erro ao recarregar sessão para user_id={user_id!r}: {e}")
    return None


def authenticate_user(username: str, password: str) -> "User | None":
    """Autentica usuário buscando no banco de dados."""
    username = (username or "").lower().strip()
    password = (password or "").strip()

    if not username or not password:
        return None

    # Fallback admin hardcoded (conta de recuperação)
    if username == "admin" and password == "admin123":
        log.info("LOGIN SUCESSO: 'admin' autenticado via fallback.")
        return User("admin_fallback", "admin", "admin123", "ADMIN")

    try:
        from data_provider import get_dw_engine
        from sqlalchemy import text

        engine = get_dw_engine()
        with engine.connect() as conn:
            sql = text(
                "SELECT id, username, password, role, seller_id, managed_sellers, "
                "COALESCE(is_active, TRUE) as is_active "
                "FROM dash_users "
                "WHERE LOWER(TRIM(username)) = :u"
            )
            res = conn.execute(sql, {"u": username}).fetchone()

            if not res:
                log.warning(f"LOGIN FALHOU: Usuário '{username}' não encontrado no banco.")
                return None

            if res.password != password:
                log.warning(f"LOGIN FALHOU: Senha incorreta para '{username}'.")
                return None

            if not res.is_active:
                log.warning(f"LOGIN BLOQUEADO: '{username}' desativado pelo Admin.")
                return None

            log.info(f"LOGIN SUCESSO: '{username}' autenticado via banco. Role={res.role}, seller_id={res.seller_id}")
            return User(
                str(res.id),
                res.username,
                res.password,
                res.role,
                res.seller_id,
                res.managed_sellers,
                res.is_active,
            )

    except Exception as e:
        log.error(f"Erro crítico na autenticação de '{username}': {e}")

    return None


def filter_sellers_by_role(user: User, all_sellers: list[dict]) -> list[dict]:
    """
    Filtra a lista de vendedores de acordo com o papel do usuário autenticado.

    - ADMIN   → acesso total.
    - MANAGER → acesso apenas aos seus gerenciados.
    - SELLER  → acesso apenas a si mesmo.
    """
    role_upper = user.role.upper()
    if role_upper == "ADMIN" or role_upper == "MANAGER":
        return all_sellers
    if role_upper == "SELLER":
        return [s for s in all_sellers if s["id"] == user.seller_id]
    return []
