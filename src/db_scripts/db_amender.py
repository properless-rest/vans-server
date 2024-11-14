
from datetime import datetime, date
from random import randrange, randint
from uuid import uuid4

from src.config import app, db
from src.models import Transaction


def make_transactions(number):
    trx_list = list()
    for _ in range(number):
        trx_year = randint(2020, 2024)
        trx_month = randint(1, 12) if trx_year != 2024 else randint(1, 9)
        trx_day = randint(1, 31) if trx_month in [1, 3, 5, 7, 8, 10, 12] else randint(1, 28)
        transaction = Transaction(
            uuid=uuid4(), 
            lessee_name="Name",
            lessee_surname="Surname",
            lessee_email=f"{uuid4().hex}@mail.com",
            price=randrange(80, 800, 20),
            transaction_date=date(trx_year, trx_month, trx_day),
            rent_commencement=datetime.now().date(),
            rent_expiration=datetime.now().date(),
            lessor_id=1,
            van_id=randint(1, 6)
        )
        trx_list.append(transaction)
    sorted_trxs = sorted(trx_list, key=lambda trx: trx.transaction_date)
    for trx in sorted_trxs:
        db.session.add(trx)
    try:
        db.session.commit()
        print(f"Created {number} new transactions")
    except Exception as e:
        print(f"ERROR: {e}")


def amend_transaction_dates():
    wrong_transactions = Transaction.query.filter(Transaction.transaction_date < "2010-01-01").all()
    for trx in wrong_transactions:
        trx.transaction_date=date(randint(2010, 2024), randint(1, 12), randint(1, 28))
    try:
        db.session.commit()
        print(f"Amended all dates")
    except Exception as e:
        print(f"ERROR: {e}")

def amend_transaction_lessors():
    wrong_transactions = Transaction.query.filter(Transaction.lessor_id != 1).all()
    for trx in wrong_transactions:
        trx.lessor_id=1
    try:
        db.session.commit()
        print(f"Amended all lessors")
    except Exception as e:
        print(f"ERROR: {e}")

def delete_extra_transactions():
    try:
        Transaction.query.filter(Transaction.id > 6).delete()
        db.session.commit()
        print("Transactions deleted successfully")
    except Exception as e:
        print(f"ERROR: {e}")

    
if __name__ == "__main__":
    with app.app_context():
        ...
        # amend_transaction_dates()
        # make_transactions(1)
        # delete_extra_transactions()
        