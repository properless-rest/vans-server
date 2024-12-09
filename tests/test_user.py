import os
#
from datetime import datetime, timedelta, timezone
from io import BytesIO
from uuid import uuid4

from freezegun import freeze_time

from config import app, db
from models import User
from main import __generate_reset_token


def test_register(client):
    # GET instead of POST
    response = client.get("/register")
    assert response.status_code == 404
    # Empty JSON
    response = client.post("/register", json={})
    assert response.status_code == 400
    assert response.json.get("message") == "Required data missing"
    # long json fields
    response = client.post("/register", json=long_name)
    assert response.status_code == 400
    assert response.json.get("message") == "Name is too long"
    #
    response = client.post("/register", json=long_surname)
    assert response.status_code == 400
    assert response.json.get("message") == "Surname is too long"
    #
    response = client.post("/register", json=long_email)
    assert response.status_code == 400
    assert response.json.get("message") == "Email is too long"
    # Bad email #1
    response = client.post("/register", json=bad_email_1)
    assert response.status_code == 400
    assert response.json.get("message") == "Invalid email"
    # Bad email #2
    response = client.post("/register", json=bad_email_2)
    assert response.status_code == 400
    assert response.json.get("message") == "Invalid email"
    # Email already taken
    response = client.post("/register", json=user_exists)
    assert response.status_code == 400
    assert response.json.get("message") == "This email is taken"
    # Short PW
    response = client.post("/register", json=short_password)
    assert response.status_code == 400
    assert response.json.get("message") == "Password must be at least 8\u00A0characters"
    # Success
    response = client.post("/register", json=admissible_data)
    assert response.status_code == 201
    assert response.json.get("message") == "User registered"


def test_login(client):
    # GET instead of POST
    response = client.get("/login")
    assert response.status_code == 404
    # Empty JSON
    response = client.post("/login", json={})
    assert response.status_code == 400
    assert response.json.get("message") == "Required data missing"
    # No such user and wrong PW
    response = client.post("/login", json=no_user)
    assert response.status_code == 401
    assert response.json.get("message") == "Wrong email or password"
    assert response.json.get("JWToken", None) is None
    assert response.json.get("RfToken", None) is None
    # Success
    example = User.query.get(1)
    print(f"{example.email}: {example.password}")
    response = client.post("/login", json={"email": "name.surname@example.com", "password": "12345678"})
    assert response.status_code == 200
    assert response.json.get("statusText") == "Login successful"
    assert response.json.get("JWToken", None) is not None
    assert response.json.get("RFToken", None) is not None


def test_get_user(client):
    # No Authorization Header
    response = client.get("/getUser", json={})
    assert response.json.get("msg")== "Missing Authorization Header"
    assert response.status_code == 401
    # Wrong JWT
    response = client.get("/getUser", headers={"Authorization": f"Bearer {false_JWT}"}, json={})
    assert response.status_code == 422
    assert response.json.get("logged_user", None) is None
    # Success
    response = client.post("/login", json={"email": "name.surname@example.com", "password": "12345678"})
    assert response.status_code == 200
    assert response.json.get("statusText") == "Login successful"
    JWToken = response.json.get("JWToken")
    # #
    response = client.get("/getUser", headers={"Authorization": f"Bearer {JWToken}"}, json={})
    assert response.status_code == 200
    assert response.json.get("statusText") == "Read succesful"
    assert response.json.get("logged_user", None) is not None
    logged_user = response.json.get("logged_user")
    assert logged_user.get("email") == "name.surname@example.com"
    # Token expires with time
    with freeze_time(datetime.now(timezone.utc) + app.config.get("JWT_ACCESS_TOKEN_EXPIRES")):
        response = client.get("/getUser", headers={"Authorization": f"Bearer {JWToken}"}, json={})
        assert response.status_code == 401
        assert response.json.get("msg") == "Token has expired"


def test_send_reset_email(client):
    # GET instead of POST
    response = client.get("/sendReset")
    assert response.status_code == 404
    # Empty JSON
    response = client.post("/sendReset", json={})
    assert response.status_code == 400
    assert response.json.get("message") == "Required data missing"
    # Non-existing user
    response = client.post("/sendReset", json=no_user)
    assert response.status_code == 400
    assert response.json.get("message") == "Email is not registred"
    # Success
    response = client.post("/sendReset", json={"email": "name.surname@example.com"})
    assert response.status_code == 200
    assert response.json.get("message") == "Email sent"


def test_validate_reset_token(client):
    # GET instead of POST
    response = client.get("/validateToken")
    assert response.status_code == 404
    # No Token
    response = client.post("/validateToken", json={})
    assert response.status_code == 200
    assert response.json.get("tokenValid") is False
    # Token is invalid
    response = client.post("/validateToken", json={"token": "012345"})
    assert response.status_code == 200
    assert response.json.get("tokenValid") is False
    # Token is valid (success)
    reset_token=(__generate_reset_token("name.surname@example.com"))
    response = client.post("/validateToken", json={"token": reset_token})
    assert response.status_code == 200
    assert response.json.get("tokenValid") is True
    # Token expires with time
    reset_token=(__generate_reset_token("name.surname@example.com"))
    with freeze_time(datetime.now(timezone.utc) + timedelta(seconds=app.config.get("RESET_PW_TOKEN_EXP") + 1)):
        response = client.post("/validateToken", json={"token": reset_token})
        assert response.status_code == 200
        assert response.json.get("tokenValid") is False


def test_reset_pw(client):
    # GET instead of POST
    response = client.get("/resetPassword")
    assert response.status_code == 404
    # No Token
    response = client.post("/resetPassword", json={})
    assert response.status_code == 401
    assert response.json.get("message") == "Cannot update password"
    # Token is invalid
    response = client.post("/resetPassword", json={"token": "012345"})
    assert response.status_code == 401
    assert response.json.get("message") == "Cannot update password"
    # No password
    reset_token=(__generate_reset_token("name.surname@example.com"))
    response = client.post("/resetPassword", json={"token": reset_token})
    assert response.status_code == 400
    assert response.json.get("message") == "Enter the new password"
    # Password is too short
    response = client.post("/resetPassword", json={"token": reset_token, "newPassword": "12345"})
    assert response.status_code == 400
    assert response.json.get("message") == "Password must be at least 8\u00A0characters"
    # Success
    reset_token=(__generate_reset_token("name.surname@example.com"))
    response = client.post("/resetPassword", json={"token": reset_token, "newPassword": "123123123"})
    assert response.status_code == 200
    assert response.json.get("message") == "User password updated"
    # Attempt to login with new credentials
    response = client.post("/login", json={"email": "name.surname@example.com", "password": "123123123"})
    assert response.status_code == 200
    assert response.json.get("statusText") == "Login successful"
    assert response.json.get("JWToken", None) is not None
    assert response.json.get("RFToken", None) is not None
    # # Setting the password back to the old one
    client.post("/resetPassword", json={"token": reset_token, "newPassword": "12345678"})
    # Logging In must be impossible since the old password has been restored
    response = client.post("/login", json={"email": "name.surname@example.com", "password": "123123123"})
    assert response.status_code == 401
    assert response.json.get("message") == "Wrong email or password"
    # Token expires with time
    reset_token=(__generate_reset_token("name.surname@example.com"))
    with freeze_time(datetime.now(timezone.utc) + timedelta(seconds=app.config.get("RESET_PW_TOKEN_EXP") + 1)):
        response = client.post("/resetPassword", json={"token": reset_token})
        assert response.status_code == 401
        assert response.json.get("message") == "Cannot update password"


def test_refresh_JWT(client):
    # GET instead of POST
    response = client.get("/refreshToken")
    assert response.status_code == 404
    # pre-requisites
    response = client.post("/login", json={"email": "name.surname@example.com", "password": "12345678"})
    assert response.status_code == 200
    assert response.json.get("statusText") == "Login successful"
    JWToken = response.json.get("JWToken")
    RFToken = response.json.get("RFToken")
    # No Authorization Header
    response = client.post("/refreshToken", json={})
    assert response.json.get("msg")== "Missing Authorization Header"
    assert response.status_code == 401
    # Wrong RFToken
    response = client.post("/refreshToken", headers={"Authorization": f"Bearer {false_JWT}"}, json={})
    assert response.status_code == 422
    assert response.json.get("JWToken", None) is None
    # JWToken sent instead of RFToken
    response = client.post("/refreshToken", headers={"Authorization": f"Bearer {JWToken}"}, json={})
    assert response.status_code == 422
    assert response.json.get("msg") == "Only refresh tokens are allowed"
    assert response.json.get("JWToken", None) is None
    # # Success
    response = client.post("/refreshToken", headers={"Authorization": f"Bearer {RFToken}"}, json={})
    assert response.status_code == 200
    assert response.json.get("JWToken", None) is not None
    new_JWToken = response.json.get("JWToken")
    # # attempting to get user with the new JWT
    response = client.get("/getUser", headers={"Authorization": f"Bearer {new_JWToken}"}, json={})
    assert response.status_code == 200
    assert response.json.get("statusText") == "Read succesful"
    assert response.json.get("logged_user", None) is not None
    logged_user = response.json.get("logged_user")
    assert logged_user.get("email") == "name.surname@example.com"


def test_upload_avatar(client):
    # pre-requisites
    user = User.query.filter_by(email="name.surname@example.com").first()
    response = client.post("/login", json={"email": user.email, "password": "12345678"})
    JWToken = response.json.get("JWToken")
    # GET instead of POST
    response = client.get("/uploadAvatar")
    assert response.status_code == 404
    # no authorization headers
    response = client.post("/uploadAvatar", content_type="multipart/form-data")
    assert response.status_code == 401
    assert response.json.get("msg")== "Missing Authorization Header"
    # extraneous JWT
    mock_file = (BytesIO(b"mocked-image"), "test.png")  # will be closed after each POST
    response = client.post(
        "/uploadAvatar",  
        headers={"Authorization": f"Bearer {false_JWT}"},
        data={"avatar": mock_file}, 
        content_type="multipart/form-data")
    assert response.status_code == 422
    assert response.json.get("msg")== "Signature verification failed"
    # no file attached
    mock_empty_file = (BytesIO(b"mocked-image"), "")  # will be closed after each POST
    response = client.post(
        "/uploadAvatar",  
        headers={"Authorization": f"Bearer {JWToken}"},
        data={"avatar": mock_empty_file}, 
        content_type="multipart/form-data"
    )
    assert response.status_code == 400
    assert response.json.get("message") == "No file detected"
    # inadmissible file name
    mock_nameless_file = (BytesIO(b"mocked-image"), ".jpeg")  # will be closed after each POST
    response = client.post(
        "/uploadAvatar",  
        headers={"Authorization": f"Bearer {JWToken}"},
        data={"avatar": mock_nameless_file}, 
        content_type="multipart/form-data"
    )
    assert response.status_code == 400
    assert response.json.get("message") == "Inadmissible file name"
    # inadmissible file extension
    mock_mp4_file = (BytesIO(b"mocked-image"), "test.mp4")  # will be closed after each POST
    response = client.post(
        "/uploadAvatar",  
        headers={"Authorization": f"Bearer {JWToken}"},
        data={"avatar": mock_mp4_file}, 
        content_type="multipart/form-data"
    )
    assert response.status_code == 400
    assert response.json.get("message") == "Extension: .png, .jp(e)g"
    # Success
    mock_file = (BytesIO(b"mocked-image"), "test.png")  # will be closed after each POST
    response = client.post(
        "/uploadAvatar",
        headers={"Authorization": f"Bearer {JWToken}"},
        data={"avatar": mock_file},
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    assert response.json.get("message") == "Profile picture updated"

    # Verify file storage
    user_folder = os.path.join(app.config["STATIC_FOLDER"], "user", str(user.uuid))
    saved_files = os.listdir(user_folder)
    assert len(saved_files) == 1  # exactly one file is saved
    assert saved_files[0].split(".")[-1] == "png"

    # ! Clean-up is in the `contest.py`'s test_app !


def test_update_user(client):
    # pre-requisites
    user = User.query.filter_by(email="name.surname@example.com").first()
    response = client.post("/login", json={"email": user.email, "password": "12345678"})
    JWToken = response.json.get("JWToken")
    # GET instead of PATCH
    response = client.get("/updateUser")  # must PATCH
    assert response.status_code == 404
    # no authorization headers
    response = client.patch("/updateUser", json={})
    assert response.status_code == 401
    assert response.json.get("msg")== "Missing Authorization Header"
    # extraneous JWT
    response = client.patch("/updateUser", headers={"Authorization": f"Bearer {false_JWT}"}, json={})
    assert response.status_code == 422
    assert response.json.get("msg")== "Signature verification failed"
    # empty JSON
    response = client.patch(
        "/updateUser", 
        headers={"Authorization": f"Bearer {JWToken}"}, 
        json={}
    )
    assert response.status_code == 400
    assert response.json.get("message") == "Required data missing"
    # long json fields
    response = client.patch(
        "/updateUser", 
        headers={"Authorization": f"Bearer {JWToken}"}, 
        json={"name": "Mike" * 100, "surname": "Wazowski"}
    )
    assert response.status_code == 400
    assert response.json.get("message") == "Name is too long"
    #
    response = client.patch(
        "/updateUser", 
        headers={"Authorization": f"Bearer {JWToken}"}, 
        json={"name": "Mike", "surname": "Wazowski" * 100}
    )
    assert response.status_code == 400
    assert response.json.get("message") == "Surname is too long"
    # same data sent (no modifications)
    response = client.patch(
        "/updateUser", 
        headers={"Authorization": f"Bearer {JWToken}"}, 
        json={"name": "Name", "surname": "Surname"}
    )
    assert response.status_code == 400
    assert response.json.get("message") == "No modifications detected"
    # Success
    response = client.patch(
        "/updateUser", 
        headers={"Authorization": f"Bearer {JWToken}"}, 
        json={"name": "Mike", "surname": "Wazowski"}
    )
    assert response.status_code == 200
    assert response.json.get("message") == "User data updated"
    assert user.name == "Mike"
    assert user.surname == "Wazowski"
    # re-write to the previous name
    user.name = "name"
    user.surname = "surname"
    db.session.commit()


def test_update_password(client):
    # pre-requisites
    user = User.query.filter_by(email="name.surname@example.com").first()
    response = client.post("/login", json={"email": user.email, "password": "12345678"})
    JWToken = response.json.get("JWToken")
    # GET instead of PATCH
    response = client.get("/updatePassword")  # must PATCH
    assert response.status_code == 404
    # no authorization headers
    response = client.patch("/updatePassword", json={})
    assert response.status_code == 401
    assert response.json.get("msg")== "Missing Authorization Header"
    # extraneous JWT
    response = client.patch("/updatePassword", headers={"Authorization": f"Bearer {false_JWT}"}, json={})
    assert response.status_code == 422
    assert response.json.get("msg")== "Signature verification failed"
    # wrong current PW
    response = client.patch(
        "/updatePassword", 
        headers={"Authorization": f"Bearer {JWToken}"}, 
        json={"currentPassword": "123123123"}
    )
    assert response.status_code == 401
    assert response.json.get("message") == "Curent password does not match"
    # no new PW provided
    response = client.patch(
        "/updatePassword", 
        headers={"Authorization": f"Bearer {JWToken}"}, 
        json={"currentPassword": "12345678"}
    )
    assert response.status_code == 400
    assert response.json.get("message") == "Enter the new password"
    # password is too short
    response = client.patch(
        "/updatePassword", 
        headers={"Authorization": f"Bearer {JWToken}"}, 
        json={"currentPassword": "12345678", "newPassword": "123123"}
    )
    assert response.status_code == 400
    assert response.json.get("message") == "Password must be at least 8\u00A0characters"
    # Success
    response = client.patch(
        "/updatePassword", 
        headers={"Authorization": f"Bearer {JWToken}"}, 
        json={"currentPassword": "12345678", "newPassword": "aVeryG00dNewPW"}
    )
    assert response.status_code == 200
    assert response.json.get("message") == "User password updated"
    # recover the old PW
    user.password = "12345678"
    db.session.commit()

long_name = {
    "name": "B" * (User.name_len + 1), 
    "surname": "Dillon", 
    "email": "bobby.di!gmail.com",
    "password": "bobDillonPW"
}

long_surname = {
    "name": "Bob", 
    "surname": "D" * (User.surname_len + 1), 
    "email": "bobby.di!gmail.com",
    "password": "bobDillonPW"
}

long_email = {
    "name": "Bob", 
    "surname": "Dillon", 
    "email": f"{'bd' * (User.email_len + 1)}@gmail.com",
    "password": "bobDillonPW"
}

bad_email_1 = {
    "name": "Bob", 
    "surname": "Dillon", 
    "email": "bobby.di!gmail.com",
    "password": "bobDillonPW"
}

bad_email_2 = {
    "name": "Bob", 
    "surname": "Dillon", 
    "email": "bobby.di@gmail!com",
    "password": "bobDillonPW"
}

user_exists = {
    "name": "Name", 
    "surname": "Surname", 
    "email": "name.surname@example.com",
    "password": "12345678"
}

short_password = {
    "name": "Bob", 
    "surname": "Dillon", 
    "email": "bobby.di@gmail.com",
    "password": "0000"
}

admissible_data = {
    "name": "Bob", 
    "surname": "Dillon", 
    "email": "bobby.di@gmail.com",
    "password": "bobbyDiPW"
}

no_user = {
    "email": "dobby.bi@gmail.com",
    "password": "dobbyBiPW"
}


false_JWT = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
