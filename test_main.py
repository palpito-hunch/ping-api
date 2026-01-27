from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


class TestPingEndpoint:
    """Tests for the /ping endpoint."""

    def test_ping_returns_200(self) -> None:
        """Ping endpoint returns HTTP 200."""
        response = client.get("/ping")
        assert response.status_code == 200

    def test_ping_returns_pong_message(self) -> None:
        """Response contains 'Pong @' prefix."""
        response = client.get("/ping")
        data = response.json()
        assert "message" in data
        assert data["message"].startswith("Pong @")

    def test_ping_default_timezone_is_utc(self) -> None:
        """Without X-Timezone header, uses UTC."""
        response = client.get("/ping")
        data = response.json()
        assert "UTC" in data["message"]

    def test_ping_with_valid_timezone(self) -> None:
        """Accepts valid IANA timezone in X-Timezone header."""
        response = client.get("/ping", headers={"X-Timezone": "America/New_York"})
        assert response.status_code == 200
        data = response.json()
        assert "Pong @" in data["message"]

    def test_ping_with_invalid_timezone_returns_400(self) -> None:
        """Invalid timezone returns HTTP 400."""
        response = client.get("/ping", headers={"X-Timezone": "Invalid/Timezone"})
        assert response.status_code == 400

    def test_ping_invalid_timezone_error_message(self) -> None:
        """Error message for invalid timezone is helpful."""
        response = client.get("/ping", headers={"X-Timezone": "NotATimezone"})
        data = response.json()
        assert "Invalid timezone" in data["detail"]
        assert "NotATimezone" in data["detail"]
        assert "IANA format" in data["detail"]

    @patch("main.datetime")
    def test_ping_returns_correct_datetime_format(self, mock_datetime) -> None:
        """Response uses expected datetime format."""
        fixed_time = datetime(2024, 6, 15, 14, 30, 45, tzinfo=ZoneInfo("UTC"))
        mock_datetime.now.return_value = fixed_time

        response = client.get("/ping")
        data = response.json()

        assert "2024-06-15 14:30:45 UTC" in data["message"]

    def test_ping_respects_timezone_in_response(self) -> None:
        """Datetime in response reflects the requested timezone."""
        response_utc = client.get("/ping", headers={"X-Timezone": "UTC"})
        response_tokyo = client.get("/ping", headers={"X-Timezone": "Asia/Tokyo"})

        # Both should succeed
        assert response_utc.status_code == 200
        assert response_tokyo.status_code == 200

        # Tokyo response should contain JST timezone indicator
        tokyo_data = response_tokyo.json()
        assert "JST" in tokyo_data["message"] or "Asia/Tokyo" in tokyo_data["message"]


class TestTimezoneVariants:
    """Test various timezone formats and edge cases."""

    @pytest.mark.parametrize(
        "timezone",
        [
            "America/New_York",
            "Europe/London",
            "Asia/Tokyo",
            "Australia/Sydney",
            "Pacific/Auckland",
            "Africa/Cairo",
            "UTC",
        ],
    )
    def test_valid_timezones_accepted(self, timezone: str) -> None:
        """Common IANA timezones are accepted."""
        response = client.get("/ping", headers={"X-Timezone": timezone})
        assert response.status_code == 200

    @pytest.mark.parametrize(
        "invalid_timezone",
        [
            "GMT+5",
            "America/NotReal",
            "12345",
            "Not/A/Real/Timezone",
        ],
    )
    def test_invalid_timezones_rejected(self, invalid_timezone: str) -> None:
        """Invalid timezone formats are rejected with 400."""
        response = client.get("/ping", headers={"X-Timezone": invalid_timezone})
        assert response.status_code == 400

    def test_empty_timezone_defaults_to_utc(self) -> None:
        """Empty timezone string defaults to UTC."""
        response = client.get("/ping", headers={"X-Timezone": ""})
        assert response.status_code == 200
        assert "UTC" in response.json()["message"]
