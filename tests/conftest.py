from os import environ, path
from datetime import datetime, timedelta
from shutil import rmtree
from uuid import uuid4
#
from pytest import fixture

# is testing, FLASK_ENV must be set to `test` to prevent loading prod settings in `config.py`
# "FLASK_ENV" is set in `pytest.ini; `pip install pytest-env` is required for syntax construing`

from config import app, bcrypt, db, SERVER_TIMEZONE
from models import User, Van, Transaction, Review
import main  # import main to register all routes with the Flask app; the tests fail otherwise;


@fixture(scope="module")
def test_app():
    # Create an application context
    with app.app_context():
        print("Creating tables...")
        db.create_all()  # Set up test database
        print("Tables created.")
        test_user = User(
            uuid=uuid4(), 
            name="Name", 
            surname="Surname", 
            email="name.surname@example.com",
            password=bcrypt.generate_password_hash("12345678").decode('utf-8')
        )
        test_van1 = Van(
            uuid=uuid4(),
            name="Van1",
            type="Simple",
            description="Van#1 Description",
            price_per_day=50,
            host_id=1
        )
        test_van2 = Van(
            uuid=uuid4(),
            name="Van2",
            type="Rugged",
            description="Van#2 Description",
            price_per_day=80,
            host_id=1
        )
        test_van3 = Van(
            uuid=uuid4(),
            name="Van3",
            type="Luxury",
            description="Van#3 Description",
            price_per_day=110,
            host_id=1
        )
        test_trx = Transaction(
            uuid=uuid4(),
            lessee_name="Mike",
            lessee_surname="Michaels",
            lessee_email="mykie_mic@example.com",
            price=100,
            # remember that the earliest possible commencement day is the day of tomorrow
            rent_commencement=(datetime.now(SERVER_TIMEZONE) + timedelta(days=1)).date(),
            rent_expiration=(datetime.now(SERVER_TIMEZONE) + timedelta(days=3)).date(),
            lessor_id=1,
            van_id=1
        )
        test_review = Review(
            uuid=uuid4(),
            author="Mike Michaels",
            text="Van#1 is a good van. I enjoyed using it. The state of the van is a bit rusty, however.",
            rate=4,
            publication_date=datetime.now().date(),
            owner_id=1,
            van_id=1,
            van_uuid=test_van1.uuid,
            van_name=test_van1.name
        )
        print("Adding table data...")
        db.session.add_all([test_user, test_van1, test_van2, test_van3, test_trx, test_review])
        db.session.commit()
        print("Table data added.")
        yield app  # yield the app as a fixture; testing happens here;
        print("Closing up db session...")
        db.session.close() # ! CLOSE !BEFORE! dropping all the tables; PostgreSQL freezes `pytest` without this line
        print("Db session closed.")
        print("Dropping data tables...")
        db.drop_all() # clear after all the test has been executed
        print("Tables dropped.")
        # clean the folder where uploaded images could be stored for testing purposes
        if path.exists(app.config.get("STATIC_FOLDER")):
            print("Removing static files used for testing...")
            rmtree(app.config.get("STATIC_FOLDER"))
            print("Static files removed.")


@fixture(scope="module")
def client(test_app):
    # Get a test client
    return test_app.test_client()


@fixture(scope="module")
def runner(test_app):
    return test_app.test_cli_runner()

