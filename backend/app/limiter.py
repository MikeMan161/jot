"""
Request rate limiting.

Two mechanisms guard the AI endpoint, and the split is deliberate:

  - Short-window burst limits live here, in process memory. That is correct rather
    than lazy: gunicorn runs a single worker (see Procfile), so one process holds
    every counter and there is nothing to synchronise. They reset on redeploy, which
    is fine — a per-minute limit only needs to survive seconds.
  - The daily cost cap lives in Postgres (see services/usage.py), because a redeploy
    resets memory but not the Anthropic bill.

Limits are applied with per-route decorators rather than by adding SlowAPIMiddleware
with default_limits. The middleware would raise RateLimitExceeded *outside* the route,
where FastAPI's exception handling sits outside CORSMiddleware — so the 429 would come
back without CORS headers and the browser would report it as a CORS failure instead of
a rate limit. Raising inside the route keeps the handler within the CORS wrapper. The
tradeoff is that undecorated routes have no blanket limit; the endpoints that cost
money or create accounts are all decorated explicitly below their route definitions.
"""
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.auth import verify_token


def user_or_ip(request: Request) -> str:
    """
    Rate-limit key for authenticated routes: the user's id, falling back to client IP
    when there is no usable token.

    Keying /ai/parse by user rather than by IP matters on demo day. Judges on the same
    venue wifi share a public IP, and IP-keyed limits would have them throttling each
    other after the first few taps. Keying by user also means a demo visitor cannot
    escape their own limit by reconnecting.
    """
    authorization = request.headers.get("authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() == "bearer" and token:
        payload = verify_token(token)
        if payload and payload.get("sub"):
            return f"user:{payload['sub']}"
    return f"ip:{get_remote_address(request)}"


# key_func here is the default for any decorator that does not override it. Routes that
# run before a user exists (register, login, demo) rely on this IP default; /ai/parse
# passes key_func=user_or_ip explicitly.
limiter = Limiter(key_func=get_remote_address)
