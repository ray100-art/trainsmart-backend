"""CSRF protection for cookie-authenticated state-changing requests.

Double-submit pattern adapted for cross-origin SPAs:
  - Cookie `trainsmart_csrf` (readable when same-origin)
  - Response header `X-CSRF-Token` (exposed via CORS for cross-origin SPAs)
  - Mutating requests must send matching `X-CSRF-Token` request header
"""
from __future__ import annotations

import secrets
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import settings

CSRF_COOKIE = "trainsmart_csrf"
CSRF_HEADER = "x-csrf-token"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

_EXEMPT_PREFIXES = (
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/v1/certificates/verify",
    "/api/v1/auth/login",
    "/api/v1/auth/forgot-password",
    "/api/v1/auth/setup-password",
)


def _is_exempt(path: str) -> bool:
    if path == "/" or path.startswith("/docs") or path.startswith("/redoc"):
        return True
    return any(path.startswith(p) for p in _EXEMPT_PREFIXES)


def _set_csrf(response: Response, token: str) -> None:
    response.set_cookie(
        key=CSRF_COOKIE,
        value=token,
        httponly=False,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite_effective,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    response.headers["X-CSRF-Token"] = token


class CsrfMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if not settings.csrf_enabled:
            return await call_next(request)

        path = request.url.path
        method = request.method.upper()
        cookie_token = request.cookies.get(CSRF_COOKIE)

        if method not in SAFE_METHODS and not _is_exempt(path):
            auth_cookie = request.cookies.get(settings.COOKIE_NAME)
            if auth_cookie:
                header_token = request.headers.get(CSRF_HEADER)
                if not cookie_token or not header_token or not secrets.compare_digest(cookie_token, header_token):
                    return JSONResponse(
                        status_code=403,
                        content={"detail": "CSRF validation failed. Refresh the page and try again."},
                    )

        response = await call_next(request)

        if method in SAFE_METHODS or not cookie_token:
            token = cookie_token or secrets.token_urlsafe(32)
            _set_csrf(response, token)
        elif cookie_token:
            response.headers["X-CSRF-Token"] = cookie_token

        return response
