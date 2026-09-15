"""Yahoo Fantasy parsing and OAuth configuration guards."""
from app.services.yahoo_service import YahooService, _resource_records


def test_yahoo_requires_both_oauth_credentials(monkeypatch):
    monkeypatch.setattr("app.services.yahoo_service.settings.yahoo_client_id", "client")
    monkeypatch.setattr("app.services.yahoo_service.settings.yahoo_client_secret", "")
    assert YahooService().configured() is False


def test_yahoo_resource_records_unwrap_count_keyed_data():
    # Yahoo nests resource fields in arrays mixed with numeric count keys. The
    # parser must find actual resources without depending on those key names.
    payload = {
        "fantasy_content": {
            "users": {
                "0": {
                    "user": [
                        {"leagues": {"0": {"league": [
                            {"league_key": "nfl.l.42"}, {"name": "The League"},
                            {"season": "2026"}, {"num_teams": "12"},
                        ]}}}
                    ]
                }
            }
        }
    }
    records = _resource_records(payload, "league")
    assert records == [{"league_key": "nfl.l.42", "name": "The League", "season": "2026", "num_teams": "12"}]
