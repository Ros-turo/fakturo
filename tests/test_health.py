import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture(scope="function")
def client():
    return TestClient(app=app)


def test_info(client):

    response = client.get("/")
    json_result = response.json()
    version = json_result["msg"]["Version"]
    status = json_result["status"]

    assert response.status_code == 200
    # assert version == "0.3"
    assert json_result["msg"]["Version"] == "0.3"
    assert status == "ok"


