from datetime import datetime, timedelta
from uuid import uuid4

from config import app, bcrypt, db, SERVER_TIMEZONE
from models import User, Van, Transaction, Review


def seed_database():
    with app.app_context():
        # Ensure tables are created

        db.create_all()

        # Create Users
        user1 = User(
            uuid=uuid4(),
            name="Alexander",
            surname="Bolverstein",
            email="a@b.c",
            password = bcrypt.generate_password_hash("12").decode('utf-8')
        )
        
        user2 = User(
            uuid=uuid4(),
            name="Snake",
            surname="Test",
            email="snaketests.app@gmail.com",
            password = bcrypt.generate_password_hash("11").decode('utf-8')
        )
        
        db.session.add_all([user1, user2])
        db.session.commit()

        # Create Vans associated with users
        van1 = Van(
            uuid=uuid4(),
            name="Modest Explorer",
            type="Simple",
            description="The Modest Explorer is a van designed to get you out of the house and into nature. This beauty is equipped with solar panels, a composting toilet, a water tank and kitchenette. The idea is that you can pack up your home and escape for a weekend or even longer!",
            price_per_day=60,
            host_id=user1.id  # Foreign key
        )
        
        van2 = Van(
            uuid=uuid4(),
            name="Beach Bum",
            type="Rugged",
            description="Beach Bum is a van inspired by surfers and travelers. It was created to be a portable home away from home, but with some cool features in it you won't find in an ordinary camper.",
            price_per_day=80,
            host_id=user1.id
        )

        van3 = Van(
            uuid=uuid4(),
            name="Reliable Red",
            type="Luxury",
            description="Reliable Red is a van that was made for travelling. The inside is comfortable and cozy, with plenty of space to stretch out in. There's a small kitchen, so you can cook if you need to. You'll feel like home as soon as you step out of it.",
            price_per_day=100,
            host_id=user1.id
        )

        van4 = Van(
            uuid=uuid4(),
            name="Dreamfinder",
            type="Simple",
            description="Dreamfinder is the perfect van to travel in and experience. With a ceiling height of 2.1m, you can stand up in this van and there is great head room. The floor is a beautiful glass-reinforced plastic (GRP) which is easy to clean and very hard wearing. A large rear window and large side windows make it really light inside and keep it well ventilated.",
            price_per_day=65,
            host_id=user1.id
        )

        van5 = Van(
            uuid=uuid4(),
            name="The Cruiser",
            type="Luxury",
            description="Dreamfinder is the perfect van to travel in and experience. With a ceiling height of 2.1m, you can stand up in this van and there is great head room. The floor is a beautiful glass-reinforced plastic (GRP) which is easy to clean and very hard wearing. A large rear window and large side windows make it really light inside and keep it well ventilated.",
            price_per_day=120,
            host_id=user1.id
        )

        van6 = Van(
            uuid=uuid4(),
            name="Green Wonder",
            type="Rugged",
            description="With this van, you can take your travel life to the next level. The Green Wonder is a sustainable vehicle that's perfect for people who are looking for a stylish, eco-friendly mode of transport that can go anywhere.",
            price_per_day=70,
            host_id=user1.id
        )


        db.session.add_all([van1, van2, van3, van4, van5, van6])
        db.session.commit()

        # Create Transactions for the vans
        transaction1 = Transaction(
            uuid=uuid4(),
            lessee_name="Manual",
            lessee_surname="Samuel",
            lessee_email="samual@example.com",
            price=van1.price_per_day * 3,
            transaction_date=datetime.now(SERVER_TIMEZONE).date(),
            rent_commencement=datetime.now(SERVER_TIMEZONE).date(),
            rent_expiration=(datetime.now(SERVER_TIMEZONE) + timedelta(days=3)).date(),
            lessor_id=user1.id,
            van_id=van1.id
        )

        transaction2 = Transaction(
            uuid=uuid4(),
            lessee_name="Linda",
            lessee_surname="Shine",
            lessee_email="lishe@example.com",
            price=van2.price_per_day * 2,
            transaction_date=datetime.now(SERVER_TIMEZONE).date(),
            rent_commencement=datetime.now(SERVER_TIMEZONE).date(),
            rent_expiration=(datetime.now(SERVER_TIMEZONE) + timedelta(days=2)).date(),
            lessor_id=user1.id,
            van_id=van2.id
        )

        db.session.add_all([transaction1, transaction2])
        db.session.commit()

        # Create Reviews for the vans
        review1 = Review(
            uuid=uuid4(),
            author="Manual Samuel",
            text="The van is fantastic",
            rate=5,
            publication_date=datetime.now(SERVER_TIMEZONE).date(),
            owner_id=user1.id,
            van_id=van1.id,
            van_uuid=van1.uuid,
            van_name=van1.name
        )

        review2 = Review(
            uuid=uuid4(),
            author="Linda Shine",
            text="The van isn't in its best conditions, but it definitely is worth its price.",
            rate=4,
            publication_date=datetime.now(SERVER_TIMEZONE).date(),
            owner_id=user1.id,
            van_id=van4.id,
            van_uuid=van4.uuid,
            van_name=van4.name
        )

        db.session.add_all([review1, review2])
        db.session.commit()

        print("Database seeded successfully with sample data.")

if __name__ == "__main__":
    seed_database()
