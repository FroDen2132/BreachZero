"""Mock-httpx tests for the RDAP-based WHOIS enricher (no real network access)."""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.enrichers.whois import WhoisEnricher  # noqa: E402


def _enrich(handler, ioc_type, value):
    enricher = WhoisEnricher(transport=httpx.MockTransport(handler))
    return asyncio.run(enricher.enrich(ioc_type, value, {}))


def test_private_ip_makes_no_external_request() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={})

    card = _enrich(handler, "ip", "192.168.1.10")
    assert calls == []
    assert card.status == "OK"
    assert card.verdict_signal == "INFO"
    assert card.icon_id == "fallback-globe"


def test_public_ip_follows_redirect_and_parses_rdap() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "rdap.org":
            return httpx.Response(302, headers={"location": "https://rdap.arin.net/registry/ip/8.8.8.8"})
        return httpx.Response(
            200,
            json={
                "name": "GOGL",
                "handle": "NET-8-8-8-0-2",
                "country": "US",
                "events": [{"eventAction": "registration", "eventDate": "2023-12-28T17:24:56Z"}],
            },
        )

    card = _enrich(handler, "ip", "8.8.8.8")
    assert card.status == "OK"
    assert card.details["name"] == "GOGL"
    assert card.details["country"] == "US"
    assert card.details["registered"] == "2023-12-28"
    assert "GOGL" in card.summary


def test_new_domain_is_suspicious() -> None:
    recent = (datetime.now(timezone.utc) - timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%SZ")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/domain/evil-login.com"
        return httpx.Response(
            200,
            json={
                "ldhName": "EVIL-LOGIN.COM",
                "events": [{"eventAction": "registration", "eventDate": recent}],
                "entities": [
                    {"roles": ["registrar"], "vcardArray": ["vcard", [["fn", {}, "text", "Cheap Registrar"]]]}
                ],
            },
        )

    card = _enrich(handler, "domain", "evil-login.com")
    assert card.status == "OK"
    assert card.verdict_signal == "SUSPICIOUS"
    assert card.details["age_days"] == 3
    assert card.details["registrar"] == "Cheap Registrar"


def test_http_error_returns_unavailable_zero_cost() -> None:
    card = _enrich(lambda r: httpx.Response(500), "domain", "example.com")
    assert card.status == "UNAVAILABLE"
    assert card.query_cost_applied == 0


def test_timeout_returns_unavailable_zero_cost() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timeout", request=request)

    card = _enrich(handler, "ip", "8.8.8.8")
    assert card.status == "UNAVAILABLE"
    assert card.query_cost_applied == 0


def test_internal_domain_makes_no_external_request() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={})

    for name in ("ad-dc-01.corp.local", "localhost", "fileserver.internal"):
        card = _enrich(handler, "domain", name)
        assert card.status == "OK"
        assert card.verdict_signal == "INFO"
    assert calls == []


def test_malformed_domain_is_rejected_without_request() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={})

    for bad in ("evil.com/../ip/1.1.1.1", "a.com?x=1", "evil.com#frag", "a b.com", ""):
        card = _enrich(handler, "domain", bad)
        assert card.status == "UNAVAILABLE"
        assert card.query_cost_applied == 0
    assert calls == []


def test_non_global_ips_make_no_external_request() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={})

    for ip in ("10.0.0.5", "172.16.4.4", "127.0.0.1", "169.254.1.1", "100.64.0.1", "224.0.0.1"):
        card = _enrich(handler, "ip", ip)
        assert card.status == "OK"
        assert card.verdict_signal == "INFO"
    assert calls == []
