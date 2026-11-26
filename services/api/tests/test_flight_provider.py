from urllib.parse import parse_qs, urlparse
import json

import pytest

from app.flight_provider import FlightProviderError, search_google_flights


class FakeResponse:
    def __init__(self, body: bytes):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self):
        return self.body


def test_search_builds_round_trip_request_and_returns_provider_payload(monkeypatch):
    seen = {}

    def fake_urlopen(request, timeout):
        seen["url"] = request.full_url
        seen["timeout"] = timeout
        return FakeResponse(json.dumps({"best_flights": [{"price": 450}]}).encode())

    monkeypatch.setattr("app.flight_provider.urlopen", fake_urlopen)
    result = search_google_flights(
        departure_id="sea", arrival_id="nrt", outbound_date="2027-04-01",
        return_date="2027-04-12", api_key="test-key", stops=1,
    )

    params = parse_qs(urlparse(seen["url"]).query)
    assert params["engine"] == ["google_flights"]
    assert params["departure_id"] == ["SEA"]
    assert params["arrival_id"] == ["NRT"]
    assert params["type"] == ["1"]
    assert params["return_date"] == ["2027-04-12"]
    assert params["stops"] == ["1"]
    assert seen["timeout"] == 20
    assert result["best_flights"][0]["price"] == 450


def test_search_omits_return_date_for_one_way(monkeypatch):
    def fake_urlopen(request, timeout):
        params = parse_qs(urlparse(request.full_url).query)
        assert params["type"] == ["2"]
        assert "return_date" not in params
        return FakeResponse(b'{"other_flights": []}')

    monkeypatch.setattr("app.flight_provider.urlopen", fake_urlopen)
    assert search_google_flights(
        departure_id="SEA", arrival_id="SFO", outbound_date="2027-04-01", api_key="test"
    ) == {"other_flights": []}


def test_search_requires_api_key(monkeypatch):
    monkeypatch.delenv("SERPAPI_API_KEY", raising=False)
    with pytest.raises(FlightProviderError, match="SERPAPI_API_KEY"):
        search_google_flights(
            departure_id="SEA", arrival_id="NRT", outbound_date="2027-04-01"
        )


def test_provider_error_is_not_returned_as_a_quote(monkeypatch):
    monkeypatch.setattr(
        "app.flight_provider.urlopen",
        lambda *_args, **_kwargs: FakeResponse(b'{"error":"invalid key"}'),
    )
    with pytest.raises(FlightProviderError, match="invalid key"):
        search_google_flights(
            departure_id="SEA", arrival_id="NRT", outbound_date="2027-04-01", api_key="bad"
        )
