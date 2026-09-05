"""Resolves the real client IP behind a trusted reverse-proxy chain.

Production runs: Client -> Caddy -> nginx -> Uvicorn/FastAPI. Caddy has no
`trusted_proxies` of its own configured, so it discards whatever
`X-Forwarded-For` a client sent it and replaces it with a single, honest
entry (the real client IP it saw on the socket) — a client cannot inject fake
entries there. nginx then appends its own view of the sender
(`$proxy_add_x_forwarded_for`), so the header Uvicorn actually receives looks
like `"<real-client-ip>, <caddy-ip>"`: exactly one hop of *trusted* appending
happened between the header's honest starting value and here.

`trusted_proxy_count` is that number of trusted appends — 1 in this
deployment's Caddy+nginx chain, 0 for local/dev (direct connections, where
`X-Forwarded-For` is not authenticated at all and must be ignored). Given N
trusted hops, the real client IP is always the (N+1)-th entry counting from
the *right* — this is safe against a client prepending arbitrary fake entries
of its own on the left, since those never affect which position we read from
the right.
"""
from fastapi import Request


def get_client_ip(request: Request, trusted_proxy_count: int) -> str:
    if trusted_proxy_count > 0:
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            hops = [hop.strip() for hop in forwarded_for.split(",") if hop.strip()]
            if len(hops) >= trusted_proxy_count + 1:
                return hops[-(trusted_proxy_count + 1)]
            # Fewer hops than configured trusted proxies — the header is
            # malformed or the deployment's proxy count doesn't match reality.
            # Falling through to the direct socket peer is the safe default
            # (it identifies the nearest proxy, not the real client, but
            # never trusts an attacker-controlled value as if it were one).

    if request.client is None:
        return "unknown"
    return request.client.host
