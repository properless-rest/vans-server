from uuid import UUID
from datetime import date
from typing import List

from sqlalchemy import CheckConstraint
# from sqlalchemy.orm import mapped_column, Mapped, relationship
# from sqlalchemy import ForeignKey

from config import db


class User(db.Model):

    # uuid: Mapped[UUID] = mapped_column(primary_key=True)
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(40), unique=False, nullable=False)
    surname = db.Column(db.String(40), unique=False, nullable=False)
    email = db.Column(db.String(40), unique=True, nullable=False)
    password = db.Column(db.String(512), unique=False, nullable=False)
    vans = db.relationship("Van", backref="User", lazy=True)
    # vans: Mapped[List] = relationship(back_populates="user", lazy=True)

    def to_JSON(self):
        return {
                "id": self.id,
                "name": self.name,
                "surname": self.surname,
                "email": self.email
                }
    
    def get_full_name(self):
        return f"{self.name} {self.surname}"
    
    def __str__(self):
        return f"User: {self.get_full_name()}"


class Van(db.Model):

    img_folder = "/static/models/vans"  # THIS IS THE PATH INSIDE THE FRONTEND APP;


    # uuid: Mapped[UUID] = mapped_column(primary_key=True)
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), nullable=False, unique=True)
    type = db.Column(db.String(30), nullable=False)
    description = db.Column(db.String(300), nullable=False)
    price_per_day = db.Column(db.Integer, nullable=False)
    image = db.Column(db.String(200), default=f"{img_folder}/default.jpg", nullable=False)
    rent_commencement = db.Column(db.DateTime)
    rent_expiration = db.Column(db.DateTime)

    # user_uuid = mapped_column(ForeignKey("user.uuid", ondelete="cascade"), nullable=False)
    # user_uuid = db.Column(db.String(32), db.ForeignKey('user.uuid'))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))

    def __str__(self):
        return f"{self.type}"

    def to_JSON(self):
        return {
                "id": self.id,
                "name": self.name,
                "pricePerDay": self.price_per_day,
                "description": self.description,
                "type": self.type,
                "image": self.image,
                "rentCommencement": self.rent_commencement,
                "rentExpiration": self.rent_expiration
                }


# class Order(db.Model):

#     uuid: Mapped[UUID] = mapped_column(primary_key=True)
#     user_uuid = mapped_column(ForeignKey("user.uuid", ondelete="cascade"))  # TODO: 1-N; cascade?
#     van_uuid = mapped_column(ForeignKey("van.uuid", max=1)   # TODO: 1-1; cascade?
