from flask import session


def test_home(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"<h1>VanLife Server</h1>" in response.data


def test_admin(client):
    response = client.get("/admin")
    assert response.status_code == 302


def test_auth(client):
    # GET 
    response = client.get("/admin", follow_redirects=True)
    assert response.status_code == 200
    assert b'<h1 class="title">AUTHORIZE</h1>' in response.data
    # must be exactly one redirect
    assert len(response.history) == 1
    # redirects to exactly this page.
    assert response.request.path == "/authorize"

    # POST
    with client:
        client.post("/authorize", data={"username": "admin", "password": "admin"})
        assert session.get("is_authorized") == True

        # Acess admin after login
        response = client.get("/admin", follow_redirects=True)
        assert response.status_code == 200
        assert b'<h1>ADMIN PAGE</h1>' in response.data

        # Cannot access admin page after logout
        client.get("/unauthorize")
        response = client.get("/admin")
        assert response.status_code == 302

