from datetime import timedelta

from pytest import fixture
from pytz import timezone

from config import app, db, TestConfig
import main  # import main to register all routes with the Flask app; the tests fail otherwise;


@fixture(scope="module")
def test_app():
    # Configure the app for testing
    app.config.from_object(TestConfig)

    # Create an application context
    with app.app_context():
        yield app  # Provide the app as a fixture


@fixture(scope="module")
def client(test_app):
    # Set up the database for testing
    db.create_all()

    # Get a test client
    with test_app.test_client() as client:
        yield client

    # Clean up after tests
    db.drop_all()
