"""Login do painel: um único admin, lido do .env (ADMIN_USUARIO e ADMIN_SENHA).

É uma trava de demonstração, não de segurança: a senha fica em texto no .env e o login
dura enquanto a aba estiver aberta (o F5 pede para entrar de novo).
"""
import hmac
import os


def _admin() -> tuple[str, str]:
    return os.getenv("ADMIN_USUARIO", "").strip(), os.getenv("ADMIN_SENHA", "")


def configurado() -> bool:
    usuario, senha = _admin()
    return bool(usuario and senha)


def confere(usuario: str, senha: str) -> bool:
    if not configurado():
        return False
    esperado_usuario, esperado_senha = _admin()
    usuario_ok = hmac.compare_digest(usuario.strip().encode(), esperado_usuario.encode())
    senha_ok = hmac.compare_digest(senha.encode(), esperado_senha.encode())
    return usuario_ok and senha_ok
