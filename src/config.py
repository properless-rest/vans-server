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
    RESET_PW_TOKEN_EXP = 900  # THIS IS FOR PW RESET FORM: IN SECONDS
    #
    STATIC_FOLDER = "static"
    DEFAULT_USER_IMG = path.join("static", "user", ".default", "default.png")
    DEFAULT_VANS_IMG = path.join("static", "vans", ".default", "default.jpg")
    #
    FLASK_ADMIN_SWATCH = 'cerulean'  # a default theme for the ADMIN panel
    ADMIN_USERNAME = getenv("ADMIN_USERNAME")
    ADMIN_PASSWORD = getenv("ADMIN_PASSWORD")
    #
    # IN ProdConf:
    # SQLALCHEMY_DATABASE_URI = "sqlite:///data.db"
    # SQLALCHEMY_TRACK_MODIFICATIONS = False
    #
    # IN ProdConf:
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
    SQLALCHEMY_DATABASE_URI = "sqlite:///database.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    #
    JWT_COOKIE_SECURE = True
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=14)


class TestConfig(Config):
    TESTING = True
    #
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    #
    JWT_COOKIE_SECURE = False
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(seconds=5)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(minutes=1)


# app.config['FRONTEND_URL'] = getenv("FRONTEND_URL")
# #
# app.config['SECRET_KEY'] = getenv("SECRET_KEY")
# app.config['SALT'] = getenv("SALT")
# app.config['RESET_PW_TOKEN_EXP'] = 900  # THIS IS FOR PW RESET FORM: IN SECONDS
# #
# app.config['STATIC_FOLDER'] = "static"
# app.config['DEFAULT_USER_IMG'] = path.join("static", "user", ".default", "default.png")
# app.config['DEFAULT_VANS_IMG'] = path.join("static", "vans", ".default", "default.jpg")
# #
# app.config['FLASK_ADMIN_SWATCH'] = 'cerulean'  # a default theme for the ADMIN panel
# app.config['ADMIN_USERNAME'] = getenv("ADMIN_USERNAME")
# app.config['ADMIN_PASSWORD'] = getenv("ADMIN_PASSWORD")
# #
# app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///data.db"
# app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
# #
# app.config["JWT_COOKIE_SECURE"] = True
# app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=1)
# app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=14)
# #
# app.config['MAIL_SERVER'] = getenv("MAIL_SERVER")
# app.config['MAIL_PORT'] = getenv("MAIL_PORT")
# app.config['MAIL_USERNAME'] = getenv("MAIL_USERNAME")
# app.config['MAIL_PASSWORD'] = getenv("MAIL_PASSWORD")
# app.config['MAIL_USE_TLS'] = True
# app.config['MAIL_USE_SSL'] = False
# #

SERVER_TIMEZONE = timezone("Europe/Riga")

CORS(app)  # cross-origin request

app.config.from_object(ProdConfig)


admin = Admin(app, name="Vans", template_mode='bootstrap4')
bcrypt = Bcrypt(app)
db = SQLAlchemy(app)
executor = Executor(app)
jwt = JWTManager(app)
mail = Mail(app)
migrate = Migrate(app, db)
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
