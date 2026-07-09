
def test_info(client):

    response = client.get("/")
    json_result = response.json()
    version = json_result["msg"]["Version"]
    status = json_result["status"]

    assert response.status_code == 200
    assert version == "0.2"
    assert status == "ok"


