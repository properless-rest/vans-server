from os import getenv

from flask import Flask
#
from flask_admin import Admin
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

from dotenv import load_dotenv


load_dotenv()

app = Flask(__name__)  # instantiate flask app
CORS(app)  # cross-origin request

app.config['SECRET_KEY'] = getenv("SECRET_KEY")
app.config['FLASK_ADMIN_SWATCH'] = 'cerulean'  # a default theme for the ADMIN panel
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///data.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

admin = Admin(app)
bcrypt = Bcrypt(app)
db = SQLAlchemy(app)
jwt = JWTManager(app)
migrate = Migrate(app, db)
