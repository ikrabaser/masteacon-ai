"""Tests for trusted-proxy-aware client IP resolution."""
from starlette.datastructures import Headers
from starlette.requests import Request

from app.core.client_ip import get_client_ip


def _make_request(headers: dict[str, str] | None = None, client_host: str | None = "10.0.0.99") -> Request:
    scope = {
        "type": "http",
        "headers": Headers(headers or {}).raw,
        "client": (client_host, 12345) if client_host else None,
    }
    return Request(scope)


def test_trusted_proxy_count_zero_ignores_x_forwarded_for() -> None:
    request = _make_request(headers={"x-forwarded-for": "1.2.3.4"}, client_host="10.0.0.99")

    assert get_client_ip(request, trusted_proxy_count=0) == "10.0.0.99"


def test_trusted_proxy_count_one_picks_the_hop_before_the_last() -> None:
    # Caddy set "client_ip", nginx appended its own IP -> "client_ip, nginx_ip"
    request = _make_request(headers={"x-forwarded-for": "203.0.113.5, 172.18.0.3"})

    assert get_client_ip(request, trusted_proxy_count=1) == "203.0.113.5"


def test_extra_hops_prepended_by_a_spoofing_client_are_ignored() -> None:
    # An attacker prepending fake entries must not shift which position we
    # read from - we always count from the right, not the left.
    request = _make_request(headers={"x-forwarded-for": "9.9.9.9, 8.8.8.8, 203.0.113.5, 172.18.0.3"})

    assert get_client_ip(request, trusted_proxy_count=1) == "203.0.113.5"


def test_missing_header_falls_back_to_the_direct_socket_peer() -> None:
    request = _make_request(headers={}, client_host="172.18.0.3")

    assert get_client_ip(request, trusted_proxy_count=1) == "172.18.0.3"


def test_fewer_hops_than_configured_falls_back_to_the_socket_peer() -> None:
    # Header present but shorter than expected (misconfiguration/malformed) -
    # never trust it blindly, fall back to the direct peer instead.
    request = _make_request(headers={"x-forwarded-for": "203.0.113.5"}, client_host="172.18.0.3")

    assert get_client_ip(request, trusted_proxy_count=1) == "172.18.0.3"


def test_no_client_and_no_header_returns_unknown() -> None:
    request = _make_request(headers={}, client_host=None)

    assert get_client_ip(request, trusted_proxy_count=0) == "unknown"
