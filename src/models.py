# standard library
from os import path
from datetime import datetime

# flask 3rd party
from flask import abort, redirect, session
from flask_admin.contrib.sqla import ModelView

# project
from config import app, admin, db, SERVER_TIMEZONE


class User(db.Model):

    name_len = 40
    surname_len = 40
    email_len = 40
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.UUID, unique=True, nullable=False)
    name = db.Column(db.String(name_len), unique=False, nullable=False)
    surname = db.Column(db.String(surname_len), unique=False, nullable=False)
    email = db.Column(db.String(email_len), unique=True, nullable=False)
    password = db.Column(db.String, unique=False, nullable=False)
    avatar = db.Column(db.String, default=app.config["DEFAULT_USER_IMG"], nullable=False)
    vans = db.relationship("Van", backref="host", lazy=True)
    transactions = db.relationship("Transaction", backref="lessor", lazy=True)
    reviews = db.relationship("Review", backref="owner", lazy=True)

    def get_full_name(self):
        return f"{self.name} {self.surname}"
    
    def __str__(self):
        return f"User: {self.get_full_name()}"
    
    def to_JSON(self):
        return {
                "id": self.id,
                "uuid": self.uuid,
                "name": self.name,
                "surname": self.surname,
                "email": self.email,
                "avatar": self.avatar,
                "vans": [van.to_JSON() for van in self.vans],
                "transactions": [transaction.to_JSON() for transaction in self.transactions],
                "reviews": [review.to_JSON() for review in self.reviews]
                }


class Van(db.Model):

    name_len = 60
    description_len = 1500

    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.UUID, unique=True, nullable=False)
    name = db.Column(db.String(name_len), nullable=False, unique=False)
    type = db.Column(db.String, nullable=False)
    description = db.Column(db.String(description_len), nullable=False)
    price_per_day = db.Column(db.Integer, nullable=False)
    image = db.Column(db.String, default=app.config["DEFAULT_VANS_IMG"], nullable=False)
    host_id = db.Column(db.Integer, db.ForeignKey("user.id"), name="host_id")
    transactions = db.relationship("Transaction", backref="van", lazy=True)
    reviews = db.relationship("Review", backref="van", lazy=True)

    def __str__(self):
        return f"{self.name} {self.type}"
    
    def __get_host_data(self):
        host = User.query.get(self.host_id)
        return {"full_name": host.get_full_name(), "email": host.email}

    def to_JSON(self):
        return {
                "id": self.id,
                "uuid": self.uuid,
                "name": self.name,
                "pricePerDay": self.price_per_day,
                "description": self.description,
                "type": self.type,
                "image": self.image,
                "host": self.__get_host_data()
                }


class Transaction(db.Model):

    name_len = 40
    surname_len = 40
    email_len = 40

    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.UUID, unique=True, nullable=False)
    lessee_name = db.Column(db.String(name_len), unique=False, nullable=False)
    lessee_surname = db.Column(db.String(surname_len), unique=False, nullable=False)
    lessee_email = db.Column(db.String(email_len), unique=False, nullable=False)
    price = db.Column(db.Integer, nullable=False)
    transaction_date = db.Column(db.Date, nullable=False, default=datetime.now(SERVER_TIMEZONE).date())
    rent_commencement = db.Column(db.Date, nullable=False)  # this is NOT! the transaction date
    rent_expiration = db.Column(db.Date, nullable=False)
    lessor_id = db.Column(db.Integer, db.ForeignKey("user.id"), name="lessor_id")
    van_id = db.Column(db.Integer, db.ForeignKey("van.id"), name="van_id")

    def __get_str_data(self):
        lessor = User.query.get(self.lessor_id)
        van = Van.query.get(self.van_id)
        return {"lessor": f"{lessor.name} {lessor.surname}", "van": van.name}

    def __repr__(self):
        data = self.__get_str_data()
        lessor = data.get("lessor")
        van = data.get("van")
        return f"{self.lessee_name} {self.lessee_surname} & {lessor} - {van}: {self.price}"

    def to_JSON(self):
        return {
                "id": self.id,
                "uuid": self.uuid,
                "lessee_name": self.lessee_name,
                "lessee_surname": self.lessee_surname,
                "lessee_email": self.lessee_email,
                "price": self.price,
                "transaction_date": self.transaction_date,
                "rent_commencement": self.rent_commencement,
                "rent_expiration": self.rent_expiration
                }


class Review(db.Model):

    author_len = 40
    text_len=512
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.UUID, unique=True, nullable=False)
    author = db.Column(db.String(author_len), unique=False, nullable=False)
    # NOTE:  MAX LENGTH: 512 symbols
    text = db.Column(db.String(text_len), unique=False, nullable=False)
    rate = db.Column(db.Integer, nullable=False)
    publication_date = db.Column(db.Date, nullable=False, default=datetime.now(SERVER_TIMEZONE).date())
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), name="owner_id")
    van_id = db.Column(db.Integer, db.ForeignKey("van.id"), name="van_id")
    van_uuid = db.Column(db.UUID, unique=False, name="van_uuid")  # needed for FrontEnd "host/reviews" <Link/> elements; Not a FK
    van_name = db.Column(db.String, nullable=False, unique=False)  # this must NOT be a ForeignKey; must remain when Van is deleted

    def __str__(self):
        return f"{self.author} - {self.rate}: {self.text}"

    def to_JSON(self):
        return {
                "id": self.id,
                "uuid": self.uuid,
                "author": self.author,
                "text": self.text,
                "rate": self.rate,
                "publication_date": self.publication_date,
                "van_name": self.van_name,
                "van_uuid": self.van_uuid,
                }


class BasicView(ModelView):
    # UUIDs not visible in standard ADMIN page
    can_create = False  # without UUID there's no way to create
    can_edit = False  # admin should not edit the user's data

    def is_accessible(self):
        # Authentification for the ADMIN
        # Additional protection, besides the `protect_admin()` view
        if "is_authorized" not in session:
            abort(403)
        return True  # else the model is accessible


class UserView(BasicView):
    # user models should not be managable by the admin
    can_delete = False

class VanView(BasicView):
    can_delete = True

class TransactionView(BasicView):
    can_delete = True

class ReviewView(BasicView):
    can_delete = True


admin.add_view(UserView(User, db.session))
admin.add_view(VanView(Van, db.session))
admin.add_view(TransactionView(Transaction, db.session))
admin.add_view(ReviewView(Review, db.session))
