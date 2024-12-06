# system
from os import getenv, path
from datetime import timedelta
from itsdangerous import URLSafeTimedSerializer

# 3rd party flask
from flask import Flask
#
from flask_admin import Admin
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flask_executor import Executor
from flask_jwt_extended import JWTManager
from flask_mailman import Mail
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

# 3rd party misc
from dotenv import load_dotenv
from pytz import timezone

load_dotenv()


app = Flask(__name__)  # instantiate flask app



class Config:
    FRONTEND_URL = getenv("FRONTEND_URL")
    #
    SECRET_KEY = getenv("SECRET_KEY")
    SALT = getenv("SALT")
    #
    STATIC_FOLDER = "static"
    DEFAULT_USER_IMG = path.join("static", "user", ".default", "default.png")
    DEFAULT_VANS_IMG = path.join("static", "vans", ".default", "default.jpg")
    #
    FLASK_ADMIN_SWATCH = 'cerulean'  # a default theme for the ADMIN panel
    ADMIN_USERNAME = getenv("ADMIN_USERNAME")
    ADMIN_PASSWORD = getenv("ADMIN_PASSWORD")
    #
    JWT_COOKIE_SECURE = True
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=14)
    #
    MAIL_SERVER = getenv("MAIL_SERVER")
    MAIL_PORT = getenv("MAIL_PORT")
    MAIL_USERNAME = getenv("MAIL_USERNAME")
    MAIL_PASSWORD = getenv("MAIL_PASSWORD")
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False


class ProdConfig(Config):
    SQLALCHEMY_DATABASE_URI = getenv("POSTGRESQL_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    #
    STATIC_FOLDER = "static"
    #
    RESET_PW_TOKEN_EXP = 900  # THIS IS FOR PW RESET FORM: IN SECONDS = 15 min.
    #
    JWT_COOKIE_SECURE = True
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=14)


class TestConfig(Config):
    TESTING = True
    #
    SQLALCHEMY_DATABASE_URI = getenv("POSTGRESQL_TEST")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    #
    STATIC_FOLDER = "tests/testatic"
    #
    RESET_PW_TOKEN_EXP = 5  # THIS IS FOR PW RESET FORM: IN SECONDS
    #
    JWT_COOKIE_SECURE = False
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(seconds=5)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(minutes=1)


# server timezone is imported into main; do not enclose it
SERVER_TIMEZONE = timezone("Europe/Riga")

CORS(app)  # cross-origin request

# if not Testing, apply prod settings, else - apply test settings
# is testing, FLASK_ENV must be set to `test` to prevent loading prod settings in `config.py`
# "FLASK_ENV" is set in `pytest.ini; `pip install pytest-env` is required for syntax construing`
if getenv("FLASK_ENV") != "test":
    app.config.from_object(ProdConfig)
else:
    app.config.from_object(TestConfig)


admin = Admin(app, name="Vans", template_mode='bootstrap4')
bcrypt = Bcrypt(app)
db = SQLAlchemy(app)
executor = Executor(app)
jwt = JWTManager(app)
mail = Mail(app)
migrate = Migrate(app, db)
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
