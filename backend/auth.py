"""
Autenticação simples por token (Bearer).

O token fica só no .env do celular servidor (AUTH_TOKEN=...).
O frontend guarda o token digitado pelo usuário no localStorage do
navegador dele (não no repositório, não no código-fonte) e manda
em cada requisição via header Authorization: Bearer <token>.
"""
from fastapi import Header, HTTPException, WebSocket, status
from typing import Optional
from . import config


def require_auth(authorization: Optional[str] = Header(default=None)):
    if config.ALLOW_NO_AUTH:
        return True
    if not config.AUTH_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AUTH_TOKEN não configurado no .env do servidor.",
        )
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Não autenticado")
    token = authorization.removeprefix("Bearer ").strip()
    if token != config.AUTH_TOKEN:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
    return True


async def require_auth_ws(websocket: WebSocket) -> bool:
    """Autenticação para WebSocket: token vem via query string ?token=..."""
    if config.ALLOW_NO_AUTH:
        return True
    token = websocket.query_params.get("token", "")
    if not config.AUTH_TOKEN or token != config.AUTH_TOKEN:
        await websocket.close(code=4401)
        return False
    return True
