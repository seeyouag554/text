from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def create_user(name="Tester", weight_kg=70, sleep_time="23:00:00"):
    response = client.post(
        "/users",
        json={"name": name, "weight_kg": weight_kg, "sleep_time": sleep_time},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_create_intake_record_within_limits(tmp_path):
    user = create_user()
    consumed_at = datetime.utcnow().replace(microsecond=0).isoformat()
    payload = {
        "user_id": user["id"],
        "caffeine_mg": 120,
        "consumed_at": consumed_at,
    }
    response = client.post("/intake-records", json=payload)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"]["single_intake_ok"] is True
    assert body["status"]["daily_total_ok"] is True
    assert body["status"]["sleep_window_ok"] is True


def test_create_intake_record_exceeds_sleep_window():
    user = create_user(sleep_time="18:00:00")
    consumed_at = (datetime.utcnow().replace(hour=17, minute=0, second=0, microsecond=0)).isoformat()
    payload = {
        "user_id": user["id"],
        "caffeine_mg": 50,
        "consumed_at": consumed_at,
    }
    response = client.post("/intake-records", json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["status"]["sleep_window_ok"] is False


def test_daily_summary_flags_over_limit():
    user = create_user(weight_kg=60)
    base_time = datetime.utcnow().replace(hour=8, minute=0, second=0, microsecond=0)
    for _ in range(3):
        payload = {
            "user_id": user["id"],
            "caffeine_mg": 150,
            "consumed_at": base_time.isoformat(),
        }
        response = client.post("/intake-records", json=payload)
        assert response.status_code == 201
        base_time += timedelta(hours=1)
    summary = client.get(
        "/summaries/daily",
        params={"user_id": user["id"], "date": base_time.isoformat()},
    )
    assert summary.status_code == 200
    body = summary.json()
    assert body["status"]["daily_total_ok"] is False
    assert body["total_caffeine_mg"] > body["status"]["daily_total_limit_mg"]
