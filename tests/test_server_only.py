

def test_request_example(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"<h1>VanLife Server</h1>" in response.data
