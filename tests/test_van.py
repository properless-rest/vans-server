
import os
from io import BytesIO

from config import app, db
from models import Van


def test_get_vans(client):
    # POST instead of GET
    response = client.post("/vans")
    assert response.status_code == 405
    # Success
    response = client.get("/vans")
    assert response.status_code == 200
    vans = response.json.get("vans", None)
    assert vans is not None
    assert len(vans) == 3
    print(vans[0])
    assert vans[0].get("host").get("email") == "name.surname@example.com"


def test_get_van(client):
    # pre-requisites
    van1_uuid = Van.query.get(1).uuid
    extraneous_uuid = "0a31763f-94dc-4198-8d92-46f4d772574b"
    # POST instead of GET
    response = client.post(f"/vans/{van1_uuid}")
    assert response.status_code == 405
    # UUID not in DB
    response = client.get(f"/vans/{extraneous_uuid}")
    assert response.status_code == 200
    assert response.json.get("message") == "Van does not exist"
    # success
    response = client.get(f"/vans/{van1_uuid}")
    assert response.status_code == 200
    van = response.json.get("van", None)
    assert van is not None
    assert van.get("description") == "Van#1 Description"


def test_add_van(client):
    # pre-requisites
    JWT = client.post("/login", json={"email": "name.surname@example.com", "password": "12345678"}).json.get("JWToken")
    # GET instead of POST
    response = client.get("/addVan")
    assert response.status_code == 404
    # no Authorization header
    response = client.post("/addVan", json={})
    assert response.status_code == 401
    assert response.json.get("msg") == "Missing Authorization Header"
    # extraneous JWT
    response = client.post("/addVan", headers={"Authorization": f"Bearer {false_JWT}"}, json={})
    assert response.status_code == 422
    assert response.json.get("msg") == "Signature verification failed"
    # empty JSON
    response = client.post("/addVan", headers={"Authorization": f"Bearer {JWT}"}, json={})
    assert response.status_code == 400
    assert response.json.get("message") == "Required data missing"
    # JSON data too long
    response = client.post("/addVan", 
                           headers={"Authorization": f"Bearer {JWT}"}, 
                           json={"name": "New" * 100, "description": "NewVan DESC.", "type": "Special", "pricePerDay": 150}
                           )
    assert response.status_code == 400
    assert response.json.get("message") == "Name is too long"
    #
    response = client.post("/addVan", 
                           headers={"Authorization": f"Bearer {JWT}"}, 
                           json={"name": "New", "description": "DESC" * 2000, "type": "Special", "pricePerDay": 150}
                           )
    assert response.status_code == 400
    assert response.json.get("message") == "Description is too long"
    # loose van type
    response = client.post("/addVan", 
                           headers={"Authorization": f"Bearer {JWT}"}, 
                           json={"name": "NewVan", "description": "NewVan DESC.", "type": "Special", "pricePerDay": 150}
                        )
    assert response.status_code == 400
    assert response.json.get("message") == "Invalid Van type"
    # loose van type
    response = client.post("/addVan", 
                           headers={"Authorization": f"Bearer {JWT}"}, 
                           json={"name": "NewVan", "description": "NewVan DESC.", "type": "Special", "pricePerDay": 150}
                        )
    assert response.status_code == 400
    assert response.json.get("message") == "Invalid Van type"
    # inadmissible price
    response = client.post("/addVan", 
                           headers={"Authorization": f"Bearer {JWT}"}, 
                           json={"name": "NewVan", "description": "NewVan DESC.", "type": "Simple", "pricePerDay": ["a", "b"]}
                        )
    assert response.status_code == 400
    assert response.json.get("message") == "Inadmissible price"
    # non-positive price
    response = client.post("/addVan", 
                           headers={"Authorization": f"Bearer {JWT}"}, 
                           json={"name": "NewVan", "description": "NewVan DESC.", "type": "Simple", "pricePerDay": -33}
                        )
    assert response.status_code == 400
    assert response.json.get("message") == "Price must be positive"
    # price too large (would overflow the SQL value checking)
    response = client.post("/addVan", 
                            headers={"Authorization": f"Bearer {JWT}"}, 
                            json={"name": "NewVan", "description": "NewVan DESC.", "type": "Simple", "pricePerDay": 2_100_000}
                        )
    assert response.status_code == 400
    assert response.json.get("message") == "Price too large"
    # Success
    response = client.post("/addVan", 
                            headers={"Authorization": f"Bearer {JWT}"}, 
                            json={"name": "NewVan", "description": "NewVan DESC.", "type": "Rugged", "pricePerDay": 90}
                        )
    assert response.status_code == 201
    assert response.json.get("message") == "Van created"
    # fetch the van and check data
    created_van = Van.query.order_by(Van.id.desc()).first()
    assert created_van.name == "NewVan"
    assert created_van.type == "Rugged"
    assert created_van.price_per_day == 90


def test_upload_image(client):
    # pre-requisites
    JWT = client.post("/login", json={"email": "name.surname@example.com", "password": "12345678"}).json.get("JWToken")
    van_uuid = Van.query.get(1).uuid
    # GET instead of POST
    response = client.get("/uploadVanImage")
    assert response.status_code == 404
    # no Authorization header
    response = client.post("/uploadVanImage", data={})
    assert response.status_code == 401
    assert response.json.get("msg") == "Missing Authorization Header"
    # extraneous JWT
    response = client.post("/uploadVanImage", headers={"Authorization": f"Bearer {false_JWT}"}, data={})
    assert response.status_code == 422
    assert response.json.get("msg") == "Signature verification failed"
    # no vanUUID
    response = client.post("/uploadVanImage", headers={"Authorization": f"Bearer {JWT}"}, data={})
    assert response.status_code == 400
    assert response.json.get("message") == "Invalid UUID"
    # wrong vanUUID
    response = client.post("/uploadVanImage", 
                           headers={"Authorization": f"Bearer {JWT}"}, 
                           data={"vanUUID": "afcda8a9-cbc1-4d11-8381-c4a9ca4299e3"},
                            content_type="multipart/form-data"
                           )
    assert response.status_code == 404
    assert response.json.get("message") == "The Van does not exist"
    # -
    response = client.post("/uploadVanImage", 
                        headers={"Authorization": f"Bearer {JWT}"}, 
                        data={"vanUUID": [123, 123, 123]},
                        content_type="multipart/form-data"
                        )
    assert response.status_code == 400
    assert response.json.get("message") == "Invalid UUID"
    #
    mocked_file = (BytesIO(b"mocked-image"), "test.png")  # will be closed after each POST

    response = client.post("/uploadVanImage", 
                    headers={"Authorization": f"Bearer {JWT}"}, 
                    data={"image": mocked_file, "vanUUID": [123, 123, 123]}, 
                    content_type="multipart/form-data"
                    )
    assert response.status_code == 400
    assert response.json.get("message") == "Invalid UUID"
    # no file attached
    empty_mocked_file = (BytesIO(b"mocked-image"), "")  # will be closed after each POST
    response = client.post("/uploadVanImage", 
                    headers={"Authorization": f"Bearer {JWT}"}, 
                    data={"image": empty_mocked_file, "vanUUID": van_uuid}, 
                    content_type="multipart/form-data"
                    )
    assert response.status_code == 400
    assert response.json.get("message") == "No file detected"
    # inadmissible file name
    nameless_mocked_file = (BytesIO(b"mocked-image"), ".jpeg")  # will be closed after each POST
    response = client.post("/uploadVanImage", 
                    headers={"Authorization": f"Bearer {JWT}"}, 
                    data={"image": nameless_mocked_file, "vanUUID": van_uuid}, 
                    content_type="multipart/form-data"
                    )
    assert response.status_code == 400
    assert response.json.get("message") == "Inadmissible file name"
    # inadmissible file extension
    inadmissible_mocked_file = (BytesIO(b"mocked-image"), "video.mp4")  # will be closed after each POST
    response = client.post("/uploadVanImage", 
                    headers={"Authorization": f"Bearer {JWT}"}, 
                    data={"image": inadmissible_mocked_file, "vanUUID": van_uuid}, 
                    content_type="multipart/form-data"
                    )
    assert response.status_code == 400
    assert response.json.get("message") == "Extension: .png, .jp(e)g"
    # Success
    mocked_file = (BytesIO(b"mocked-image"), "van.png")  # will be closed after each POST
    response = client.post("/uploadVanImage", 
                    headers={"Authorization": f"Bearer {JWT}"}, 
                    data={"image": mocked_file, "vanUUID": van_uuid}, 
                    content_type="multipart/form-data"
                    )
    assert response.status_code == 200
    assert response.json.get("message") == "Image updated"
    # Verify file storage
    van_folder = os.path.join(app.config["STATIC_FOLDER"], "vans", str(van_uuid))
    saved_files = os.listdir(van_folder)
    assert len(saved_files) == 1  # exactly one file is saved
    assert saved_files[0].split(".")[-1] == "png"

    # ! Clean-up is in the `contest.py`'s test_app !


def test_update_van(client):
    # pre-requisites
    JWT = client.post("/login", json={"email": "name.surname@example.com", "password": "12345678"}).json.get("JWToken")
    first_van = Van.query.get(1)
    van_uuid = first_van.uuid
    # GET instead of PATCH
    response = client.get("/updateVan")
    assert response.status_code == 404
    # no Authorization header
    response = client.patch("/updateVan", json={})
    assert response.status_code == 401
    assert response.json.get("msg") == "Missing Authorization Header"
    # extraneous JWT
    response = client.patch("/updateVan", headers={"Authorization": f"Bearer {false_JWT}"}, json={})
    assert response.status_code == 422
    assert response.json.get("msg") == "Signature verification failed"
    # no vanUUID
    response = client.patch("/updateVan", headers={"Authorization": f"Bearer {JWT}"}, json={})
    assert response.status_code == 400
    assert response.json.get("message") == "Invalid UUID"
    # wrong vanUUID
    response = client.patch("/updateVan", 
                            headers={"Authorization": f"Bearer {JWT}"}, 
                            json={"vanUUID": "afcda8a9-cbc1-4d11-8381-c4a9ca4299e3"},
                           )
    assert response.status_code == 404
    assert response.json.get("message") == "The Van does not exist"    
    # -
    response = client.patch("/updateVan", 
                        headers={"Authorization": f"Bearer {JWT}"}, 
                        json={"vanUUID": [123, 123, 123]},
                        )
    assert response.status_code == 400
    assert response.json.get("message") == "Invalid UUID"
    # no data in JSON
    response = client.patch("/updateVan", 
                    headers={"Authorization": f"Bearer {JWT}"}, 
                    json={"vanUUID": van_uuid}, 
                    )
    assert response.status_code == 400
    assert response.json.get("message") == "Required data missing"
    # JSON data too long
    response = client.patch("/updateVan", 
                           headers={"Authorization": f"Bearer {JWT}"}, 
                           json={
                            "vanUUID": van_uuid,
                            "name": "New" * 100, 
                            "description": "NewVan DESC.", 
                            "type": "Special", 
                            "pricePerDay": 50
                           }
                           )
    assert response.status_code == 400
    assert response.json.get("message") == "Name is too long"
    #
    response = client.patch("/updateVan", 
                           headers={"Authorization": f"Bearer {JWT}"}, 
                           json={
                            "vanUUID": van_uuid,
                            "name": "New", 
                            "description": "DESC" * 2000, 
                            "type": "Special", 
                            "pricePerDay": 50
                           }
                           )
    assert response.status_code == 400
    assert response.json.get("message") == "Description is too long"
    # loose van type
    response = client.patch("/updateVan", 
                           headers={"Authorization": f"Bearer {JWT}"}, 
                           json={
                                "vanUUID": van_uuid,
                                "name": "Van1", 
                                "description": "Van#1 Description",
                                "type": "Special", 
                                "pricePerDay": 50
                                }
                        )
    assert response.status_code == 400
    assert response.json.get("message") == "Invalid Van type"
    # inadmissible price
    response = client.patch("/updateVan", 
                           headers={"Authorization": f"Bearer {JWT}"}, 
                           json={
                                "vanUUID": van_uuid,
                                "name": "Van1", 
                                "description": "Van#1 Description", 
                                "type": "Simple", 
                                "pricePerDay": ["a", "b"]
                            }
                        )
    assert response.status_code == 400
    assert response.json.get("message") == "Inadmissible price"
    # non-positive price
    response = client.patch("/updateVan", 
                           headers={"Authorization": f"Bearer {JWT}"}, 
                           json={
                                "vanUUID": van_uuid,
                                "name": "Van1", 
                                "description": "Van#1 Description", 
                                "type": "Simple", 
                                "pricePerDay": -33
                            }
                        )
    assert response.status_code == 400
    assert response.json.get("message") == "Price must be positive"
    # price too large (would overflow the SQL value checking)
    response = client.patch("/updateVan", 
                            headers={"Authorization": f"Bearer {JWT}"}, 
                           json={
                                "vanUUID": van_uuid,
                                "name": "Van1", 
                                "description": "Van#1 Description", 
                                "type": "Simple", 
                                "pricePerDay": 2_100_000
                            }                        )
    assert response.status_code == 400
    assert response.json.get("message") == "Price too large"
    # no modifications
    response = client.patch("/updateVan", 
                           headers={"Authorization": f"Bearer {JWT}"}, 
                           json={
                                "vanUUID": van_uuid,
                                "name": "Van1", 
                                "description": "Van#1 Description", 
                                "type": "Simple", 
                                "pricePerDay": 50
                            }
                        )
    assert response.status_code == 400
    assert response.json.get("message") == "No modifications detected"
    # Success
    response = client.patch("/updateVan", 
                        headers={"Authorization": f"Bearer {JWT}"}, 
                        json={
                            "vanUUID": van_uuid,
                            "name": "Van1", 
                            "description": "Van#1 Modified", 
                            "type": "Simple", 
                            "pricePerDay": 70
                        }
                    )
    assert response.status_code == 200
    assert response.json.get("message") == "Van data updated"
    # verify modified data
    assert first_van.description == "Van#1 Modified"
    assert first_van.price_per_day == 70


def test_delete_van(client):
    # pre-requisites
    JWT = client.post("/login", json={"email": "name.surname@example.com", "password": "12345678"}).json.get("JWToken")
    first_van = Van.query.get(1)
    van_uuid = first_van.uuid
    # POST instead of DELETE
    response = client.post("/deleteVan")
    assert response.status_code == 405
    # no Authorization header
    response = client.delete("/deleteVan", json={})
    assert response.status_code == 401
    assert response.json.get("msg") == "Missing Authorization Header"
    # extraneous JWT
    response = client.delete("/deleteVan", headers={"Authorization": f"Bearer {false_JWT}"}, json={})
    assert response.status_code == 422
    assert response.json.get("msg") == "Signature verification failed"
    # no vanUUID
    response = client.delete("/deleteVan", headers={"Authorization": f"Bearer {JWT}"}, json={})
    assert response.status_code == 400
    assert response.json.get("message") == "Invalid UUID"
    # wrong vanUUID
    response = client.delete("/deleteVan", 
                            headers={"Authorization": f"Bearer {JWT}"}, 
                            json={"vanUUID": "afcda8a9-cbc1-4d11-8381-c4a9ca4299e3"},
                           )
    assert response.status_code == 404
    assert response.json.get("message") == "The Van does not exist"    
    # -
    response = client.delete("/deleteVan", 
                        headers={"Authorization": f"Bearer {JWT}"}, 
                        json={"vanUUID": [123, 123, 123]},
                        )
    assert response.status_code == 400
    assert response.json.get("message") == "Invalid UUID"
    # Success
    response = client.delete("/deleteVan", 
                        headers={"Authorization": f"Bearer {JWT}"}, 
                        json={"vanUUID": van_uuid},
                        )
    assert response.status_code == 200
    assert response.json.get("message") == "Van deleted"
    # confirm that the first Van is absent in the query ORM
    first_van = Van.query.order_by(Van.id).first()
    assert first_van.name == "Van2"
    assert first_van.type == "Rugged"



false_JWT = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
