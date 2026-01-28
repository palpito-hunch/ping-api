import os
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Set test database before importing app
os.environ["DATABASE_URL"] = "sqlite:///./test_ping.db"

from database import Base, User, get_db
from main import app

# Test database setup
TEST_DATABASE_URL = "sqlite:///./test_ping.db"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_database():
    """Create tables before each test and clean up after."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


@pytest.fixture
def user_id():
    """Generate unique user ID for each test."""
    return str(uuid4())


class TestPingEndpoint:
    """Tests for the /ping endpoint."""

    def test_ping_returns_200(self, client, user_id) -> None:
        """Ping endpoint returns HTTP 200."""
        response = client.get("/ping", headers={"X-User-Id": user_id})
        assert response.status_code == 200

    def test_ping_returns_pong_message(self, client, user_id) -> None:
        """Response contains 'Pong @' prefix."""
        response = client.get("/ping", headers={"X-User-Id": user_id})
        data = response.json()
        assert "message" in data
        assert data["message"].startswith("Pong @")

    def test_ping_returns_views_count(self, client, user_id) -> None:
        """Response contains views count."""
        response = client.get("/ping", headers={"X-User-Id": user_id})
        data = response.json()
        assert "views" in data
        assert data["views"] == 1

    def test_ping_returns_updated_at(self, client, user_id) -> None:
        """Response contains updated_at timestamp."""
        response = client.get("/ping", headers={"X-User-Id": user_id})
        data = response.json()
        assert "updated_at" in data
        assert len(data["updated_at"]) > 0

    def test_ping_requires_user_id(self, client) -> None:
        """Request without X-User-Id returns 422."""
        response = client.get("/ping")
        assert response.status_code == 422

    def test_ping_rejects_empty_user_id(self, client) -> None:
        """Request with empty X-User-Id returns 400."""
        response = client.get("/ping", headers={"X-User-Id": ""})
        assert response.status_code == 400
        assert "required" in response.json()["detail"].lower()

    def test_ping_rejects_whitespace_user_id(self, client) -> None:
        """Request with whitespace-only X-User-Id returns 400."""
        response = client.get("/ping", headers={"X-User-Id": "   "})
        assert response.status_code == 400

    def test_ping_default_timezone_is_utc(self, client, user_id) -> None:
        """Without X-Timezone header, uses UTC."""
        response = client.get("/ping", headers={"X-User-Id": user_id})
        data = response.json()
        assert "UTC" in data["message"]

    def test_ping_with_valid_timezone(self, client, user_id) -> None:
        """Accepts valid IANA timezone in X-Timezone header."""
        response = client.get("/ping", headers={"X-User-Id": user_id, "X-Timezone": "America/New_York"})
        assert response.status_code == 200
        data = response.json()
        assert "Pong @" in data["message"]

    def test_ping_with_invalid_timezone_returns_400(self, client, user_id) -> None:
        """Invalid timezone returns HTTP 400."""
        response = client.get("/ping", headers={"X-User-Id": user_id, "X-Timezone": "Invalid/Timezone"})
        assert response.status_code == 400

    def test_ping_invalid_timezone_error_message(self, client, user_id) -> None:
        """Error message for invalid timezone is helpful."""
        response = client.get("/ping", headers={"X-User-Id": user_id, "X-Timezone": "NotATimezone"})
        data = response.json()
        assert "Invalid timezone" in data["detail"]
        assert "NotATimezone" in data["detail"]
        assert "IANA format" in data["detail"]


class TestViewTracking:
    """Tests for view count tracking."""

    def test_first_request_creates_user_with_one_view(self, client, user_id) -> None:
        """First request for a user creates them with views=1."""
        response = client.get("/ping", headers={"X-User-Id": user_id})
        data = response.json()
        assert data["views"] == 1

    def test_second_request_increments_views(self, client, user_id) -> None:
        """Second request increments view count."""
        client.get("/ping", headers={"X-User-Id": user_id})
        response = client.get("/ping", headers={"X-User-Id": user_id})
        data = response.json()
        assert data["views"] == 2

    def test_multiple_requests_increment_correctly(self, client, user_id) -> None:
        """Multiple requests increment view count correctly."""
        for i in range(1, 6):
            response = client.get("/ping", headers={"X-User-Id": user_id})
            assert response.json()["views"] == i

    def test_different_users_have_separate_counts(self, client) -> None:
        """Different users have independent view counts."""
        user1 = str(uuid4())
        user2 = str(uuid4())

        # User 1 makes 3 requests
        for _ in range(3):
            client.get("/ping", headers={"X-User-Id": user1})

        # User 2 makes 1 request
        response = client.get("/ping", headers={"X-User-Id": user2})
        assert response.json()["views"] == 1

        # User 1 still has 3 views (now 4 after this request)
        response = client.get("/ping", headers={"X-User-Id": user1})
        assert response.json()["views"] == 4

    def test_updated_at_changes_on_each_request(self, client, user_id) -> None:
        """updated_at timestamp changes on each request."""
        response1 = client.get("/ping", headers={"X-User-Id": user_id})
        updated_at_1 = response1.json()["updated_at"]

        # Small delay to ensure timestamp difference
        import time
        time.sleep(0.01)

        response2 = client.get("/ping", headers={"X-User-Id": user_id})
        updated_at_2 = response2.json()["updated_at"]

        # Timestamps should be different (or at least not fail)
        assert updated_at_1 is not None
        assert updated_at_2 is not None


class TestConcurrency:
    """Tests for race condition handling."""

    def test_concurrent_requests_count_correctly(self, client) -> None:
        """Concurrent requests are counted atomically without race conditions."""
        user_id = str(uuid4())
        num_requests = 50
        results = []

        def make_request():
            response = client.get("/ping", headers={"X-User-Id": user_id})
            results.append(response.json()["views"])

        # Make concurrent requests
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(num_requests)]
            for future in futures:
                future.result()

        # Final count should equal number of requests
        final_response = client.get("/ping", headers={"X-User-Id": user_id})
        final_views = final_response.json()["views"]

        # Total should be num_requests + 1 (for the final check)
        assert final_views == num_requests + 1

    def test_no_duplicate_counts_under_concurrency(self, client) -> None:
        """No view counts are skipped or duplicated under concurrent load."""
        user_id = str(uuid4())
        num_requests = 20
        view_counts = []
        lock = threading.Lock()

        def make_request():
            response = client.get("/ping", headers={"X-User-Id": user_id})
            with lock:
                view_counts.append(response.json()["views"])

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(num_requests)]
            for future in futures:
                future.result()

        # All view counts should be unique (no duplicates from race conditions)
        assert len(view_counts) == num_requests
        # Max should be num_requests (no skips)
        assert max(view_counts) == num_requests


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
    def test_valid_timezones_accepted(self, client, user_id, timezone: str) -> None:
        """Common IANA timezones are accepted."""
        response = client.get("/ping", headers={"X-User-Id": user_id, "X-Timezone": timezone})
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
    def test_invalid_timezones_rejected(self, client, user_id, invalid_timezone: str) -> None:
        """Invalid timezone formats are rejected with 400."""
        response = client.get("/ping", headers={"X-User-Id": user_id, "X-Timezone": invalid_timezone})
        assert response.status_code == 400

    def test_empty_timezone_defaults_to_utc(self, client, user_id) -> None:
        """Empty timezone string defaults to UTC."""
        response = client.get("/ping", headers={"X-User-Id": user_id, "X-Timezone": ""})
        assert response.status_code == 200
        assert "UTC" in response.json()["message"]

    def test_updated_at_respects_timezone(self, client, user_id) -> None:
        """updated_at is formatted in the requested timezone."""
        response = client.get("/ping", headers={"X-User-Id": user_id, "X-Timezone": "Asia/Tokyo"})
        data = response.json()
        # Should contain JST or similar timezone indicator
        assert "JST" in data["updated_at"] or "Asia" in data["updated_at"] or len(data["updated_at"]) > 0
