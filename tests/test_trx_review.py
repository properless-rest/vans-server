
from datetime import datetime, timedelta

from config import SERVER_TIMEZONE
from models import Van, Review


def test_make_trx(client):
    # pre-requisites
    van_uuid = Van.query.get(1).uuid
    # GET instead of POST
    response = client.get("/makeTransaction")
    assert response.status_code == 404
    # Inadmissible van UUID format
    response = client.post("/makeTransaction", json={"vanUUID": 1_234_567_890})
    assert response.status_code == 400
    assert response.json.get("message") == "Invalid UUID"
    # Bad van UUID
    response = client.post("/makeTransaction", json={"vanUUID": wrong_van_UUID})
    assert response.status_code == 404
    assert response.json.get("message") == "The Van does not exist"
    # empty JSON
    response = client.post("/makeTransaction", json={"vanUUID": van_uuid})
    assert response.status_code == 400
    assert response.json.get("message") == "Required data missing"
    # JSON data too long
    response = client.post("/makeTransaction", 
                           json={
                               "vanUUID": van_uuid, 
                               "lesseeName": "Jack" * 100, 
                               "lesseeSurname": "Daniels", 
                               "lesseeEmail": "iamnotalchohol!example.com", 
                               "rentCommencement": (datetime.now(SERVER_TIMEZONE) + timedelta(days=1)).date().isoformat(),
                               "rentExpiration": (datetime.now(SERVER_TIMEZONE) + timedelta(days=4)).date().isoformat(),
                               "price": 150
                               }
                           )
    assert response.status_code == 400
    assert response.json.get("message") == "Name is too long"
    #
    response = client.post("/makeTransaction", 
                           json={
                               "vanUUID": van_uuid, 
                               "lesseeName": "Jack", 
                               "lesseeSurname": "Daniels" * 100, 
                               "lesseeEmail": "iamnotalchohol!example.com", 
                               "rentCommencement": (datetime.now(SERVER_TIMEZONE) + timedelta(days=1)).date().isoformat(),
                               "rentExpiration": (datetime.now(SERVER_TIMEZONE) + timedelta(days=4)).date().isoformat(),
                               "price": 150
                               }
                           )
    assert response.status_code == 400
    assert response.json.get("message") == "Surname is too long"
    #
    response = client.post("/makeTransaction", 
                           json={
                               "vanUUID": van_uuid, 
                               "lesseeName": "Jack", 
                               "lesseeSurname": "Daniels", 
                               "lesseeEmail": f"{'alcho' * 100}@example.com", 
                               "rentCommencement": (datetime.now(SERVER_TIMEZONE) + timedelta(days=1)).date().isoformat(),
                               "rentExpiration": (datetime.now(SERVER_TIMEZONE) + timedelta(days=4)).date().isoformat(),
                               "price": 150
                               }
                           )
    assert response.status_code == 400
    assert response.json.get("message") == "Email is too long"
    # invalid email
    response = client.post("/makeTransaction", 
                           json={
                               "vanUUID": van_uuid, 
                               "lesseeName": "Jack", 
                               "lesseeSurname": "Daniels", 
                               "lesseeEmail": "iamnotalchohol!example.com", 
                               "rentCommencement": (datetime.now(SERVER_TIMEZONE) + timedelta(days=1)).date().isoformat(),
                               "rentExpiration": (datetime.now(SERVER_TIMEZONE) + timedelta(days=4)).date().isoformat(),
                               "price": 150
                               }
                           )
    assert response.status_code == 400
    assert response.json.get("message") == "Invalid email"
    # invalid dates
    response = client.post("/makeTransaction", 
                           json={
                               "vanUUID": van_uuid, 
                               "lesseeName": "Jack", 
                               "lesseeSurname": "Daniels", 
                               "lesseeEmail": "iamnotalchohol@example.com", 
                               "rentCommencement": "2021-77-33",
                               "rentExpiration": (datetime.now(SERVER_TIMEZONE) + timedelta(days=3)).date().isoformat(),
                               "price": 150
                               }
                           )
    assert response.status_code == 400
    assert response.json.get("message") == "Invalid date format"
    # -
    response = client.post("/makeTransaction", 
                            json={
                                "vanUUID": van_uuid, 
                                "lesseeName": "Jack", 
                                "lesseeSurname": "Daniels", 
                                "lesseeEmail": "iamnotalchohol@example.com", 
                                "rentCommencement": (datetime.now(SERVER_TIMEZONE) + timedelta(days=1)).date().isoformat(),
                                "rentExpiration": [2022, 11, 29],
                               "price": 150
                                }
                            )
    assert response.status_code == 400
    assert response.json.get("message") == "Invalid date format"
    # the commencement date is before the day of TOMORROW
    response = client.post("/makeTransaction", 
                           json={
                               "vanUUID": van_uuid, 
                               "lesseeName": "Jack", 
                               "lesseeSurname": "Daniels", 
                               "lesseeEmail": "iamnotalchohol@example.com", 
                               "rentCommencement": datetime.now(SERVER_TIMEZONE).date().isoformat(),
                               "rentExpiration": (datetime.now(SERVER_TIMEZONE) + timedelta(days=3)).date().isoformat(),
                               "price": 150
                               }
                           )
    assert response.status_code == 400
    assert response.json.get("message") == "Inadmissible commencement date"
    # the commencement date comes after the expiration date
    response = client.post("/makeTransaction", 
                           json={
                               "vanUUID": van_uuid, 
                               "lesseeName": "Jack", 
                               "lesseeSurname": "Daniels", 
                               "lesseeEmail": "iamnotalchohol@example.com", 
                               "rentCommencement": (datetime.now(SERVER_TIMEZONE) + timedelta(days=3)).date().isoformat(),
                               "rentExpiration": (datetime.now(SERVER_TIMEZONE) + timedelta(days=1)).date().isoformat(),
                               "price": 150
                               }
                           )
    assert response.status_code == 400
    assert response.json.get("message") == "Inadmissible dates"
    # invalid price
    response = client.post("/makeTransaction", 
                           json={
                               "vanUUID": van_uuid, 
                               "lesseeName": "Jack", 
                               "lesseeSurname": "Daniels", 
                               "lesseeEmail": "iamnotalchohol@example.com", 
                               "rentCommencement": (datetime.now(SERVER_TIMEZONE) + timedelta(days=1)).date().isoformat(),
                               "rentExpiration": (datetime.now(SERVER_TIMEZONE) + timedelta(days=4)).date().isoformat(),
                               "price": 'abc'
                               }
                           )
    assert response.status_code == 400
    assert response.json.get("message") == "Invalid price"
    # price less than van's price per day
    response = client.post("/makeTransaction", 
                           json={
                               "vanUUID": van_uuid, 
                               "lesseeName": "Jack", 
                               "lesseeSurname": "Daniels", 
                               "lesseeEmail": "iamnotalchohol@example.com", 
                               "rentCommencement": (datetime.now(SERVER_TIMEZONE) + timedelta(days=1)).date().isoformat(),
                               "rentExpiration": (datetime.now(SERVER_TIMEZONE) + timedelta(days=4)).date().isoformat(),
                               "price": 33
                               }
                           )
    assert response.status_code == 400
    assert response.json.get("message") == "Invalid price"
    # price is a non-positive number
    response = client.post("/makeTransaction", 
                           json={
                               "vanUUID": van_uuid, 
                               "lesseeName": "Jack", 
                               "lesseeSurname": "Daniels", 
                               "lesseeEmail": "iamnotalchohol@example.com", 
                               "rentCommencement": (datetime.now(SERVER_TIMEZONE) + timedelta(days=1)).date().isoformat(),
                               "rentExpiration": (datetime.now(SERVER_TIMEZONE) + timedelta(days=4)).date().isoformat(),
                               "price": 0
                               }
                           )
    assert response.status_code == 400
    assert response.json.get("message") == "Invalid price"
    # price is larger than SQLite's highest admissible number
    response = client.post("/makeTransaction", 
                           json={
                               "vanUUID": van_uuid, 
                               "lesseeName": "Jack", 
                               "lesseeSurname": "Daniels", 
                               "lesseeEmail": "iamnotalchohol@example.com", 
                               "rentCommencement": (datetime.now(SERVER_TIMEZONE) + timedelta(days=1)).date().isoformat(),
                               "rentExpiration": (datetime.now(SERVER_TIMEZONE) + timedelta(days=4)).date().isoformat(),
                               "price": 2_100_000
                               }
                           )
    assert response.status_code == 400
    assert response.json.get("message") == "Price too large"
    # price is miscalculated
    response = client.post("/makeTransaction", 
                           json={
                               "vanUUID": van_uuid, 
                               "lesseeName": "Jack", 
                               "lesseeSurname": "Daniels", 
                               "lesseeEmail": "iamnotalchohol@example.com", 
                               "rentCommencement": (datetime.now(SERVER_TIMEZONE) + timedelta(days=1)).date().isoformat(),
                               "rentExpiration": (datetime.now(SERVER_TIMEZONE) + timedelta(days=4)).date().isoformat(),
                               "price": 300
                               }
                           )
    assert response.status_code == 400
    assert response.json.get("message") == "Price miscalculated"
    # success
    response = client.post("/makeTransaction", 
                           json={
                               "vanUUID": van_uuid, 
                               "lesseeName": "Jack", 
                               "lesseeSurname": "Daniels", 
                               "lesseeEmail": "iamnotalchohol@example.com", 
                               "rentCommencement": (datetime.now(SERVER_TIMEZONE) + timedelta(days=1)).date().isoformat(),
                               "rentExpiration": (datetime.now(SERVER_TIMEZONE) + timedelta(days=4)).date().isoformat(),
                               "price": 150
                               }
                           )
    assert response.status_code == 201
    assert response.json.get("message") == "Transaction created"


def test_make_review(client):
    # pre-requisites
    van = Van.query.get(1)
    van_uuid = van.uuid
    # GET instead of POST
    response = client.get("/makeReview")
    assert response.status_code == 404
    # Inadmissible van UUID format
    response = client.post("/makeReview", json={"vanUUID": 1_234_567_890})
    assert response.status_code == 400
    assert response.json.get("message") == "Invalid UUID"
    # Bad van UUID
    response = client.post("/makeReview", json={"vanUUID": wrong_van_UUID})
    assert response.status_code == 404
    assert response.json.get("message") == "The Van does not exist"
    # empty JSON
    response = client.post("/makeReview", json={"vanUUID": van_uuid})
    assert response.status_code == 400
    assert response.json.get("message") == "Required data missing"
    # JSON data too long
    response = client.post(
        "/makeReview", 
        json={
            "vanUUID": van_uuid, 
            "author": "Jack Daniels" * 100, 
            "review": "I am no alchohol. The van was good.",
            "rating": "sbv"
            }
        )
    assert response.status_code == 400
    assert response.json.get("message") == "Author is too long"
    #
    response = client.post(
        "/makeReview", 
        json={
            "vanUUID": van_uuid, 
            "author": "Jack Daniels", 
            "review": "I am no alchohol. The van was good." * 1000,
            "rating": "sbv"
            }
        )
    assert response.status_code == 400
    assert response.json.get("message") == "Review is too long"
    # invalid rating
    response = client.post(
        "/makeReview", 
        json={
            "vanUUID": van_uuid, 
            "author": "Jack Daniels", 
            "review": "I am no alchohol. The van was good.",
            "rating": "sbv"
            }
        )
    assert response.status_code == 400
    assert response.json.get("message") == "Invalid rating format"
    # rating out of range 
    response = client.post(
        "/makeReview", 
        json={
            "vanUUID": van_uuid, 
            "author": "Jack Daniels", 
            "review": "I am no alchohol. The van was good.",
            "rating": 7
            }
        )
    assert response.status_code == 400
    assert response.json.get("message") == "Rating must be 1 to 5"
    # Success
    response = client.post(
        "/makeReview", 
        json={
            "vanUUID": van_uuid, 
            "author": "Jack Daniels", 
            "review": "I am no alchohol. The van was good.",
            "rating": 5
            }
        )
    assert response.status_code == 201
    assert response.json.get("message") == "Review created"
    # confirm review creation
    assert len(van.reviews) == 2  # 1 review from `conftest.py`; another one - created;


wrong_van_UUID = "afcda8a9-cbc1-4d11-8381-c4a9ca4299e3"
